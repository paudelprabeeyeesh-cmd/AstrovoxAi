import SwiftUI

struct Message: Identifiable, Codable {
    let id: UUID
    var role: String
    var content: String
    var timestamp: Date?
}

struct Conversation: Identifiable, Codable {
    let id: UUID
    var title: String
    var messages: [Message]
    var model: String
    var createdAt: Date?
}
