// Background service worker for Chrome extension
import { AstrovoxCore } from './shared/core.js'

const core = window.AstrovoxCore || new AstrovoxCore()
core.init().catch(console.error)

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'CHAT') {
    handleChat(message.payload)
      .then(sendResponse)
      .catch(error => sendResponse({ error: error.message }))
    return true
  }

  if (message.type === 'EXPLAIN') {
    handleExplain(message.payload)
      .then(sendResponse)
      .catch(error => sendResponse({ error: error.message }))
    return true
  }

  if (message.type === 'SUMMARIZE') {
    handleSummarize(message.payload)
      .then(sendResponse)
      .catch(error => sendResponse({ error: error.message }))
    return true
  }

  if (message.type === 'REFACTOR') {
    handleRefactor(message.payload)
      .then(sendResponse)
      .catch(error => sendResponse({ error: error.message }))
    return true
  }

  if (message.type === 'GENERATE_TESTS') {
    handleGenerateTests(message.payload)
      .then(sendResponse)
      .catch(error => sendResponse({ error: error.message }))
    return true
  }
})

async function handleChat(payload) {
  const response = await core.chat(payload.message)
  return response
}

async function handleExplain(payload) {
  const response = await core.explain(payload.code)
  return response
}

async function handleSummarize(payload) {
  const response = await core.summarize(payload.content)
  return response
}

async function handleRefactor(payload) {
  const response = await core.refactor(payload.code, payload.language)
  return response
}

async function handleGenerateTests(payload) {
  const response = await core.generateTests(payload.code, payload.language)
  return response
}

chrome.contextMenus.create({
  id: 'astrovox-explain',
  title: 'Explain with Astrovox',
  contexts: ['selection']
})

chrome.contextMenus.create({
  id: 'astrovox-summarize',
  title: 'Summarize with Astrovox',
  contexts: ['selection']
})

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'astrovox-explain' && info.selectionText) {
    chrome.tabs.sendMessage(tab.id, {
      type: 'EXPLAIN_SELECTION',
      text: info.selectionText
    })
  }
  if (info.menuItemId === 'astrovox-summarize' && info.selectionText) {
    chrome.tabs.sendMessage(tab.id, {
      type: 'SUMMARIZE_SELECTION',
      text: info.selectionText
    })
  }
})
