import SwiftUI

@main
struct AstrovoxAIApp: App {
    @StateObject private var chatViewModel = ChatViewModel()
    @StateObject private var conversationsViewModel = ConversationsViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(chatViewModel)
                .environmentObject(conversationsViewModel)
        }
    }
}
