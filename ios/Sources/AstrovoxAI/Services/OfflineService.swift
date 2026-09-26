import Foundation

@MainActor
class OfflineService: ObservableObject {
    static let shared = OfflineService()
    private let storageURL: URL = {
        let urls = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
        let dir = urls[0].appendingPathComponent("AstrovoxAI", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("offline_messages.json")
    }()

    private var messages: [Message] = []

    private init() {
        load()
    }

    func saveMessage(_ message: Message) {
        messages.append(message)
        persist()
    }

    func fetchMessages(conversationId: String) -> [Message] {
        messages.filter { $0.conversationId == conversationId }
    }

    func clear() {
        messages.removeAll()
        persist()
    }

    private func load() {
        guard let data = try? Data(contentsOf: storageURL),
              let decoded = try? JSONDecoder().decode([Message].self, from: data) else { return }
        messages = decoded
    }

    private func persist() {
        if let data = try? JSONEncoder().encode(messages) {
            try? data.write(to: storageURL)
        }
    }
}
