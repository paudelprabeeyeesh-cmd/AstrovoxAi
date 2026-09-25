package ai.astrovox.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.project.Project
import javax.swing.SwingWorker
import java.net.HttpURLConnection
import java.net.URL
import java.io.OutputStreamWriter
import java.io.BufferedReader
import java.io.InputStreamReader

class AstrovoxClient {
  companion object {
    private const val API_BASE = "https://api.astrovox.ai/v1"

    fun getApiKey(): String {
      return com.intellij.openapi.application.ApplicationManager.getApplication()
        .getService(ai.astrovox.services.AstrovoxSettingsService::class.java)
        ?.getApiKey() ?: ""
    }

    fun callAPI(endpoint: String, data: Map<String, Any>): Map<String, Any> {
      val apiKey = getApiKey()
      if (apiKey.isEmpty()) {
        throw IllegalStateException("API key not configured")
      }

      val url = URL("$API_BASE$endpoint")
      val conn = url.openConnection() as HttpURLConnection
      conn.requestMethod = "POST"
      conn.setRequestProperty("Content-Type", "application/json")
      conn.setRequestProperty("Authorization", "Bearer $apiKey")
      conn.doOutput = true

      OutputStreamWriter(conn.outputStream).use { writer ->
        writer.write(com.google.gson.Gson().toJson(data))
        writer.flush()
      }

      val response = StringBuilder()
      BufferedReader(InputStreamReader(conn.inputStream)).use { reader ->
        var line: String?
        while (reader.readLine().also { line = it } != null) {
          response.append(line)
        }
      }

      return com.google.gson.Gson().fromJson(response.toString(), Map::class.java) as Map<String, Any>
    }
  }
}

class StartChatAction : AnAction() {
  override fun actionPerformed(e: AnActionEvent) {
    Messages.showInfoMessage("Astrovox AI chat panel is available in the right sidebar.", "Astrovox AI")
  }
}

class ExplainCodeAction : AnAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val editor = e.getData(com.intellij.openapi.actionSystem.CommonDataKeys.EDITOR) ?: return
    val code = editor.selectionModel.selectedText
    if (code.isNullOrEmpty()) {
      Messages.showWarningDialog("Please select some code first.", "Astrovox AI")
      return
    }

    object : SwingWorker<String, Void>() {
      override fun doInBackground(): String {
        return try {
          val result = AstrovoxClient.callAPI("/explain", mapOf("code" to code, "language" to editor.document.languageId))
          result["explanation"]?.toString() ?: result["content"]?.toString() ?: "No explanation available"
        } catch (ex: Exception) {
          "Error: ${ex.message}"
        }
      }

      override fun done() {
        try {
          Messages.showInfoMessage(get(), "Code Explanation")
        } catch (ex: Exception) {
          Messages.showErrorDialog("Failed to show explanation: ${ex.message}", "Astrovox AI")
        }
      }
    }.execute()
  }
}

class GenerateTestsAction : AnAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val editor = e.getData(com.intellij.openapi.actionSystem.CommonDataKeys.EDITOR) ?: return
    val code = editor.selectionModel.selectedText
    if (code.isNullOrEmpty()) {
      Messages.showWarningDialog("Please select some code first.", "Astrovox AI")
      return
    }

    object : SwingWorker<String, Void>() {
      override fun doInBackground(): String {
        return try {
          val result = AstrovoxClient.callAPI("/generate-tests", mapOf("code" to code, "language" to editor.document.languageId))
          result["tests"]?.toString() ?: result["content"]?.toString() ?: "No tests generated"
        } catch (ex: Exception) {
          "Error: ${ex.message}"
        }
      }

      override fun done() {
        try {
          val project = e.project
          if (project != null) {
            val doc = com.intellij.openapi.command.WriteCommandAction.writeCommandAction(project).compute {
              com.intellij.openapi.fileEditor.FileDocumentManager.getInstance().getDocument(com.intellij.psi.PsiFileFactory.getInstance(project).createFileFromText("GeneratedTests.${editor.document.languageId}", get()))
            }
            com.intellij.openapi.wm.ToolWindowManager.getInstance(project).getEditorManager(project).openEditor(doc!!, true)
          }
        } catch (ex: Exception) {
          Messages.showErrorDialog("Failed to generate tests: ${ex.message}", "Astrovox AI")
        }
      }
    }.execute()
  }
}

class RefactorCodeAction : AnAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val editor = e.getData(com.intellij.openapi.actionSystem.CommonDataKeys.EDITOR) ?: return
    val project = e.project ?: return
    val code = editor.selectionModel.selectedText
    if (code.isNullOrEmpty()) {
      Messages.showWarningDialog("Please select some code first.", "Astrovox AI")
      return
    }

    object : SwingWorker<String, Void>() {
      override fun doInBackground(): String {
        return try {
          val result = AstrovoxClient.callAPI("/refactor", mapOf("code" to code, "language" to editor.document.languageId))
          result["refactored"]?.toString() ?: result["content"]?.toString() ?: code
        } catch (ex: Exception) {
          code
        }
      }

      override fun done() {
        try {
          com.intellij.openapi.command.WriteCommandAction.writeCommandAction(project).run {
            editor.document.replaceString(editor.selectionModel.selectionStart, editor.selectionModel.selectionEnd, get())
          }
        } catch (ex: Exception) {
          Messages.showErrorDialog("Failed to refactor code: ${ex.message}", "Astrovox AI")
        }
      }
    }.execute()
  }
}

class ReviewCodeAction : AnAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val editor = e.getData(com.intellij.openapi.actionSystem.CommonDataKeys.EDITOR) ?: return
    val code = editor.selectionModel.selectedText
    if (code.isNullOrEmpty()) {
      Messages.showWarningDialog("Please select some code first.", "Astrovox AI")
      return
    }

    object : SwingWorker<String, Void>() {
      override fun doInBackground(): String {
        return try {
          val result = AstrovoxClient.callAPI("/review", mapOf("code" to code, "language" to editor.document.languageId))
          result["review"]?.toString() ?: result["content"]?.toString() ?: "No review available"
        } catch (ex: Exception) {
          "Error: ${ex.message}"
        }
      }

      override fun done() {
        try {
          Messages.showInfoMessage(get(), "Code Review")
        } catch (ex: Exception) {
          Messages.showErrorDialog("Failed to review code: ${ex.message}", "Astrovox AI")
        }
      }
    }.execute()
  }
}

class DocumentCodeAction : AnAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val editor = e.getData(com.intellij.openapi.actionSystem.CommonDataKeys.EDITOR) ?: return
    val project = e.project ?: return
    val code = editor.selectionModel.selectedText
    if (code.isNullOrEmpty()) {
      Messages.showWarningDialog("Please select some code first.", "Astrovox AI")
      return
    }

    object : SwingWorker<String, Void>() {
      override fun doInBackground(): String {
        return try {
          val result = AstrovoxClient.callAPI("/document", mapOf("code" to code, "language" to editor.document.languageId))
          result["documentation"]?.toString() ?: result["content"]?.toString() ?: ""
        } catch (ex: Exception) {
          ""
        }
      }

      override fun done() {
        try {
          com.intellij.openapi.command.WriteCommandAction.writeCommandAction(project).run {
            editor.document.insertString(editor.selectionModel.selectionEnd, "\n\n" + get())
          }
        } catch (ex: Exception) {
          Messages.showErrorDialog("Failed to document code: ${ex.message}", "Astrovox AI")
        }
      }
    }.execute()
  }
}

class FixBugAction : AnAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val editor = e.getData(com.intellij.openapi.actionSystem.CommonDataKeys.EDITOR) ?: return
    val project = e.project ?: return
    val code = editor.selectionModel.selectedText
    if (code.isNullOrEmpty()) {
      Messages.showWarningDialog("Please select some code first.", "Astrovox AI")
      return
    }

    val bugDescription = Messages.showInputDialog(project, "Describe the bug:", "Fix Bug with Astrovox", null)
    if (bugDescription.isNullOrEmpty()) return

    object : SwingWorker<String, Void>() {
      override fun doInBackground(): String {
        return try {
          val result = AstrovoxClient.callAPI("/fix-bug", mapOf("code" to code, "bug_description" to bugDescription, "language" to editor.document.languageId))
          result["fixed_code"]?.toString() ?: result["content"]?.toString() ?: code
        } catch (ex: Exception) {
          code
        }
      }

      override fun done() {
        try {
          com.intellij.openapi.command.WriteCommandAction.writeCommandAction(project).run {
            editor.document.replaceString(editor.selectionModel.selectionStart, editor.selectionModel.selectionEnd, get())
          }
        } catch (ex: Exception) {
          Messages.showErrorDialog("Failed to fix bug: ${ex.message}", "Astrovox AI")
        }
      }
    }.execute()
  }
}
