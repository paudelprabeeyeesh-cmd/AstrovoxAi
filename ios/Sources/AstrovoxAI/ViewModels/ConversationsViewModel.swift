import Foundation
import Combine

@MainActor
class ConversationsViewModel: ObservableObject {
    @Published var conversations: [Conversation] = []
    @Published var isLoading: Bool = false
    @Published var error: String?

    private let api = APIService()

    func loadConversations() async {
        isLoading = true
        error = nil
        do {
            let remote = try await api.getConversations()
            conversations = remote.map { remoteConversation in
                Conversation(
                    id: remoteConversation.id,
                    title: remoteConversation.title,
                    createdAt: remoteConversation.createdAt,
                    updatedAt: remoteConversation.updatedAt,
                    model: remoteConversation.model
                )
            }
        } catch {
            self.error = error.localizedDescription
        }
        isLoading = false
    }
}
