package ai.astrovox

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.content.Content
import com.intellij.ui.content.ContentFactory
import javax.swing.*

class ChatToolWindowFactory : ToolWindowFactory {
  override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
    val contentFactory = ContentFactory.getInstance()
    val panel = JPanel().apply {
      layout = BoxLayout(this, BoxLayout.Y_AXIS)
      add(JLabel("Astrovox AI Chat"))
      add(JTextArea().apply {
        rows = 20
        columns = 50
        lineWrap = true
        wrapStyleWord = true
      })
    }
    val content = contentFactory.createContent(panel, "", false)
    toolWindow.contentManager.addContent(content)
  }
}
