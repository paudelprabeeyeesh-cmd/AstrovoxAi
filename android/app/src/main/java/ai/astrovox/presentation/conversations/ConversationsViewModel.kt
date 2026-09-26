package ai.astrovox.presentation.conversations

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import ai.astrovox.data.repository.ChatRepository
import ai.astrovox.domain.model.Conversation
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class ConversationsState(
    val conversations: List<Conversation> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

class ConversationsViewModel(private val repository: ChatRepository) : ViewModel() {
    private val _state = MutableStateFlow(ConversationsState())
    val state: StateFlow<ConversationsState> = _state

    init {
        loadConversations()
    }

    fun loadConversations() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                repository.getConversations().collect { list ->
                    _state.value = _state.value.copy(
                        conversations = list.map { entity ->
                            Conversation(
                                id = entity.id,
                                title = entity.title,
                                createdAt = entity.createdAt,
                                updatedAt = entity.updatedAt,
                                model = entity.model
                            )
                        },
                        isLoading = false
                    )
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    error = e.message ?: "Unknown error",
                    isLoading = false
                )
            }
        }
    }
}
