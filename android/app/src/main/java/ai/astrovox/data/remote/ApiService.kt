package ai.astrovox.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

data class ChatRequest(
    val conversation_id: String,
    val message: String,
    val model: String
)

interface AstrovoxApi {
    @POST("/v1/chat/message")
    suspend fun sendMessage(@Body request: ChatRequest): Map<String, Any>

    @GET("/v1/health")
    suspend fun healthCheck(): Map<String, Any>
}

object ApiService {
    private val retrofit = RetrofitClient.retrofit
    fun create(): AstrovoxApi = retrofit.create(AstrovoxApi::class.java)
}
