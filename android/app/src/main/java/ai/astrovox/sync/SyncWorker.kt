package ai.astrovox.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import ai.astrovox.data.local.AppDatabase
import ai.astrovox.data.remote.ApiService
import ai.astrovox.data.remote.RetrofitClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class SyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    private val api = ApiService.create()
    private val database = AppDatabase.getInstance(applicationContext)

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        return@withContext try {
            val pending = database.messageDao().getPendingOffline()
            pending.forEach { entity ->
                val request = ai.astrovox.data.remote.ChatRequest(
                    conversation_id = entity.conversationId,
                    message = entity.content,
                    model = "gpt-4"
                )
                val response = api.sendMessage(request)
                database.messageDao().markSynced(entity.id)
            }
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}
