const vscode = require('vscode')
const axios = require('axios')

const API_BASE = 'https://api.astrovox.ai/v1'

class AstrovoxClient {
  constructor() {
    this.apiKey = ''
    this.model = 'gpt-4'
    this.maxTokens = 2048
    this.temperature = 0.7
    this.chatHistory = []
  }

  loadConfig() {
    const config = vscode.workspace.getConfiguration('astrovox')
    this.apiKey = config.get('apiKey', '')
    this.model = config.get('model', 'gpt-4')
    this.maxTokens = config.get('maxTokens', 2048)
    this.temperature = config.get('temperature', 0.7)
  }

  async callAPI(endpoint, data = {}) {
    this.loadConfig()
    if (!this.apiKey) {
      vscode.window.showWarningMessage('Astrovox API key not configured. Please set it in settings.')
      throw new Error('API key not configured')
    }

    const response = await axios.post(`${API_BASE}${endpoint}`, data, {
      headers: { 'Authorization': `Bearer ${this.apiKey}`, 'Content-Type': 'application/json' },
      timeout: 60000
    })
    return response.data
  }

  async chat(message, conversationId) {
    const result = await this.callAPI('/chat/message', {
      conversation_id: conversationId || `vscode-${Date.now()}`,
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
    const result = await this.callAPI('/explain', { code, language })
    return result.explanation || result.content
  }

  async generateTests(code, language) {
    const result = await this.callAPI('/generate-tests', { code, language })
    return result.tests || result.content
  }

  async refactor(code, language) {
    const result = await this.callAPI('/refactor', { code, language })
    return result.refactored || result.content
  }

  async review(code, language) {
    const result = await this.callAPI('/review', { code, language })
    return result.review || result.content
  }

  async document(code, language) {
    const result = await this.callAPI('/document', { code, language })
    return result.documentation || result.content
  }

  async fixBug(code, bugDescription, language) {
    const result = await this.callAPI('/fix-bug', { code, bug_description: bugDescription, language })
    return result.fixed_code || result.content
  }

  async optimize(code, language) {
    const result = await this.callAPI('/optimize', { code, language })
    return result.optimized_code || result.content
  }

  clearHistory() {
    this.chatHistory = []
  }
}

const client = new AstrovoxClient()

function activate(context) {
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
    { id: 'optimizeCode', title: 'Optimize Code', action: handleOptimizeCode }
  ]

  const registrations = commands.map(cmd =>
    vscode.commands.registerCommand(`astrovox.${cmd.id}`, cmd.action)
  )

  chatPanel.webview.onDidReceiveMessage(async (message) => {
    if (message.type === 'CHAT') {
      try {
        const response = await client.chat(message.payload)
        chatPanel.webview.postMessage({ type: 'RESPONSE', payload: response })
      } catch (error) {
        chatPanel.webview.postMessage({ type: 'ERROR', payload: { error: error.message } })
      }
    }
    if (message.type === 'EXPLAIN') {
      try {
        const response = await client.explain(message.payload.code, message.payload.language)
        chatPanel.webview.postMessage({ type: 'RESPONSE', payload: { content: response } })
      } catch (error) {
        chatPanel.webview.postMessage({ type: 'ERROR', payload: { error: error.message } })
      }
    }
  })

  if (vscode.workspace.getConfiguration('astrovox').get('showStatusBar')) {
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100)
    statusBar.text = '$(robot) Astrovox'
    statusBar.tooltip = 'Astrovox AI Assistant'
    statusBar.command = 'astrovox.startChat'
    statusBar.show()
    context.subscriptions.push(statusBar)
  }

  context.subscriptions.push(
    chatPanel,
    ...registrations
  )
}

async function handleExplainCode() {
  const editor = vscode.window.activeTextEditor
  if (!editor) return
  const code = editor.document.getText(editor.selection)
  if (!code) return
  try {
    const response = await client.explain(code, editor.document.languageId)
    await vscode.window.showInformationMessage(`Explanation: ${response.slice(0, 200)}...`)
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
    const doc = await vscode.workspace.openTextDocument({ content: tests, language: editor.document.languageId })
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
    await editor.edit(editBuilder => {
      editBuilder.replace(editor.selection, refactored)
    })
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
    vscode.window.showInformationMessage(`Review: ${review.slice(0, 300)}...`)
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
    await editor.edit(editBuilder => {
      editBuilder.insert(editor.selection.start, docs)
    })
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
    await editor.edit(editBuilder => {
      editBuilder.replace(editor.selection, fixed)
    })
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
    await editor.edit(editBuilder => {
      editBuilder.replace(editor.selection, optimized)
    })
  } catch (e) {
    vscode.window.showErrorMessage(`Failed to optimize code: ${e.message}`)
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
  </style>
</head>
<body>
  <textarea id="input" rows="3" placeholder="Ask Astrovox..."></textarea>
  <button id="send">Send</button>
  <div id="response" style="display:none;"></div>
  <script>
    const vscode = acquireVsCodeApi()
    document.getElementById('send').addEventListener('click', () => {
      const input = document.getElementById('input')
      const response = document.getElementById('response')
      response.style.display = 'block'
      response.textContent = 'Thinking...'
      vscode.postMessage({ type: 'CHAT', payload: input.value })
    })
    window.addEventListener('message', event => {
      const response = document.getElementById('response')
      const msg = event.data
      if (msg.type === 'RESPONSE') response.textContent = msg.payload.content || JSON.stringify(msg.payload)
      else if (msg.type === 'ERROR') { response.textContent = msg.payload.error; response.style.color = '#ef4444' }
    })
  </script>
</body>
</html>`
}

function deactivate() {}

module.exports = { activate, deactivate }
