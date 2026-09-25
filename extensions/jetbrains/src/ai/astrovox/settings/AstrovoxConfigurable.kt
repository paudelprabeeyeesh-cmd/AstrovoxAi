package ai.astrovox.settings

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.options.ConfigurationException
import com.intellij.ui.components.JBTextField
import com.intellij.ui.components.JBCheckBox
import com.intellij.ui.components.JBSpinner
import javax.swing.*
import java.awt.*

class AstrovoxConfigurable : Configurable {
  private lateinit var apiKeyField: JBTextField
  private lateinit var modelField: JBTextField
  private lateinit var maxTokensSpinner: JBSpinner
  private lateinit var temperatureSpinner: JBSpinner
  private lateinit var autoUpdateCheckbox: JBCheckBox
  private lateinit var updateIntervalField: JBTextField
  private lateinit var showStatusBarCheckbox: JBCheckBox

  private val settingsService = com.intellij.openapi.application.ApplicationManager.getApplication()
    .getService(ai.astrovox.services.AstrovoxSettingsService::class.java)

  override fun getDisplayName() = "Astrovox AI"

  override fun createComponent(): JComponent {
    val panel = JPanel().apply {
      layout = GridBagLayout()
      border = javax.swing.BorderFactory.createEmptyBorder(16, 16, 16, 16)
    }

    apiKeyField = JBTextField()
    modelField = JBTextField("gpt-4")
    maxTokensSpinner = JBSpinner(SpinnerNumberModel(2048, 1, 128000, 1))
    temperatureSpinner = JBSpinner(SpinnerNumberModel(0.7, 0.0, 2.0, 0.1))
    autoUpdateCheckbox = JBCheckBox("Auto-check for updates", true)
    updateIntervalField = JBTextField("24")
    showStatusBarCheckbox = JBCheckBox("Show status bar item", true)

    val gbc = GridBagConstraints()
    gbc.insets = Insets(8, 8, 8, 8)
    gbc.anchor = GridBagConstraints.WEST
    gbc.fill = GridBagConstraints.HORIZONTAL

    gbc.gridx = 0; gbc.gridy = 0
    panel.add(JLabel("API Key:"), gbc)
    gbc.gridx = 1; gbc.weightx = 1.0
    panel.add(apiKeyField, gbc)

    gbc.gridx = 0; gbc.gridy = 1; gbc.weightx = 0.0
    panel.add(JLabel("Default Model:"), gbc)
    gbc.gridx = 1; gbc.weightx = 1.0
    panel.add(modelField, gbc)

    gbc.gridx = 0; gbc.gridy = 2; gbc.weightx = 0.0
    panel.add(JLabel("Max Tokens:"), gbc)
    gbc.gridx = 1; gbc.weightx = 1.0
    panel.add(maxTokensSpinner, gbc)

    gbc.gridx = 0; gbc.gridy = 3; gbc.weightx = 0.0
    panel.add(JLabel("Temperature:"), gbc)
    gbc.gridx = 1; gbc.weightx = 1.0
    panel.add(temperatureSpinner, gbc)

    gbc.gridx = 0; gbc.gridy = 4; gbc.gridwidth = 2
    panel.add(showStatusBarCheckbox, gbc)

    gbc.gridx = 0; gbc.gridy = 5; gbc.gridwidth = 2
    panel.add(autoUpdateCheckbox, gbc)

    gbc.gridx = 0; gbc.gridy = 6; gbc.gridwidth = 1; gbc.weightx = 0.0
    panel.add(JLabel("Update Interval (hours):"), gbc)
    gbc.gridx = 1; gbc.weightx = 1.0
    panel.add(updateIntervalField, gbc)

    return panel
  }

  override fun isModified(): Boolean {
    return apiKeyField.text != (settingsService?.apiKey ?: "") ||
      modelField.text != (settingsService?.model ?: "gpt-4") ||
      (maxTokensSpinner.value as Int) != (settingsService?.maxTokens ?: 2048) ||
      (temperatureSpinner.value as Double) != (settingsService?.temperature ?: 0.7) ||
      autoUpdateCheckbox.isSelected != (settingsService?.autoUpdate ?: true) ||
      showStatusBarCheckbox.isSelected != (settingsService?.showStatusBar ?: true)
  }

  @Throws(ConfigurationException::class)
  override fun apply() {
    settingsService?.apiKey = apiKeyField.text
    settingsService?.model = modelField.text
    settingsService?.maxTokens = (maxTokensSpinner.value as Int).coerceAtLeast(1)
    settingsService?.temperature = (temperatureSpinner.value as Double).coerceIn(0.0, 2.0)
    settingsService?.autoUpdate = autoUpdateCheckbox.isSelected
    settingsService?.updateCheckIntervalHours = updateIntervalField.text.toIntOrNull() ?: 24
    settingsService?.showStatusBar = showStatusBarCheckbox.isSelected
    settingsService?.saveSettings()

    if (autoUpdateCheckbox.isSelected) {
      settingsService?.startUpdateChecker()
    } else {
      settingsService?.stopUpdateChecker()
    }
  }

  override fun reset() {
    settingsService?.loadSettings()
    apiKeyField.text = settingsService?.apiKey ?: ""
    modelField.text = settingsService?.model ?: "gpt-4"
    maxTokensSpinner.value = settingsService?.maxTokens ?: 2048
    temperatureSpinner.value = settingsService?.temperature ?: 0.7
    autoUpdateCheckbox.isSelected = settingsService?.autoUpdate ?: true
    showStatusBarCheckbox.isSelected = settingsService?.showStatusBar ?: true
  }
}
