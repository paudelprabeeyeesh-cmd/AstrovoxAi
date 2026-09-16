'use client'

import { useState, useCallback } from 'react'
import { api } from '@/lib/api'
import type { ToolExecutionResult } from '@/lib/api'

export interface UseToolsReturn {
  tools: MCPTool[]
  loading: boolean
  error: Error | null
  loadTools: () => Promise<void>
  executeTool: (name: string, args: Record<string, unknown>) => Promise<ToolExecutionResult | null>
  lastResult: ToolExecutionResult | null
}

export interface MCPTool {
  id: string
  name: string
  description: string
  parameters: ToolParameter[]
}

export interface ToolParameter {
  name: string
  type: string
  required: boolean
  description: string
}

export function useTools() {
  const [tools, setTools] = useState<MCPTool[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [lastResult, setLastResult] = useState<ToolExecutionResult | null>(null)

  const loadTools = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<MCPTool[]>('/tools')
      setTools(data)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load tools'))
    } finally {
      setLoading(false)
    }
  }, [])

  const executeTool = useCallback(async (name: string, args: Record<string, unknown>): Promise<ToolExecutionResult | null> => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.executeTool(name, args)
      setLastResult(result)
      return result
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Tool execution failed'))
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    tools,
    loading,
    error,
    loadTools,
    executeTool,
    lastResult,
  }
}
