package ai.astrovox

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import ai.astrovox.domain.usecase.SendMessageUseCase

class ChatViewModelFactory(private val sendMessage: SendMessageUseCase) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(ai.astrovox.presentation.chat.ChatViewModel::class.java)) {
            return ai.astrovox.presentation.chat.ChatViewModel(sendMessage) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class")
    }
}
