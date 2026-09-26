package ai.astrovox

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import ai.astrovox.ui.theme.AstrovoxAITheme
import ai.astrovox.presentation.chat.ChatScreen
import ai.astrovox.presentation.chat.ChatViewModel
import ai.astrovox.domain.usecase.SendMessageUseCase
import ai.astrovox.data.repository.ChatRepository
import ai.astrovox.data.remote.ApiService
import ai.astrovox.data.local.AppDatabase
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AstrovoxAITheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    val application = application as AstrovoxAIApplication
                    val api = ApiService.create("https://api.astrovox.ai")
                    val repository = ChatRepository(api, application.database.conversationDao(), application.database.messageDao())
                    val useCase = SendMessageUseCase(repository)
                    val viewModel: ChatViewModel = viewModel(factory = ChatViewModelFactory(useCase))
                    ChatScreen(viewModel = viewModel, conversationId = "android-main")
                }
            }
        }
    }
}
