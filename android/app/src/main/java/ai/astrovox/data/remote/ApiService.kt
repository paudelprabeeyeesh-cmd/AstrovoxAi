package ai.astrovox.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

data class ChatRequest(
    val conversation_id: String,
    val message: String,
    val model: String = "gpt-4",
    val max_tokens: Int = 2048,
    val temperature: Double = 0.7,
    val stream: Boolean = false
)

data class MessageResponse(
    val ai_message: ChatMessage?,
    val content: String?,
    val conversation_id: String?
)

data class ChatMessage(
    val role: String,
    val content: String,
    val timestamp: String,
    val id: String?,
    val offline: Boolean
)

data class ConversationResponse(
    val id: String,
    val title: String,
    val created_at: String,
    val updated_at: String,
    val model: String
)

interface ApiService {
    @POST("v1/chat/message")
    suspend fun sendMessage(@Body request: ChatRequest): MessageResponse

    @GET("v1/conversations")
    suspend fun getConversations(): List<ConversationResponse>
}
