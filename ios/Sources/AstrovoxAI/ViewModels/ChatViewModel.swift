import Foundation
import Combine

@MainActor
class ChatViewModel: ObservableObject {
    @Published var messages: [Message] = []
    @Published var isLoading: Bool = false
    @Published var error: String?

    private let api = APIService()
    private var conversationId: String?

    func send(message: String, model: String = "gpt-4") async {
        guard !message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        error = nil
        isLoading = true

        if conversationId == nil {
            conversationId = "ios-\(Date().timeIntervalSince1970)"
        }

        let userMessage = Message(
            id: UUID().uuidString,
            conversationId: conversationId!,
            role: "user",
            content: message,
            timestamp: Date(),
            offline: false
        )
        messages.append(userMessage)

        do {
            let response = try await api.sendMessage(
                conversationId: conversationId!,
                message: message,
                model: model
            )
            if let content = response.content {
                let assistantMessage = Message(
                    id: UUID().uuidString,
                    conversationId: conversationId!,
                    role: "assistant",
                    content: content,
                    timestamp: Date(),
                    offline: false
                )
                messages.append(assistantMessage)
            }
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    func clear() {
        messages.removeAll()
        conversationId = nil
    }
}
