package ai.astrovox.presentation.chat

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import ai.astrovox.domain.model.Message

@Composable
fun ChatScreen(viewModel: ChatViewModel, conversationId: String, onError: (String) -> Unit = {}) {
    val state by viewModel.state.collectAsState()
    var message by remember { mutableStateOf("") }

    LaunchedEffect(state.error) {
        state.error?.let { onError(it) }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth().padding(16.dp),
            reverseLayout = true
        ) {
            items(state.messages) { msg ->
                MessageBubble(message = msg)
                Spacer(modifier = Modifier.height(8.dp))
            }
            if (state.isLoading) {
                item {
                    CircularProgressIndicator(modifier = Modifier.padding(16.dp))
                }
            }
        }
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = message,
                onValueChange = { message = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("Ask Astrovox...") }
            )
            Spacer(modifier = Modifier.width(8.dp))
            Button(onClick = {
                if (message.isNotBlank()) {
                    viewModel.send(message.trim(), conversationId)
                    message = ""
                }
            }) {
                Text("Send")
            }
        }
    }
}

@Composable
fun MessageBubble(message: Message) {
    val isUser = message.role == "user"
    val backgroundColor = if (isUser) Color(0xFF0EA5E9) else Color(0xFF1F2430)
    val textColor = if (isUser) Color(0xFF0B1220) else Color(0xFFE6E8EB)
    val alignment = if (isUser) Arrangement.End else Arrangement.Start

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = alignment
    ) {
        Surface(
            modifier = Modifier.widthIn(max = 280.dp),
            shape = RoundedCornerShape(12.dp),
            color = backgroundColor,
            contentColor = textColor
        ) {
            Text(text = message.content, modifier = Modifier.padding(12.dp))
        }
    }
}
