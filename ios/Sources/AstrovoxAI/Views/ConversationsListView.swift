import SwiftUI

struct ConversationsListView: View {
    @ObservedObject var viewModel: ConversationsViewModel
    @State private var selectedConversation: String? = nil

    var body: some View {
        NavigationStack(path: $selectedConversation) {
            List(viewModel.conversations) { conversation in
                NavigationLink(value: conversation.id) {
                    VStack(alignment: .leading) {
                        Text(conversation.title)
                            .font(.headline)
                        Text("Model: \(conversation.model)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Conversations")
            .navigationDestination(for: String.self) { conversationId in
                ChatView(conversationId: conversationId)
            }
            .task {
                await viewModel.loadConversations()
            }
        }
    }
}
