import Foundation

struct User: Codable, Equatable {
    let id: String
    let email: String
    let fullName: String
    let createdAt: Date
}
