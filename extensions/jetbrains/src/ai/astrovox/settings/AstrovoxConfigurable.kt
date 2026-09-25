package ai.astrovox.settings

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.options.ConfigurableProvider
import javax.swing.JComponent
import javax.swing.JTextField
import javax.swing.JCheckBox
import javax.swing.JPanel
import javax.swing.BoxLayout
import ai.astrovox.services.AstrovoxSettingsService

class AstrovoxConfigurable : Configurable {
  private val settings = AstrovoxSettingsService.getInstance()
  private var apiKeyField: JTextField? = null
  private var modelField: JTextField? = null
  private var maxTokensField: JTextField? = null
  private var temperatureField: JTextField? = null
  private var autoCompleteCheck: JCheckBox? = null
  private var showStatusBarCheck: JCheckBox? = null
  private var mainPanel: JPanel? = null

  override fun getDisplayName(): String = "Astrovox AI"

  override fun createComponent(): JComponent {
    mainPanel = JPanel().apply {
      layout = BoxLayout(this, BoxLayout.Y_AXIS)
      border = javax.swing.border.EmptyBorder(20, 20, 20, 20)
    }

    apiKeyField = createTextField("API Key:", settings.getApiKey())
    modelField = createTextField("Model:", settings.getModel())
    maxTokensField = createTextField("Max Tokens:", settings.getMaxTokens().toString())
    temperatureField = createTextField("Temperature:", settings.getTemperature().toString())
    autoCompleteCheck = createCheckBox("Enable Auto Complete", settings.isAutoCompleteEnabled())
    showStatusBarCheck = createCheckBox("Show Status Bar", settings.showStatusBar)

    return mainPanel!!
  }

  private fun createTextField(label: String, value: String): JTextField {
    val panel = JPanel().apply {
      layout = java.awt.BorderLayout(8, 0)
      maximumSize = java.awt.Dimension(Int.MAX_VALUE, 30)
    }
    val labelComponent = javax.swing.JLabel(label)
    val textField = JTextField(value, 30)
    panel.add(labelComponent, java.awt.BorderLayout.WEST)
    panel.add(textField, java.awt.BorderLayout.CENTER)
    mainPanel?.add(panel)
    return textField
  }

  private fun createCheckBox(label: String, selected: Boolean): JCheckBox {
    val checkBox = JCheckBox(label, selected)
    mainPanel?.add(checkBox)
    return checkBox
  }

  override fun isModified(): Boolean {
    return apiKeyField?.text != settings.getApiKey() ||
      modelField?.text != settings.getModel() ||
      maxTokensField?.text != settings.getMaxTokens().toString() ||
      temperatureField?.text != settings.getTemperature().toString() ||
      autoCompleteCheck?.isSelected != settings.isAutoCompleteEnabled() ||
      showStatusBarCheck?.isSelected != settings.showStatusBar
  }

  override fun apply() {
    apiKeyField?.text?.let { settings.setApiKey(it) }
    modelField?.text?.let { settings.setModel(it) }
    maxTokensField?.text?.toIntOrNull()?.let { settings.setMaxTokens(it) }
    temperatureField?.text?.toDoubleOrNull()?.let { settings.setTemperature(it) }
    autoCompleteCheck?.isSelected?.let { settings.setAutoComplete(it) }
    settings.showStatusBar = showStatusBarCheck?.isSelected ?: true
  }

  override fun reset() {
    apiKeyField?.text = settings.getApiKey()
    modelField?.text = settings.getModel()
    maxTokensField?.text = settings.getMaxTokens().toString()
    temperatureField?.text = settings.getTemperature().toString()
    autoCompleteCheck?.isSelected = settings.isAutoCompleteEnabled()
    showStatusBarCheck?.isSelected = settings.showStatusBar
  }

  override fun disposeUIResources() {
    apiKeyField = null
    modelField = null
    maxTokensField = null
    temperatureField = null
    autoCompleteCheck = null
    showStatusBarCheck = null
    mainPanel = null
  }
}

class AstrovoxConfigurableProvider : ConfigurableProvider() {
  override fun createConfigurable(): Configurable? {
    return AstrovoxConfigurable()
  }
}
