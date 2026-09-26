package ai.astrovox.data.repository

import ai.astrovox.data.local.ConversationDao
import ai.astrovox.data.local.MessageDao
import ai.astrovox.data.local.entities.ConversationEntity
import ai.astrovox.data.local.entities.MessageEntity
import ai.astrovox.data.remote.ApiService
import ai.astrovox.data.remote.ChatRequest
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

class ChatRepository(
    private val api: ApiService,
    private val conversationDao: ConversationDao,
    private val messageDao: MessageDao
) {
    fun getConversations(): Flow<List<ConversationEntity>> = flow {
        emit(conversationDao.getAll())
    }

    fun getMessages(conversationId: String): Flow<List<MessageEntity>> = flow {
        emit(messageDao.getByConversation(conversationId))
    }

    suspend fun sendMessage(conversationId: String, message: String, model: String): MessageEntity {
        val request = ChatRequest(
            conversation_id = conversationId,
            message = message,
            model = model
        )
        val response = api.sendMessage(request)

        val userMessage = MessageEntity(
            id = "local-${System.currentTimeMillis()}-user",
            conversationId = conversationId,
            role = "user",
            content = message,
            timestamp = System.currentTimeMillis(),
            offline = false
        )
        val assistantMessage = MessageEntity(
            id = "local-${System.currentTimeMillis()}-assistant",
            conversationId = conversationId,
            role = "assistant",
            content = response["content"] as? String ?: (response["ai_message"] as? Map<*, *>)?.get("content") as? String ?: "",
            timestamp = System.currentTimeMillis(),
            offline = false
        )

        messageDao.insert(userMessage)
        messageDao.insert(assistantMessage)

        return assistantMessage
    }
}
