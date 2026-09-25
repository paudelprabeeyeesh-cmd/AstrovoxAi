package ai.astrovox

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.content.Content
import com.intellij.ui.content.ContentFactory
import javax.swing.*
import java.awt.*
import javax.swing.border.EmptyBorder

class ChatToolWindowFactory : ToolWindowFactory {
  override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
    val contentFactory = ContentFactory.getInstance()
    val panel = JPanel().apply {
      layout = BorderLayout()
      border = EmptyBorder(16, 16, 16, 16)
      background = Color(2, 4, 10)
    }

    val header = JPanel().apply {
      layout = FlowLayout(FlowLayout.LEFT, 8, 0)
      background = Color(2, 4, 10)
      add(JLabel("ASTROVOX AI").apply {
        foreground = Color(103, 232, 249)
        font = font.deriveFont(Font.BOLD, 14f)
      })
    }

    val chatArea = JTextArea().apply {
      isEditable = false
      background = Color(15, 23, 42)
      foreground = Color(226, 232, 240)
      font = Font("Monospaced", Font.PLAIN, 12)
      lineWrap = true
      wrapStyleWord = true
      text = "Welcome to Astrovox AI. Select code and use actions to get started."
      border = EmptyBorder(8, 8, 8, 8)
    }

    val inputPanel = JPanel().apply {
      layout = BorderLayout(8, 0)
      background = Color(2, 4, 10)
      border = EmptyBorder(8, 0, 0, 0)
    }

    val inputField = JTextField().apply {
      background = Color(5, 10, 24)
      foreground = Color(103, 232, 249)
      caretColor = Color(103, 232, 249)
      font = Font("Monospaced", Font.PLAIN, 12)
      border = BorderFactory.createCompoundBorder(
        BorderFactory.createLineBorder(Color(30, 41, 59)),
        EmptyBorder(8, 12, 8, 12)
      )
    }

    val sendButton = JButton("SEND").apply {
      background = Color(6, 182, 212)
      foreground = Color(2, 4, 10)
      isFocusPainted = false
      font = font.deriveFont(Font.BOLD, 12f)
      addActionListener {
        val message = inputField.text.trim()
        if (message.isNotEmpty()) {
          chatArea.append("\n\nYou: $message")
          inputField.text = ""
          chatArea.append("\n\nAstrovox: Thinking...")
        }
      }
    }

    inputPanel.add(inputField, BorderLayout.CENTER)
    inputPanel.add(sendButton, BorderLayout.EAST)

    panel.add(header, BorderLayout.NORTH)
    panel.add(JScrollPane(chatArea), BorderLayout.CENTER)
    panel.add(inputPanel, BorderLayout.SOUTH)

    val content = contentFactory.createContent(panel, "", false)
    toolWindow.contentManager.addContent(content)
  }
}
