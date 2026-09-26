package ai.astrovox.domain.model

data class Message(
    val id: String,
    val conversationId: String,
    val role: String,
    val content: String,
    val timestamp: Long,
    val offline: Boolean
)
