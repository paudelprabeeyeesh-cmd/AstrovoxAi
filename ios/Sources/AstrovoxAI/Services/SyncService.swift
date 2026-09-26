import Foundation
import Combine

@MainActor
class SyncService: ObservableObject {
    @Published var isSyncing: Bool = false
    @Published var lastSyncDate: Date?

    private let api = APIService()
    private let offlineService = OfflineService.shared
    private var pendingMessages: [Message] = []

    func enqueue(_ message: Message) {
        pendingMessages.append(message)
        attemptSync()
    }

    func attemptSync() {
        guard !pendingMessages.isEmpty, !isSyncing else { return }
        isSyncing = true
        Task {
            do {
                try await syncPendingMessages()
                pendingMessages.removeAll()
                lastSyncDate = Date()
            } catch {
                print("Sync failed: \(error)")
            }
            isSyncing = false
        }
    }

    private func syncPendingMessages() async throws {
        for message in pendingMessages {
            _ = try await api.sendMessage(
                conversationId: message.conversationId,
                message: message.content,
                model: "gpt-4"
            )
        }
    }
}
