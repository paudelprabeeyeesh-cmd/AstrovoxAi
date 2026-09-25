package ai.astrovox.services

import com.intellij.openapi.components.Service
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.Logger
import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.TimeUnit

@Service
@State(name = "AstrovoxSettings", storages = [Storage("astrovox.xml")])
class AstrovoxSettingsService {
  private val LOG = Logger.getInstance(AstrovoxSettingsService::class.java)
  private val client = OkHttpClient.Builder()
    .connectTimeout(30, TimeUnit.SECONDS)
    .writeTimeout(30, TimeUnit.SECONDS)
    .readTimeout(120, TimeUnit.SECONDS)
    .build()

  var apiKey: String = ""
  var model: String = "gpt-4"
  var maxTokens: Int = 2048
  var temperature: Double = 0.7
  var conversationId: String = "jetbrains-${System.currentTimeMillis()}"
  var autoUpdate: Boolean = true
  var updateCheckIntervalHours: Int = 24
  var showStatusBar: Boolean = true

  private var updateChecker: java.util.concurrent.ScheduledFuture<*>? = null
  private var latestVersion: String = "1.0.0"
  private var updateAvailable: Boolean = false

  fun getSettings(): Map<String, Any> = mapOf(
    "apiKey" to apiKey,
    "model" to model,
    "maxTokens" to maxTokens,
    "temperature" to temperature,
    "conversationId" to conversationId,
    "autoUpdate" to autoUpdate,
    "showStatusBar" to showStatusBar
  )

  fun loadSettings() {
    val state = ApplicationManager.getApplication().stateStore
    val stored = state?.getState(this)
    stored?.let {
      apiKey = it.apiKey ?: apiKey
      model = it.model ?: model
      maxTokens = it.maxTokens ?: maxTokens
      temperature = it.temperature ?: temperature
      conversationId = it.conversationId ?: conversationId
      autoUpdate = it.autoUpdate ?: autoUpdate
      updateCheckIntervalHours = it.updateCheckIntervalHours ?: updateCheckIntervalHours
      showStatusBar = it.showStatusBar ?: showStatusBar
    }
  }

  fun saveSettings() {
    val state = ApplicationManager.getApplication().stateStore
    state?.setState(this, this)
  }

  fun isConfigured(): Boolean = apiKey.isNotBlank()

  fun startUpdateChecker() {
    if (!autoUpdate || updateChecker != null) return

    val interval = updateCheckIntervalHours.toLong()
    updateChecker = java.util.concurrent.Executors.newSingleThreadScheduledExecutor().scheduleAtFixedRate(
      { checkForUpdates() },
      interval,
      interval,
      java.util.concurrent.TimeUnit.HOURS
    )
  }

  fun stopUpdateChecker() {
    updateChecker?.cancel(false)
    updateChecker = null
  }

  fun checkForUpdates() {
    if (!isConfigured()) return

    ApplicationManager.getApplication().executeOnPooledThread {
      try {
        val request = Request.Builder()
          .url("https://api.astrovox.ai/v1/extensions/jetbrains/latest")
          .header("User-Agent", "astrovox-jetbrains/1.0.0")
          .build()

        client.newCall(request).execute().use { response ->
          if (!response.isSuccessful) return@use

          val body = response.body?.string() ?: return@use
          val data = JSONObject(body)
          val remoteVersion = data.getString("version")

          if (isNewerVersion(remoteVersion, "1.0.0")) {
            latestVersion = remoteVersion
            updateAvailable = true
            showUpdateNotification(data.getString("version"), data.optString("changelog", ""))
          }
        }
      } catch (e: Exception) {
        LOG.warn("Update check failed", e)
      }
    }
  }

  private fun showUpdateNotification(version: String, changelog: String) {
    ApplicationManager.getApplication().invokeLater {
      com.intellij.notification.NotificationGroupManager.getInstance()
        .getNotificationGroup("Astrovox Updates")
        .createNotification(
          "Astrovox AI v$version is available",
          "A new version of Astrovox AI is available. View changelog or ignore this update.",
          com.intellij.notification.NotificationType.INFORMATION
        )
        .addAction(com.intellij.notification.NotificationAction.createSimpleExpiring("View Changelog") {
          showChangelog(version, changelog)
        })
        .addAction(com.intellij.notification.NotificationAction.createSimpleExpiring("Ignore") {})
        .notify(null)
    }
  }

  fun showChangelog(version: String, changelog: String) {
    ApplicationManager.getApplication().invokeLater {
      val dialog = com.intellij.openapi.ui.DialogWrapper(ApplicationManager.getApplication().lastFocusedFrame)
      dialog.title = "Astrovox AI Changelog - v$version"
      dialog.init()
      dialog.show()
    }
  }

  private fun isNewerVersion(remoteVersion: String, localVersion: String): Boolean {
    if (remoteVersion == localVersion) return false
    val normalize = { v: String -> v.split('.').map { it.toIntOrNull() ?: 0 } }
    val remote = normalize(remoteVersion)
    val local = normalize(localVersion)
    for (i in 0 until maxOf(remote.size, local.size)) {
      val r = remote.getOrElse(i) { 0 }
      val l = local.getOrElse(i) { 0 }
      if (r > l) return true
      if (r < l) return false
    }
    return false
  }
}
