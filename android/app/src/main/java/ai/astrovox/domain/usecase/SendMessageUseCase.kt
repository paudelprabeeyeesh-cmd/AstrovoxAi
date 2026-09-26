package ai.astrovox.domain.usecase

import ai.astrovox.data.repository.ChatRepository
import ai.astrovox.domain.model.Message

class SendMessageUseCase(private val repository: ChatRepository) {
    suspend operator fun invoke(conversationId: String, message: String, model: String): Message {
        val entity = repository.sendMessage(conversationId, message, model)
        return Message(
            id = entity.id,
            conversationId = entity.conversationId,
            role = entity.role,
            content = entity.content,
            timestamp = entity.timestamp,
            offline = entity.offline
        )
    }
}
