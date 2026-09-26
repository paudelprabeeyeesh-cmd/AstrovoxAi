import Foundation

struct Conversation: Identifiable, Codable, Equatable {
    let id: String
    let title: String
    let createdAt: Date
    let updatedAt: Date
    let model: String
}
