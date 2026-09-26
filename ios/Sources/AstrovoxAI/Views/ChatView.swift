import SwiftUI

struct ChatView: View {
    let conversationId: String
    @EnvironmentObject var viewModel: ChatViewModel
    @State private var messageText: String = ""

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(viewModel.messages) { message in
                            MessageBubble(message: message)
                                .id(message.id)
                        }
                        if viewModel.isLoading {
                            ProgressView()
                                .padding()
                        }
                    }
                    .padding()
                }
                .onChange(of: viewModel.messages.count) { _ in
                    if let last = viewModel.messages.last {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }

            Divider()

            HStack(spacing: 12) {
                TextField("Ask Astrovox...", text: $messageText)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        Task { await send() }
                    }

                Button(action: {
                    Task { await send() }
                }) {
                    Text("Send")
                        .bold()
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(Color.accentColor)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
                .disabled(messageText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            .padding()
        }
        .navigationTitle("Astrovox AI")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func send() async {
        let text = messageText
        messageText = ""
        await viewModel.send(message: text)
    }
}

struct MessageBubble: View {
    let message: Message
    var body: some View {
        HStack {
            if message.role == "user" { Spacer() }
            Text(message.content)
                .padding(10)
                .background(message.role == "user" ? Color.accentColor : Color(white: 0.12))
                .foregroundStyle(message.role == "user" ? .white : .primary)
                .clipShape(RoundedRectangle(cornerRadius: 12))
            if message.role != "user" { Spacer() }
        }
    }
}
