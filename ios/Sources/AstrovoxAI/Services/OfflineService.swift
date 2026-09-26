import Foundation
import CoreData

@objc(OfflineService)
class OfflineService: NSObject {
    static let shared = OfflineService()

    private override init() {
        super.init()
    }

    func saveMessage(_ message: Message, context: NSManagedObjectContext) throws {
        let entity = OfflineMessageEntity(context: context)
        entity.id = message.id
        entity.conversationId = message.conversationId
        entity.role = message.role
        entity.content = message.content
        entity.timestamp = message.timestamp
        entity.offline = message.offline
        try context.save()
    }

    func fetchMessages(conversationId: String, context: NSManagedObjectContext) throws -> [Message] {
        let request = NSFetchRequest<OfflineMessageEntity>(entityName: "OfflineMessageEntity")
        request.predicate = NSPredicate(format: "conversationId == %@", conversationId)
        request.sortDescriptors = [NSSortDescriptor(key: "timestamp", ascending: true)]
        let results = try context.fetch(request)
        return results.map { entity in
            Message(
                id: entity.id ?? UUID().uuidString,
                conversationId: entity.conversationId ?? "",
                role: entity.role ?? "",
                content: entity.content ?? "",
                timestamp: entity.timestamp ?? Date(),
                offline: entity.offline
            )
        }
    }
}

@objc(OfflineMessageEntity)
class OfflineMessageEntity: NSManagedObject {
    @NSManaged var id: String?
    @NSManaged var conversationId: String?
    @NSManaged var role: String?
    @NSManaged var content: String?
    @NSManaged var timestamp: Date
    @NSManaged var offline: Bool
}
