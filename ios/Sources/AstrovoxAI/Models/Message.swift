import Foundation

struct Message: Identifiable, Codable, Equatable {
    let id: String
    let conversationId: String
    let role: String
    let content: String
    let timestamp: Date
    let offline: Bool
}
