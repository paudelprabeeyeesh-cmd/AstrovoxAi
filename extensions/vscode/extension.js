const vscode = require('vscode')
const axios = require('axios')

const API_BASE = 'https://api.astrovox.ai/v1'
const CONFIG_SECTION = 'astrovox'
const STATE_KEY = 'astrovox_state'
const EXTENSION_VERSION = '1.0.0'
const UPDATE_CHECK_INTERVAL = 24 * 60 * 60 * 1000

class ExtensionUpdateNotifier {
  constructor(context) {
    this.context = context
    this.latestVersion = EXTENSION_VERSION
    this.lastCheck = null
    this.updateAvailable = false
    this.changelog = null
    this.checkInterval = null
  }

  async initialize() {
    this.lastCheck = this.context.globalState.get('lastUpdateCheck')
    if (Date.now() - (this.lastCheck || 0) > UPDATE_CHECK_INTERVAL) {
      this.checkForUpdates()
    }

    this.checkInterval = setInterval(() => this.checkForUpdates(), UPDATE_CHECK_INTERVAL)
    this.context.subscriptions.push(
      vscode.commands.registerCommand('astrovox.checkForUpdates', () => this.checkForUpdates(true)),
      vscode.commands.registerCommand('astrovox.viewChangelog', () => this.viewChangelog())
    )
  }

  async checkForUpdates(force = false) {
    try {
      const response = await axios.get(`${API_BASE}/extensions/vscode/latest`, {
        timeout: 10000,
        headers: { 'User-Agent': `astrovox-vscode/${EXTENSION_VERSION}` }
      }).catch(() => null)

      if (response?.data) {
        const { version, changelog, min_vscode_version, download_url, published_at } = response.data

        if (this.isNewerVersion(version, EXTENSION_VERSION)) {
          this.latestVersion = version
          this.updateAvailable = true
          this.changelog = changelog
          this.lastCheck = Date.now()
          await this.context.globalState.update('lastUpdateCheck', this.lastCheck)
          await this.context.globalState.update('latestVersion', version)

          if (min_vscode_version && !this.isVSCodeVersionSupported(min_vscode_version)) {
            vscode.window.showWarningMessage(
              `Astrovox AI update requires VS Code ${min_vscode_version} or later. Please update VS Code first.`,
              'View Changelog'
            ).then(selection => {
              if (selection === 'View Changelog') {
                vscode.env.openExternal(vscode.Uri.parse(download_url || 'https://github.com/astrovox/astrovox/releases'))
              }
            })
            return
          }

          const action = await vscode.window.showInformationMessage(
            `Astrovox AI v${version} is available!`,
            'Update Now',
            'View Changelog',
            'Later'
          )

          if (action === 'Update Now') {
            await this.performUpdate(download_url)
          } else if (action === 'View Changelog') {
            await this.viewChangelog()
          }
        }
      }
    } catch (e) {
      console.error('Update check failed:', e)
    }
  }

  async performUpdate(downloadUrl) {
    try {
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: 'Updating Astrovox AI...',
          cancellable: false
        },
        async (progress) => {
          progress.report({ increment: 0, message: 'Downloading update...' })
          const url = downloadUrl || 'https://github.com/astrovox/astrovox/releases/latest'
          await vscode.env.openExternal(vscode.Uri.parse(url))

          progress.report({ increment: 100, message: 'Update ready!' })
          await vscode.window.showInformationMessage(
            'Update downloaded. Please install the VSIX and reload the window when prompted.'
          )
        }
      )
    } catch (e) {
      vscode.window.showErrorMessage(`Update failed: ${e.message}`)
    }
  }

  async viewChangelog() {
    try {
      const changelog = this.changelog || await this.fetchChangelog()
      const doc = await vscode.workspace.openTextDocument({
        content: `# Astrovox AI Changelog\n\n## v${this.latestVersion}\n\n${changelog || 'No changelog available.'}\n\n---\n*Released: ${new Date().toLocaleDateString()}*`,
        language: 'markdown'
      })
      await vscode.window.showTextDocument(doc, { viewColumn: vscode.ViewColumn.Beside })
    } catch {
      vscode.env.openExternal(vscode.Uri.parse('https://github.com/astrovox/astrovox/releases'))
    }
  }

  async fetchChangelog() {
    try {
      const response = await axios.get(`${API_BASE}/extensions/vscode/changelog`, { timeout: 5000 })
      return response.data?.changelog || null
    } catch {
      return null
    }
  }

  isNewerVersion(remoteVersion, localVersion) {
    if (!remoteVersion || remoteVersion === localVersion) return false
    const normalize = (v) => v.split('.').map(n => parseInt(n) || 0)
    const remote = normalize(remoteVersion)
    const local = normalize(localVersion)
    for (let i = 0; i < Math.max(remote.length, local.length); i++) {
      const r = remote[i] || 0
      const l = local[i] || 0
      if (r > l) return true
      if (r < l) return false
    }
    return false
  }

  isVSCodeVersionSupported(minVersion) {
    const vscodeVersion = vscode.version
    const normalize = (v) => v.split('.').map(n => parseInt(n) || 0)
    const current = normalize(vscodeVersion)
    const required = normalize(minVersion)
    for (let i = 0; i < Math.max(current.length, required.length); i++) {
      const c = current[i] || 0
      const r = required[i] || 0
      if (c > r) return true
      if (c < r) return false
    }
    return true
  }

  dispose() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
    }
  }
}

class AstrovoxClient {
  constructor() {
    this.apiKey = ''
    this.model = 'gpt-4'
    this.maxTokens = 2048
    this.temperature = 0.7
    this.chatHistory = []
    this.conversationId = null
    this.requestId = 0
  }

  loadConfig() {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION)
    this.apiKey = config.get('apiKey', '')
    this.model = config.get('model', 'gpt-4')
    this.maxTokens = config.get('maxTokens', 2048)
    this.temperature = config.get('temperature', 0.7)
    this.conversationId = config.get('conversationId') || `vscode-${Date.now()}`
  }

  async callAPI(endpoint, data = {}) {
    this.loadConfig()
    if (!this.apiKey) {
      vscode.window.showWarningMessage('Astrovox API key not configured. Please set it in settings.')
      throw new Error('API key not configured')
    }

    const response = await axios.post(`${API_BASE}${endpoint}`, data, {
      headers: { 'Authorization': `Bearer ${this.apiKey}`, 'Content-Type': 'application/json' },
      timeout: 120000
    })
    return response.data
  }

  async chat(message, conversationId) {
    this.requestId++
    const result = await this.callAPI('/chat/message', {
      conversation_id: conversationId || this.conversationId,
      message,
      model: this.model,
      max_tokens: this.maxTokens,
      temperature: this.temperature
    })
    this.chatHistory.push({ role: 'user', content: message })
    if (result.ai_message?.content) {
      this.chatHistory.push({ role: 'assistant', content: result.ai_message.content })
    }
    return result
  }

  async explain(code, language) {
    return this.callAPI('/explain', { code, language })
  }

  async generateTests(code, language) {
    return this.callAPI('/generate-tests', { code, language })
  }

  async refactor(code, language) {
    return this.callAPI('/refactor', { code, language })
  }

  async review(code, language) {
    return this.callAPI('/review', { code, language })
  }

  async document(code, language) {
    return this.callAPI('/document', { code, language })
  }

  async fixBug(code, bugDescription, language) {
    return this.callAPI('/fix-bug', { code, bug_description: bugDescription, language })
  }

  async optimize(code, language) {
    return this.callAPI('/optimize', { code, language })
  }

  async detectSecurity(code, language) {
    return this.callAPI('/detect-security', { code, language })
  }

  async translate(text, language) {
    return this.callAPI('/translate', { text, language })
  }

  clearHistory() {
    this.chatHistory = []
    this.conversationId = `vscode-${Date.now()}`
  }
}

const client = new AstrovoxClient()
let updateNotifier = null

function activate(context) {
  updateNotifier = new ExtensionUpdateNotifier(context)
  updateNotifier.initialize()

  const chatPanel = vscode.window.createWebviewPanel(
    'astrovox.chat',
    'Astrovox AI',
    vscode.ViewColumn.One,
    { enableScripts: true, retainContextWhenHidden: true }
  )

  chatPanel.webview.html = getWebviewContent()

  const commands = [
    { id: 'startChat', title: 'Start Chat', action: () => chatPanel.reveal() },
    { id: 'explainCode', title: 'Explain Code', action: handleExplainCode },
    { id: 'generateTests', title: 'Generate Tests', action: handleGenerateTests },
    { id: 'refactorCode', title: 'Refactor Code', action: handleRefactorCode },
    { id: 'reviewCode', title: 'Review Code', action: handleReviewCode },
    { id: 'documentCode', title: 'Document Code', action: handleDocumentCode },
    { id: 'fixBug', title: 'Fix Bug', action: handleFixBug },
    { id: 'optimizeCode', title: 'Optimize Code', action: handleOptimizeCode },
    { id: 'detectSecurityIssues', title: 'Detect Security Issues', action: handleDetectSecurity },
    { id: 'translateCode', title: 'Translate Code', action: handleTranslate }
  ]

  const registrations = commands.map(cmd =>
    vscode.commands.registerCommand(`astrovox.${cmd.id}`, cmd.action)
  )

  chatPanel.webview.onDidReceiveMessage(async (message) => {
    try {
      let response
      switch (message.type) {
        case 'CHAT':
          response = await client.chat(message.payload.message, message.payload.conversationId)
          break
        case 'EXPLAIN':
          response = await client.explain(message.payload.code, message.payload.language)
          break
        default:
          response = { error: 'Unknown message type' }
      }
      chatPanel.webview.postMessage({ type: 'RESPONSE', payload: response, requestId: message.requestId })
    } catch (error) {
      chatPanel.webview.postMessage({ type: 'ERROR', payload: { error: error.message }, requestId: message.requestId })
    }
  })

  if (vscode.workspace.getConfiguration(CONFIG_SECTION).get('showStatusBar')) {
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100)
    statusBar.text = '$(robot) Astrovox'
    statusBar.tooltip = 'Astrovox AI Assistant'
    statusBar.command = 'astrovox.startChat'
    statusBar.show()
    context.subscriptions.push(statusBar)
  }

  context.subscriptions.push(chatPanel, ...registrations)
}

async function handleExplainCode() {
  const editor = vscode.window.activeTextEditor
  if (!editor) return
  const code = editor.document.getText(editor.selection)
  if (!code) return
  try {
    const response = await client.explain(code, editor.document.languageId)
    const content = response.content || JSON.stringify(response)
    await vscode.window.showInformationMessage(`Explanation: ${content.slice(0, 300)}${content.length > 300 ? '...' : ''}`)
  } catch (e) {
    vscode.window.showErrorMessage(`Failed to explain code: ${e.message}`)
  }
}

async function handleGenerateTests() {
  const editor = vscode.window.activeTextEditor
  if (!editor) return
  const code = editor.document.getText(editor.selection)
  if (!code) return
  try {
    const tests = await client.generateTests(code, editor.document.languageId)
    const content = tests.tests || tests.content || JSON.stringify(tests)
    const doc = await vscode.workspace.openTextDocument({ content, language: editor.document.languageId })
    await vscode.window.showTextDocument(doc)
  } catch (e) {
    vscode.window.showErrorMessage(`Failed to generate tests: ${e.message}`)
  }
}

async function handleRefactorCode() {
  const editor = vscode.window.activeTextEditor
  if (!editor) return
  const code = editor.document.getText(editor.selection)
  if (!code) return
  try {
    const refactored = await client.refactor(code, editor.document.languageId)
    const content = refactored.refactored || refactored.content || JSON.stringify(refactored)
    await editor.edit(editBuilder => editBuilder.replace(editor.selection, content))
  } catch (e) {
    vscode.window.showErrorMessage(`Failed to refactor code: ${e.message}`)
  }
}

async function handleReviewCode() {
  const editor = vscode.window.activeTextEditor
  if (!editor) return
  const code = editor.document.getText(editor.selection)
  if (!code) return
  try {
    const review = await client.review(code, editor.document.languageId)
    const content = review.review || review.content || JSON.stringify(review)
    await vscode.window.showInformationMessage(`Review: ${content.slice(0, 500)}${content.length > 500 ? '...' : ''}`)
  } catch (e) {
    vscode.window.showErrorMessage(`Failed to review code: ${e.message}`)
  }
}

async function handleDocumentCode() {
  const editor = vscode.window.activeTextEditor
  if (!editor) return
  const code = editor.document.getText(editor.selection)
  if (!code) return
  try {
    const docs = await client.document(code, editor.document.languageId)
    const content = docs.documentation || docs.content || JSON.stringify(docs)
    await editor.edit(editBuilder => editBuilder.insert(editor.selection.start, content))
  } catch (e) {
    vscode.window.showErrorMessage(`Failed to document code: ${e.message}`)
  }
}

async function handleFixBug() {
  const editor = vscode.window.activeTextEditor
  if (!editor) return
  const code = editor.document.getText(editor.selection)
  if (!code) return
  const bugDescription = await vscode.window.showInputBox({ prompt: 'Describe the bug' })
  if (!bugDescription) return
  try {
    const fixed = await client.fixBug(code, bugDescription, editor.document.languageId)
    const content = fixed.fixed_code || fixed.content || JSON.stringify(fixed)
    await editor.edit(editBuilder => editBuilder.replace(editor.selection, content))
  } catch (e) {
    vscode.window.showErrorMessage(`Failed to fix bug: ${e.message}`)
  }
}

async function handleOptimizeCode() {
  const editor = vscode.window.activeTextEditor
  if (!editor) return
  const code = editor.document.getText(editor.selection)
  if (!code) return
  try {
    const optimized = await client.optimize(code, editor.document.languageId)
    const content = optimized.optimized_code || optimized.content || JSON.stringify(optimized)
    await editor.edit(editBuilder => editBuilder.replace(editor.selection, content))
  } catch (e) {
    vscode.window.showErrorMessage(`Failed to optimize code: ${e.message}`)
  }
}

async function handleDetectSecurity() {
  const editor = vscode.window.activeTextEditor
  if (!editor) return
  const code = editor.document.getText(editor.selection)
  if (!code) return
  try {
    const security = await client.detectSecurity(code, editor.document.languageId)
    const content = security.content || JSON.stringify(security)
    await vscode.window.showInformationMessage(`Security: ${content.slice(0, 500)}${content.length > 500 ? '...' : ''}`)
  } catch (e) {
    vscode.window.showErrorMessage(`Security analysis failed: ${e.message}`)
  }
}

async function handleTranslate() {
  const editor = vscode.window.activeTextEditor
  if (!editor) return
  const code = editor.document.getText(editor.selection)
  if (!code) return
  const language = await vscode.window.showInputBox({ prompt: 'Target language (e.g., Python, JavaScript)' })
  if (!language) return
  try {
    const translated = await client.translate(code, language)
    const content = translated.content || JSON.stringify(translated)
    const doc = await vscode.workspace.openTextDocument({ content, language })
    await vscode.window.showTextDocument(doc)
  } catch (e) {
    vscode.window.showErrorMessage(`Translation failed: ${e.message}`)
  }
}

function getWebviewContent() {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Astrovox AI</title>
  <style>
    :root {
      --bg: var(--vscode-editor-background);
      --fg: var(--vscode-editor-foreground);
      --input-bg: var(--vscode-input-background);
      --input-fg: var(--vscode-input-foreground);
      --border: var(--vscode-input-border);
      --accent: #06b6d4;
    }
    body { font-family: var(--vscode-font-family); color: var(--fg); background: var(--bg); padding: 16px; margin: 0; }
    #input { width: 100%; padding: 8px 12px; background: var(--input-bg); color: var(--input-fg); border: 1px solid var(--border); border-radius: 4px; margin-bottom: 8px; }
    #send { padding: 6px 12px; background: var(--accent); color: #02040a; border: none; border-radius: 4px; cursor: pointer; }
    #response { margin-top: 12px; padding: 12px; background: var(--vscode-textBlockQuote-background); border-radius: 4px; white-space: pre-wrap; }
    .error { color: #ef4444; }
  </style>
</head>
<body>
  <textarea id="input" rows="3" placeholder="Ask Astrovox..."></textarea>
  <button id="send">Send</button>
  <div id="response" style="display:none;"></div>
  <script>
    const vscode = acquireVsCodeApi()
    let requestId = 0
    document.getElementById('send').addEventListener('click', () => {
      const input = document.getElementById('input')
      const response = document.getElementById('response')
      response.style.display = 'block'
      response.textContent = 'Thinking...'
      response.className = ''
      vscode.postMessage({ type: 'CHAT', payload: { message: input.value }, requestId: ++requestId })
    })
    window.addEventListener('message', event => {
      const response = document.getElementById('response')
      const msg = event.data
      if (msg.type === 'RESPONSE') {
        response.textContent = msg.payload.content || JSON.stringify(msg.payload)
      } else if (msg.type === 'ERROR') {
        response.textContent = msg.payload.error
        response.className = 'error'
      }
    })
  </script>
</body>
</html>`
}

function deactivate() {
  if (updateNotifier) {
    updateNotifier.dispose()
  }
}

module.exports = { activate, deactivate }
