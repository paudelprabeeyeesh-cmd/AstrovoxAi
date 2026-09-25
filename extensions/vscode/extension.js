const vscode = require('vscode')
const axios = require('axios')

const API_BASE = 'https://api.astrovox.ai/v1'

function activate(context) {
  const chatPanel = vscode.window.createWebviewPanel(
    'astrovox.chat',
    'Astrovox AI',
    vscode.ViewColumn.One,
    { enableScripts: true }
  )

  chatPanel.webview.html = getWebviewContent()

  const startChatCmd = vscode.commands.registerCommand('astrovox.startChat', () => {
    chatPanel.reveal()
  })

  const explainCodeCmd = vscode.commands.registerCommand('astrovox.explainCode', async () => {
    const editor = vscode.window.activeTextEditor
    if (!editor) return
    const code = editor.document.getText(editor.selection)
    if (!code) return
    const response = await callAPI('/explain', { code })
    vscode.window.showInformationMessage(response.explanation || 'Code explained')
  })

  const generateTestsCmd = vscode.commands.registerCommand('astrovox.generateTests', async () => {
    const editor = vscode.window.activeTextEditor
    if (!editor) return
    const code = editor.document.getText(editor.selection)
    if (!code) return
    const response = await callAPI('/generate-tests', { code, language: editor.document.languageId })
    const doc = await vscode.workspace.openTextDocument({ content: response.tests, language: editor.document.languageId })
    await vscode.window.showTextDocument(doc)
  })

  const refactorCmd = vscode.commands.registerCommand('astrovox.refactor', async () => {
    const editor = vscode.window.activeTextEditor
    if (!editor) return
    const code = editor.document.getText(editor.selection)
    if (!code) return
    const response = await callAPI('/refactor', { code, language: editor.document.languageId })
    await editor.edit(editBuilder => {
      editBuilder.replace(editor.selection, response.refactored)
    })
  })

  chatPanel.webview.onDidReceiveMessage(async (message) => {
    if (message.type === 'CHAT') {
      try {
        const response = await callAPI('/chat/message', { message: message.payload })
        chatPanel.webview.postMessage({ type: 'RESPONSE', payload: response })
      } catch (error) {
        chatPanel.webview.postMessage({ type: 'ERROR', payload: { error: error.message } })
      }
    }
  })

  context.subscriptions.push(chatPanel, startChatCmd, explainCodeCmd, generateTestsCmd, refactorCmd)
}

async function callAPI(endpoint, data) {
  const apiKey = vscode.workspace.getConfiguration('astrovox').get('apiKey')
  const response = await axios.post(`${API_BASE}${endpoint}`, data, {
    headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' }
  })
  return response.data
}

function getWebviewContent() {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Astrovox AI</title>
  <style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); background: var(--vscode-editor-background); padding: 16px; margin: 0; }
    #input { width: 100%; padding: 8px 12px; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); border-radius: 4px; margin-bottom: 8px; }
    #send { padding: 6px 12px; background: #06b6d4; color: #02040a; border: none; border-radius: 4px; cursor: pointer; }
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
