import Foundation

struct SendMessageRequest: Codable {
    let conversationId: String
    let message: String
    let model: String
    let maxTokens: Int
    let temperature: Double
    let stream: Bool
}

struct SendMessageResponse: Codable {
    let aiMessage: ChatMessage?
    let content: String?
    let conversationId: String?

    enum CodingKeys: String, CodingKey {
        case aiMessage = "ai_message"
        case content
        case conversationId = "conversation_id"
    }
}

struct ChatMessage: Codable {
    let role: String
    let content: String
    let timestamp: String
    let id: String?
    let offline: Bool
}

struct ConversationResponse: Codable {
    let id: String
    let title: String
    let createdAt: String
    let updatedAt: String
    let model: String
}

enum APIServiceError: LocalizedError {
    case invalidURL
    case requestFailed(Error)
    case decodingFailed(Error)
    case serverError(statusCode: Int, message: String)

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Invalid API URL."
        case .requestFailed(let error): return "Request failed: \(error.localizedDescription)"
        case .decodingFailed(let error): return "Decoding failed: \(error.localizedDescription)"
        case .serverError(let code, let message): return "Server error (\(code)): \(message)"
        }
    }
}

class APIService {
    private let baseURL: String = "https://api.astrovox.ai"

    func sendMessage(conversationId: String, message: String, model: String = "gpt-4") async throws -> SendMessageResponse {
        let url = URL(string: "\(baseURL)/v1/chat/message")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = SendMessageRequest(
            conversationId: conversationId,
            message: message,
            model: model,
            maxTokens: 2048,
            temperature: 0.7,
            stream: false
        )
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIServiceError.invalidURL
        }
        guard httpResponse.statusCode == 200 else {
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw APIServiceError.serverError(statusCode: httpResponse.statusCode, message: message)
        }
        return try JSONDecoder().decode(SendMessageResponse.self, from: data)
    }

    func getConversations() async throws -> [ConversationResponse] {
        let url = URL(string: "\(baseURL)/v1/conversations")!
        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw APIServiceError.invalidURL
        }
        return try JSONDecoder().decode([ConversationResponse].self, from: data)
    }
}
