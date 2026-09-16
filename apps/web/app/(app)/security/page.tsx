'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Shield, Scan, Eye, EyeOff, Key, FileText, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { api } from '@/lib/api'

interface AuditLogEntry {
  action: string
  resource: string
  details: string
  created_at: string
}

interface ApiKeyItem {
  id: string
  name: string
  scopes: string
  last_used: string
  created_at: string
}

export default function SecurityPage() {
  const [promptText, setPromptText] = useState('')
  const [promptResult, setPromptResult] = useState<{ injected: boolean; confidence: number } | null>(null)
  const [secretsText, setSecretsText] = useState('')
  const [secretsResult, setSecretsResult] = useState<{ secrets_found: number; findings: Array<{ type: string; value: string; position: number }> } | null>(null)
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([])
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([])
  const [newKeyName, setNewKeyName] = useState('')
  const [isCreateKeyOpen, setIsCreateKeyOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [createdKey, setCreatedKey] = useState<string | null>(null)

  useEffect(() => {
    loadAuditLogs()
    loadApiKeys()
  }, [])

  const loadAuditLogs = async () => {
    try {
      const data = await api.get<{ logs: AuditLogEntry[] }>('/audit/logs')
      setAuditLogs(data.logs)
    } catch (e) {
      console.error('Failed to load audit logs', e)
    }
  }

  const loadApiKeys = async () => {
    try {
      const data = await api.get<{ keys: ApiKeyItem[] }>('/api-keys')
      setApiKeys(data.keys)
    } catch (e) {
      console.error('Failed to load API keys', e)
    }
  }

  const handleScanPrompt = async () => {
    setLoading(true)
    try {
      const result = await api.post<{ injected: boolean; confidence: number }>('/security/scan-prompt', { prompt: promptText })
      setPromptResult(result)
      await api.post('/audit/log', { action: 'security_scan_prompt', resource: 'prompt', details: { result } })
    } catch (e) {
      console.error('Scan failed', e)
    } finally {
      setLoading(false)
    }
  }

  const handleScanSecrets = async () => {
    setLoading(true)
    try {
      const result = await api.post<{ secrets_found: number; findings: Array<{ type: string; value: string; position: number }> }>('/security/scan-secrets', { text: secretsText })
      setSecretsResult(result)
      await api.post('/audit/log', { action: 'security_scan_secrets', resource: 'text', details: { secrets_found: result.secrets_found } })
    } catch (e) {
      console.error('Scan failed', e)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) return
    setLoading(true)
    try {
      const result = await api.post<{ key: string }>('/api-keys', { name: newKeyName, scopes: 'read' })
      setCreatedKey(result.key)
      setNewKeyName('')
      loadApiKeys()
    } catch (e) {
      console.error('Failed to create key', e)
    } finally {
      setLoading(false)
    }
  }

  const handleRevokeKey = async (keyId: string) => {
    setLoading(true)
    try {
      await api.delete(`/api-keys/${keyId}`)
      loadApiKeys()
    } catch (e) {
      console.error('Failed to revoke key', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Security</h1>
        <p className="text-muted-foreground">Monitor and manage security settings.</p>
      </div>

      <Tabs defaultValue="scanner" className="space-y-4">
        <TabsList>
          <TabsTrigger value="scanner">
            <Shield className="h-4 w-4 mr-2" />
            Scanner
          </TabsTrigger>
          <TabsTrigger value="audit">
            <FileText className="h-4 w-4 mr-2" />
            Audit Logs
          </TabsTrigger>
          <TabsTrigger value="api-keys">
            <Key className="h-4 w-4 mr-2" />
            API Keys
          </TabsTrigger>
        </TabsList>

        <TabsContent value="scanner" className="space-y-4">
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Scan className="h-5 w-5" />
              Prompt Injection Scanner
            </h2>
            <Textarea
              placeholder="Enter prompt to scan for injection attacks..."
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              className="min-h-[120px] mb-4"
            />
            <Button onClick={handleScanPrompt} disabled={loading || !promptText.trim()}>
              {loading ? 'Scanning...' : 'Scan Prompt'}
            </Button>
            {promptResult && (
              <div className="mt-4 p-4 rounded-md bg-muted/30">
                {promptResult.injected ? (
                  <div className="flex items-center gap-2 text-destructive">
                    <AlertTriangle className="h-5 w-5" />
                    <span className="font-medium">Prompt injection detected!</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-green-600">
                    <CheckCircle2 className="h-5 w-5" />
                    <span className="font-medium">No injection detected</span>
                  </div>
                )}
              </div>
            )}
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Secret Scanner
            </h2>
            <Textarea
              placeholder="Enter text to scan for secrets..."
              value={secretsText}
              onChange={(e) => setSecretsText(e.target.value)}
              className="min-h-[120px] mb-4"
            />
            <Button onClick={handleScanSecrets} disabled={loading || !secretsText.trim()}>
              {loading ? 'Scanning...' : 'Scan Secrets'}
            </Button>
            {secretsResult && secretsResult.secrets_found > 0 && (
              <div className="mt-4 space-y-2">
                <p className="text-sm font-medium text-destructive">{secretsResult.secrets_found} secrets found</p>
                {secretsResult.findings.map((finding, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded-md bg-destructive/5">
                    <div>
                      <Badge variant="destructive">{finding.type}</Badge>
                      <p className="text-sm font-mono mt-1">{finding.value}</p>
                    </div>
                    <span className="text-xs text-muted-foreground">pos: {finding.position}</span>
                  </div>
                ))}
              </div>
            )}
            {secretsResult && secretsResult.secrets_found === 0 && (
              <div className="mt-4 p-4 rounded-md bg-muted/30">
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle2 className="h-5 w-5" />
                  <span className="font-medium">No secrets found</span>
                </div>
              </div>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="audit" className="space-y-4">
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Audit Logs
            </h2>
            <div className="space-y-2">
              {auditLogs.length === 0 ? (
                <p className="text-sm text-muted-foreground">No audit logs found.</p>
              ) : (
                auditLogs.map((log, idx) => (
                  <div key={idx} className="p-3 rounded-md bg-muted/30 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{log.action}</span>
                      <span className="text-xs text-muted-foreground">{new Date(log.created_at).toLocaleString()}</span>
                    </div>
                    {log.resource && <p className="text-xs text-muted-foreground">Resource: {log.resource}</p>}
                    {log.details && <p className="text-xs font-mono">{log.details}</p>}
                  </div>
                ))
              )}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="api-keys" className="space-y-4">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Key className="h-5 w-5" />
                API Keys
              </h2>
              <Button size="sm" onClick={() => setIsCreateKeyOpen(true)}>
                Create Key
              </Button>
            </div>
            <div className="space-y-2">
              {apiKeys.length === 0 ? (
                <p className="text-sm text-muted-foreground">No API keys found.</p>
              ) : (
                apiKeys.map((key) => (
                  <div key={key.id} className="flex items-center justify-between p-3 rounded-md bg-muted/30">
                    <div>
                      <p className="text-sm font-medium">{key.name}</p>
                      <p className="text-xs text-muted-foreground">Scopes: {key.scopes}</p>
                      <p className="text-xs text-muted-foreground">Created: {new Date(key.created_at).toLocaleDateString()}</p>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => handleRevokeKey(key.id)}>
                      Revoke
                    </Button>
                  </div>
                ))
              )}
            </div>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={isCreateKeyOpen} onOpenChange={setIsCreateKeyOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <Input placeholder="Key name" value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} />
            {createdKey && (
              <div className="p-3 rounded-md bg-muted/30">
                <p className="text-xs text-muted-foreground mb-1">API Key (save this now)</p>
                <div className="flex items-center gap-2">
                  <code className="text-sm font-mono flex-1">{createdKey}</code>
                  <Button variant="ghost" size="icon" onClick={() => navigator.clipboard.writeText(createdKey)}>
                    <EyeOff className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsCreateKeyOpen(false); setCreatedKey(null) }}>Close</Button>
            <Button onClick={handleCreateKey} disabled={loading || !newKeyName.trim()}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
