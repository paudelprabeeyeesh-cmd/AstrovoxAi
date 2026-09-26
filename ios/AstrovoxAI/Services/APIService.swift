import Foundation

class APIService: ObservableObject {
    static let shared = APIService()
    private let baseURL = "https://api.astrovox.ai/v1"
    private let session = URLSession.shared

    func sendMessage(conversationId: UUID, message: String, model: String = "gpt-4") async throws -> [String: Any] {
        let url = URL(string: "\(baseURL)/chat/message")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ["conversation_id": conversationId.uuidString, "message": message, "model": model]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, _) = try await session.data(for: request)
        return try JSONSerialization.jsonObject(with: data) as! [String: Any]
    }

    func healthCheck() async throws -> [String: Any] {
        let url = URL(string: "\(baseURL)/health")!
        let (data, _) = try await session.data(from: url)
        return try JSONSerialization.jsonObject(with: data) as! [String: Any]
    }
}
