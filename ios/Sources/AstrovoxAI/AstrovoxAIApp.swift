import SwiftUI

@main
struct AstrovoxAIApp: App {
    @StateObject private var chatViewModel = ChatViewModel()
    @StateObject private var conversationsViewModel = ConversationsViewModel()

    var body: some Scene {
        WindowGroup {
            NavigationStack {
                ConversationsListView(viewModel: conversationsViewModel)
            }
            .environmentObject(chatViewModel)
            .environmentObject(conversationsViewModel)
        }
        .windowStyle(.titleBar)
        .windowResizability(.contentSize)
    }
}
