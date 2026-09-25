import { useState, useEffect, useRef, useCallback } from 'react'

const STORAGE_KEY = 'astrovox-chat-history'

export function useChatHistory() {
  const [history, setHistory] = useState([])
  const [branches, setBranches] = useState({})
  const [activeBranch, setActiveBranch] = useState(null)

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        setHistory(parsed.history || [])
        setBranches(parsed.branches || {})
      } catch (e) {
        console.error('Failed to load chat history:', e)
      }
    }
  }, [])

  const saveToStorage = useCallback((newHistory, newBranches) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      history: newHistory,
      branches: newBranches,
      lastSaved: new Date().toISOString()
    }))
  }, [])

  const addMessage = useCallback((message) => {
    setHistory(prev => {
      const newHistory = [...prev, { ...message, id: message.id || crypto.randomUUID() }]
      saveToStorage(newHistory, branches)
      return newHistory
    })
  }, [branches, saveToStorage])

  const createBranch = useCallback((messageId, label) => {
    setBranches(prev => {
      const newBranches = {
        ...prev,
        [messageId]: {
          id: crypto.randomUUID(),
          label: label || `Branch ${Object.keys(prev).length + 1}`,
          parentId: messageId,
          messages: [],
          createdAt: new Date().toISOString()
        }
      }
      saveToStorage(history, newBranches)
      return newBranches
    })
  }, [history, saveToStorage])

  const addBranchMessage = useCallback((branchId, message) => {
    setBranches(prev => {
      const branch = prev[branchId]
      if (!branch) return prev
      const newBranches = {
        ...prev,
        [branchId]: {
          ...branch,
          messages: [...branch.messages, { ...message, id: message.id || crypto.randomUUID() }]
        }
      }
      saveToStorage(history, newBranches)
      return newBranches
    })
  }, [history, saveToStorage])

  const clearHistory = useCallback(() => {
    setHistory([])
    setBranches({})
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return {
    history,
    branches,
    activeBranch,
    setActiveBranch,
    addMessage,
    createBranch,
    addBranchMessage,
    clearHistory
  }
}
