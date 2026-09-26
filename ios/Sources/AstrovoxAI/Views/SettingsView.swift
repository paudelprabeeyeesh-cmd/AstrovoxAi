import SwiftUI

struct SettingsView: View {
    @AppStorage("astrovox_api_key") private var apiKey: String = ""
    @AppStorage("astrovox_model") private var model: String = "gpt-4"
    @AppStorage("astrovox_max_tokens") private var maxTokens: Int = 2048
    @AppStorage("astrovox_temperature") private var temperature: Double = 0.7

    var body: some View {
        Form {
            Section("API") {
                SecureField("API Key", text: $apiKey)
                TextField("Model", text: $model)
            }

            Section("Generation") {
                Stepper("Max Tokens: \(maxTokens)", value: $maxTokens, in: 256...8192, step: 256)
                Slider(value: $temperature, in: 0...2, step: 0.1)
                Text("Temperature: \(temperature, specifier: "%.1f")")
                    .font(.caption)
            }
        }
        .navigationTitle("Settings")
    }
}
