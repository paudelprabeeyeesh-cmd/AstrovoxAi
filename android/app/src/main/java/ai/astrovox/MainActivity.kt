package ai.astrovox

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Spacer
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import ai.astrovox.data.local.AppDatabase
import ai.astrovox.data.remote.ApiService
import ai.astrovox.data.repository.ChatRepository
import ai.astrovox.domain.usecase.SendMessageUseCase
import ai.astrovox.notification.NotificationHelper
import ai.astrovox.presentation.chat.ChatScreen
import ai.astrovox.presentation.chat.ChatViewModel
import ai.astrovox.presentation.conversations.ConversationsScreen
import ai.astrovox.presentation.conversations.ConversationsViewModel
import ai.astrovox.ui.theme.AstrovoxAITheme
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        NotificationHelper.createChannel(this)

        val syncWork = PeriodicWorkRequestBuilder<ai.astrovox.sync.SyncWorker>(15, TimeUnit.MINUTES)
            .build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "astrovox_sync",
            ExistingPeriodicWorkPolicy.KEEP,
            syncWork
        )

        setContent {
            AstrovoxAITheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    val application = application as AstrovoxAIApplication
                    val api = ApiService.create()
                    val repository = ChatRepository(
                        api,
                        application.database.conversationDao(),
                        application.database.messageDao()
                    )
                    val useCase = SendMessageUseCase(repository)
                    val navController = rememberNavController()
                    var errorMessage by remember { mutableStateOf<String?>(null) }

                    NavHost(navController = navController, startDestination = "conversations") {
                        composable("conversations") {
                            val viewModel: ConversationsViewModel = viewModel(
                                factory = ConversationsViewModel.Factory(repository)
                            )
                            ConversationsScreen(
                                viewModel = viewModel,
                                onConversationSelected = { id ->
                                    navController.navigate("chat/$id")
                                }
                            )
                        }
                        composable("chat/{conversationId}") { backStackEntry ->
                            val conversationId = backStackEntry.arguments?.getString("conversationId") ?: "unknown"
                            val viewModel: ChatViewModel = viewModel(
                                factory = ChatViewModel.Factory(useCase)
                            )
                            errorMessage?.let { msg ->
                                ErrorScreen(message = msg, onRetry = { errorMessage = null })
                            } ?: run {
                                ChatScreen(viewModel = viewModel, conversationId = conversationId, onError = { errorMessage = it })
                            }
                        }
                    }

                    errorMessage?.let { msg ->
                        ErrorScreen(message = msg, onRetry = { errorMessage = null })
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleDeepLink(intent)
    }

    private fun handleDeepLink(intent: Intent?) {
        val data: Uri? = intent?.data
        data?.let { uri ->
            if (uri.scheme == "astrovox" && uri.host == "chat") {
                val conversationId = uri.lastPathSegment ?: return
                setContent {
                    AstrovoxAITheme {
                        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                            val application = application as AstrovoxAIApplication
                            val api = ApiService.create()
                            val repository = ChatRepository(
                                api,
                                application.database.conversationDao(),
                                application.database.messageDao()
                            )
                            val useCase = SendMessageUseCase(repository)
                            val viewModel: ChatViewModel = viewModel(factory = ChatViewModelFactory(useCase))
                            ChatScreen(viewModel = viewModel, conversationId = conversationId, onError = {})
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ErrorScreen(message: String, onRetry: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(text = message, modifier = Modifier.padding(16.dp), color = MaterialTheme.colorScheme.error)
        Spacer(modifier = Modifier.height(16.dp))
        Button(onClick = onRetry) {
            Text("Retry")
        }
    }
}
