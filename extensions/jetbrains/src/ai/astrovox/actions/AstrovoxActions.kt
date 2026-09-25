package ai.astrovox.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.ui.Messages
import ai.astrovox.services.AstrovoxSettingsService

abstract class BaseAstrovoxAction : AnAction() {
  protected val settingsService = com.intellij.openapi.application.ApplicationManager.getApplication()
    .getService(AstrovoxSettingsService::class.java)

  override fun update(e: AnActionEvent) {
    e.presentation.isEnabledAndVisible = settingsService?.isConfigured() ?: false
  }

  protected fun getSelectedCode(e: AnActionEvent): String? {
    val editor = e.getData(CommonDataKeys.EDITOR) ?: return null
    val selection = editor.selectionModel.selectedText
    if (!selection.isNullOrEmpty()) return selection
    return editor.document.text
  }

  protected fun getLanguage(e: AnActionEvent): String {
    val editor = e.getData(CommonDataKeys.EDITOR) ?: return "unknown"
    return editor.document.languageID
  }
}

class StartChatAction : BaseAstrovoxAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val toolWindowManager = com.intellij.openapi.wm.ToolWindowManager.getInstance(e.project!!)
    val toolWindow = toolWindowManager.getToolWindow("Astrovox Chat")
    toolWindow?.show(null)
  }
}

class ExplainCodeAction : BaseAstrovoxAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val code = getSelectedCode(e) ?: return
    val language = getLanguage(e)
    performRequest("explain", code, language, e) { result ->
      Messages.showInfoMessage(e.project, result, "Astrovox Explanation")
    }
  }
}

class GenerateTestsAction : BaseAstrovoxAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val code = getSelectedCode(e) ?: return
    val language = getLanguage(e)
    performRequest("generate-tests", code, language, e) { result ->
      val editor = e.getData(CommonDataKeys.EDITOR)
      val document = editor?.document
      if (document != null) {
        com.intellij.openapi.command.WriteCommandAction.runWriteCommandAction(e.project) {
          document.insertString(document.textLength, "\n\n$result")
        }
      }
    }
  }
}

class RefactorCodeAction : BaseAstrovoxAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val code = getSelectedCode(e) ?: return
    val language = getLanguage(e)
    performRequest("refactor", code, language, e) { result ->
      val editor = e.getData(CommonDataKeys.EDITOR) ?: return@performRequest
      val selectionModel = editor.selectionModel
      com.intellij.openapi.command.WriteCommandAction.runWriteCommandAction(e.project) {
        editor.document.replaceString(selectionModel.selectionStart, selectionModel.selectionEnd, result)
      }
    }
  }
}

class ReviewCodeAction : BaseAstrovoxAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val code = getSelectedCode(e) ?: return
    val language = getLanguage(e)
    performRequest("review", code, language, e) { result ->
      Messages.showInfoMessage(e.project, result, "Astrovox Code Review")
    }
  }
}

class DocumentCodeAction : BaseAstrovoxAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val code = getSelectedCode(e) ?: return
    val language = getLanguage(e)
    performRequest("document", code, language, e) { result ->
      val editor = e.getData(CommonDataKeys.EDITOR) ?: return@performRequest
      com.intellij.openapi.command.WriteCommandAction.runWriteCommandAction(e.project) {
        editor.document.insertString(editor.caretModel.offset, result)
      }
    }
  }
}

class FixBugAction : BaseAstrovoxAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val code = getSelectedCode(e) ?: return
    val language = getLanguage(e)
    val bugDescription = Messages.showInputDialog(e.project, "Describe the bug:", "Fix Bug", null) ?: return
    performRequest("fix-bug", code, language, e, mapOf("bug_description" to bugDescription)) { result ->
      val editor = e.getData(CommonDataKeys.EDITOR) ?: return@performRequest
      val selectionModel = editor.selectionModel
      com.intellij.openapi.command.WriteCommandAction.runWriteCommandAction(e.project) {
        editor.document.replaceString(selectionModel.selectionStart, selectionModel.selectionEnd, result)
      }
    }
  }
}

class OptimizeCodeAction : BaseAstrovoxAction() {
  override fun actionPerformed(e: AnActionEvent) {
    val code = getSelectedCode(e) ?: return
    val language = getLanguage(e)
    performRequest("optimize", code, language, e) { result ->
      val editor = e.getData(CommonDataKeys.EDITOR) ?: return@performRequest
      val selectionModel = editor.selectionModel
      com.intellij.openapi.command.WriteCommandAction.runWriteCommandAction(e.project) {
        editor.document.replaceString(selectionModel.selectionStart, selectionModel.selectionEnd, result)
      }
    }
  }
}

class AstrovoxUpdateAction : BaseAstrovoxAction() {
  override fun actionPerformed(e: AnActionEvent) {
    settingsService?.checkForUpdates()
    Messages.showInfoMessage(e.project, "Checking for updates...", "Astrovox Update")
  }
}

private fun performRequest(
  endpoint: String,
  code: String,
  language: String,
  e: AnActionEvent,
  extraParams: Map<String, String> = emptyMap(),
  onResult: (String) -> Unit
) {
  val service = settingsService ?: return
  if (!service.isConfigured()) {
    Messages.showWarningDialog(e.project, "Please configure your Astrovox API key in Settings.", "API Key Required")
    return
  }

  val progressIndicator = com.intellij.openapi.progress.ProgressManager.getGlobalProgressIndicator()
  if (progressIndicator != null) {
    progressIndicator.isIndeterminate = true
  }

  com.intellij.openapi.application.ApplicationManager.getApplication().executeOnPooledThread {
    try {
      val client = okhttp3.OkHttpClient.Builder()
        .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(120, java.util.concurrent.TimeUnit.SECONDS)
        .build()

      val bodyJson = org.json.JSONObject().apply {
        put("code", code)
        put("language", language)
        extraParams.forEach { (k, v) -> put(k, v) }
      }

      val request = okhttp3.Request.Builder()
        .url("https://api.astrovox.ai/v1/$endpoint")
        .post(okhttp3.RequestBody.create(bodyJson.toString(), okhttp3.MediaType.parse("application/json")))
        .addHeader("Authorization", "Bearer ${service.apiKey}")
        .addHeader("Content-Type", "application/json")
        .build()

      client.newCall(request).execute().use { response ->
        val responseBody = response.body?.string() ?: ""
        val data = org.json.JSONObject(responseBody)
        val result = when {
          data.has("content") -> data.getString("content")
          data.has("explanation") -> data.getString("explanation")
          data.has("refactored") -> data.getString("refactored")
          data.has("tests") -> data.getString("tests")
          data.has("review") -> data.getString("review")
          data.has("fixed_code") -> data.getString("fixed_code")
          data.has("optimized_code") -> data.getString("optimized_code")
          data.has("documentation") -> data.getString("documentation")
          else -> responseBody
        }

        com.intellij.openapi.application.ApplicationManager.getApplication().invokeLater {
          onResult(result)
        }
      }
    } catch (ex: Exception) {
      com.intellij.openapi.application.ApplicationManager.getApplication().invokeLater {
        Messages.showErrorDialog(e.project, "Astrovox error: ${ex.message}", "Error")
      }
    } finally {
      progressIndicator?.isIndeterminate = false
    }
  }
}
