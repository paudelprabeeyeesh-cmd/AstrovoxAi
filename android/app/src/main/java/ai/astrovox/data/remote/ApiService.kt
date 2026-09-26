package ai.astrovox.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface ApiService {
    @POST("/chat/message")
    suspend fun sendMessage(@Body request: Map<String, String>): Map<String, Any>

    @GET("/health")
    suspend fun healthCheck(): Map<String, Any>
}

object ApiService {
    private val retrofit = ApiClient.retrofit
    fun create(): ApiService = retrofit.create(com.ai.astrovox.data.remote.ApiService::class.java)
}
