package ai.astrovox.services

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.util.xmlb.XmlSerializerUtil

@Service
@State(name = "ai.astrovox.AstrovoxSettings", storages = [Storage("astrovox-settings.xml")])
class AstrovoxSettingsService : PersistentStateComponent<AstrovoxSettingsService.State> {
  data class State(
    var apiKey: String = "",
    var model: String = "gpt-4",
    var maxTokens: Int = 2048,
    var temperature: Double = 0.7,
    var autoComplete: Boolean = false,
    var showStatusBar: Boolean = true
  )

  private var state = State()

  override fun getState(): State = state

  override fun loadState(state: State) {
    this.state = state
  }

  fun getApiKey(): String = state.apiKey
  fun setApiKey(apiKey: String) { state.apiKey = apiKey }
  fun getModel(): String = state.model
  fun setModel(model: String) { state.model = model }
  fun getMaxTokens(): Int = state.maxTokens
  fun setMaxTokens(maxTokens: Int) { state.maxTokens = maxTokens }
  fun getTemperature(): Double = state.temperature
  fun setTemperature(temperature: Double) { state.temperature = temperature }
  fun isAutoCompleteEnabled(): Boolean = state.autoComplete
  fun setAutoComplete(enabled: Boolean) { state.autoComplete = enabled }

  companion object {
    fun getInstance(): AstrovoxSettingsService {
      return ApplicationManager.getApplication().getService(AstrovoxSettingsService::class.java)
    }
  }
}
