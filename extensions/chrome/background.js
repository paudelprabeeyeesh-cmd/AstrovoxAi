// Background service worker for Chrome extension
import { ExtensionCore } from './shared/core.js'

const core = new ExtensionCore()
core.init().catch(console.error)

const UPDATE_STORAGE_KEY = 'astrovox_last_update_check'
const EXTENSION_VERSION = '1.1.0'
const UPDATE_CHECK_INTERVAL = 24 * 60 * 60 * 1000

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  core.handleRuntimeMessage(message, sender, sendResponse)
  return true
})

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

chrome.contextMenus.create({
  id: 'astrovox-refactor',
  title: 'Refactor with Astrovox',
  contexts: ['selection']
})

chrome.contextMenus.create({
  id: 'astrovox-review',
  title: 'Review with Astrovox',
  contexts: ['selection']
})

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!info.selectionText) return

  const handlers = {
    'astrovox-explain': () => sendToContent(tab.id, 'EXPLAIN_SELECTION', { text: info.selectionText }),
    'astrovox-summarize': () => sendToContent(tab.id, 'SUMMARIZE_SELECTION', { text: info.selectionText }),
    'astrovox-refactor': () => sendToContent(tab.id, 'REFACTOR_SELECTION', { text: info.selectionText }),
    'astrovox-review': () => sendToContent(tab.id, 'REVIEW_SELECTION', { text: info.selectionText })
  }

  if (handlers[info.menuItemId]) {
    handlers[info.menuItemId]()
  }
})

async function sendToContent(tabId, type, payload) {
  try {
    await chrome.tabs.sendMessage(tabId, { type, payload })
  } catch (e) {
    console.error('Failed to send message to content script:', e)
  }
}

chrome.alarms.create('astrovox-update-check', { periodInMinutes: UPDATE_CHECK_INTERVAL / 60 / 1000 })

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'astrovox-update-check') {
    await checkForExtensionUpdate()
  }
})

chrome.runtime.onInstalled.addListener(async (details) => {
  if (details.reason === 'install') {
    chrome.tabs.create({ url: 'https://astrovox.ai/welcome' })
  } else if (details.reason === 'update') {
    await checkForExtensionUpdate()
  }
})

async function checkForExtensionUpdate() {
  try {
    const settings = await chrome.storage.local.get(['astrovoxSettings'])
    const apiKey = settings.astrovoxSettings?.apiKey

    if (!apiKey) return

    const response = await fetch('https://api.astrovox.ai/v1/extensions/chrome/latest', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'User-Agent': `astrovox-chrome/${EXTENSION_VERSION}`
      }
    })

    if (!response.ok) return

    const data = await response.json()
    const remoteVersion = data.version

    if (isNewerVersion(remoteVersion, EXTENSION_VERSION)) {
      chrome.runtime.sendMessage({
        type: 'EXTENSION_UPDATE_AVAILABLE',
        payload: {
          version: remoteVersion,
          changelog: data.changelog,
          download_url: data.download_url,
          is_critical: data.is_critical
        }
      }).catch(() => {})

      await chrome.storage.local.set({
        last_update_check: Date.now(),
        latest_version: remoteVersion
      })

      if (data.is_critical) {
        await showCriticalUpdateNotification(remoteVersion, data.download_url)
      } else {
        await showUpdateNotification(remoteVersion)
      }
    }
  } catch (e) {
    console.error('Extension update check failed:', e)
  }
}

async function showUpdateNotification(version) {
  const notifications = await chrome.notifications.getAll()
  if (Object.keys(notifications).length > 0) return

  const notificationId = 'astrovox-update'
  await chrome.notifications.create(notificationId, {
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: 'Astrovox AI Update Available',
    message: `Version ${version} is available. Click to update.`,
    priority: 2,
    requireInteraction: true,
    buttons: ['Update Now', 'Later']
  })

  chrome.notifications.onButtonClicked.addListener(async (id, buttonIndex) => {
    if (id === notificationId && buttonIndex === 0) {
      await chrome.tabs.create({ url: 'https://chrome.google.com/webstore/detail/astrovox-ai' })
    }
    await chrome.notifications.clear(id)
  })
}

async function showCriticalUpdateNotification(version, downloadUrl) {
  await chrome.notifications.create('astrovox-critical-update', {
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: `Critical Update Required - Astrovox AI v${version}`,
    message: 'A critical security update is available. Please update immediately.',
    priority: 2,
    requireInteraction: true,
    buttons: ['Update Now', 'Learn More']
  })
}

chrome.notifications.onClicked.addListener(async (id) => {
  if (id === 'astrovox-update' || id === 'astrovox-critical-update') {
    await chrome.tabs.create({ url: 'https://chrome.google.com/webstore/detail/astrovox-ai' })
  }
  await chrome.notifications.clear(id)
})

function isNewerVersion(remoteVersion, localVersion) {
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

chrome.runtime.onSuspendListener = () => {
  chrome.alarms.getAll((alarms) => {
    alarms.forEach(alarm => {
      if (alarm.name !== 'astrovox-update-check') {
        chrome.alarms.clear(alarm.name)
      }
    })
  })
}
