package ai.astrovox.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.ui.Messages

class StartChatAction : AnAction() {
  override fun actionPerformed(e: AnActionEvent) {
    Messages.showInfoMessage("Astrovox AI chat coming soon", "Astrovox AI")
  }
}

class ExplainCodeAction : AnAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val editor = e.project?.let { com.intellij.openapi.editor.EditorFactory.getInstance().createEditor(it) }
    Messages.showInfoMessage("Code explanation coming soon", "Astrovox AI")
  }
}

class GenerateTestsAction : AnAction() {
  override fun actionPerformed(e: AnActionEvent) {
    Messages.showInfoMessage("Test generation coming soon", "Astrovox AI")
  }
}
