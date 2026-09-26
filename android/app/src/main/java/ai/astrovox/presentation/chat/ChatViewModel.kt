package ai.astrovox.presentation.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import ai.astrovox.domain.usecase.SendMessageUseCase
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class ChatState(
    val messages: List<ai.astrovox.domain.model.Message> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

class ChatViewModel(private val sendMessage: SendMessageUseCase) : ViewModel() {
    private val _state = MutableStateFlow(ChatState())
    val state: StateFlow<ChatState> = _state

    fun send(message: String, conversationId: String, model: String = "gpt-4") {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val result = sendMessage(conversationId, message, model)
                _state.value = _state.value.copy(
                    messages = _state.value.messages + result,
                    isLoading = false
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    error = e.message ?: "Unknown error",
                    isLoading = false
                )
            }
        }
    }
}
