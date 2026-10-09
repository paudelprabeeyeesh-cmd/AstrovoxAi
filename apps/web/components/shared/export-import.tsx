'use client'
import { useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Download, Upload, FileJson, FileText, FileSpreadsheet } from 'lucide-react'
import { useChatStore } from '@/lib/store/chat-store'
import type { Conversation, Message } from '@/types'

interface ExportImportProps {
  conversationId?: string
}

type ExportFormat = 'json' | 'markdown' | 'csv'

export function ExportImport({ conversationId }: ExportImportProps) {
  const [showExportDialog, setShowExportDialog] = useState(false)
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [exportFormat, setExportFormat] = useState<ExportFormat>('json')
  const [importData, setImportData] = useState('')
  const [importError, setImportError] = useState<string | null>(null)
  const { conversations, messages, addMessage, setConversations, setMessages } = useChatStore()

  const exportConversations = useCallback(
    (conversationsToExport: Conversation[], messagesToExport: Message[]) => {
      const data = {
        version: '1.0',
        exportedAt: new Date().toISOString(),
        conversations: conversationsToExport.map((conv) => ({
          ...conv,
          messages: messagesToExport
            .filter((m) => m.conversationId === conv.id)
            .map((m) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              timestamp: m.timestamp,
              model: m.model,
              feedback: m.feedback,
            })),
        })),
      }

      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `astrovox-export-${new Date().toISOString().split('T')[0]}.${exportFormat}`
      a.click()
      URL.revokeObjectURL(url)
    },
    [exportFormat]
  )

  const exportAsMarkdown = useCallback((conversationsToExport: Conversation[], messagesToExport: Message[]) => {
    let markdown = '# AstrovoxAI Export\n\n'
    markdown += `Exported: ${new Date().toLocaleString()}\n\n---\n\n`

    conversationsToExport.forEach((conv) => {
      markdown += `## ${conv.title}\n\n`
      const convMessages = messagesToExport.filter((m) => m.conversationId === conv.id)
      convMessages.forEach((msg) => {
        const role = msg.role === 'user' ? '**You**' : '**Assistant**'
        const time = msg.timestamp ? new Date(msg.timestamp).toLocaleString() : ''
        markdown += `### ${role} ${time ? `(${time})` : ''}\n\n${msg.content}\n\n---\n\n`
      })
    })

    const blob = new Blob([markdown], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `astrovox-export-${new Date().toISOString().split('T')[0]}.md`
    a.click()
    URL.revokeObjectURL(url)
  }, [])

  const exportAsCSV = useCallback((conversationsToExport: Conversation[], messagesToExport: Message[]) => {
    let csv = 'Conversation,Role,Content,Timestamp\n'
    conversationsToExport.forEach((conv) => {
      const convMessages = messagesToExport.filter((m) => m.conversationId === conv.id)
      convMessages.forEach((msg) => {
        const content = `"${msg.content.replace(/"/g, '""')}"`
        const time = msg.timestamp ? new Date(msg.timestamp).toISOString() : ''
        csv += `"${conv.title}","${msg.role}",${content},"${time}"\n`
      })
    })

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `astrovox-export-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }, [])

  const handleExport = useCallback(() => {
    const conversationsToExport = conversationId
      ? conversations.filter((c) => c.id === conversationId)
      : conversations

    if (conversationsToExport.length === 0) {
      alert('No conversations to export')
      return
    }

    switch (exportFormat) {
      case 'json':
        exportConversations(conversationsToExport, messages)
        break
      case 'markdown':
        exportAsMarkdown(conversationsToExport, messages)
        break
      case 'csv':
        exportAsCSV(conversationsToExport, messages)
        break
    }

    setShowExportDialog(false)
  }, [conversationId, conversations, messages, exportFormat, exportConversations, exportAsMarkdown, exportAsCSV])

  const handleImport = useCallback(() => {
    try {
      const data = JSON.parse(importData)
      if (!data.conversations || !Array.isArray(data.conversations)) {
        throw new Error('Invalid format: missing conversations array')
      }

      const importedConversations: Conversation[] = []
      const importedMessages: Message[] = []

      data.conversations.forEach((conv: any) => {
        const newConv: Conversation = {
          id: conv.id || crypto.randomUUID(),
          title: conv.title || 'Imported Conversation',
          createdAt: conv.createdAt || new Date().toISOString(),
          updatedAt: conv.updatedAt || new Date().toISOString(),
          model: conv.model || 'gpt-4',
          messageCount: conv.messages?.length || 0,
          preview: conv.preview || conv.messages?.[0]?.content?.slice(0, 100),
          pinned: false,
          folder: conv.folder,
        }
        importedConversations.push(newConv)

        if (conv.messages) {
          conv.messages.forEach((msg: any) => {
            importedMessages.push({
              id: msg.id || crypto.randomUUID(),
              role: msg.role,
              content: msg.content,
              conversationId: newConv.id,
              model: msg.model,
              timestamp: msg.timestamp || Date.now(),
              feedback: msg.feedback,
            })
          })
        }
      })

      setConversations([...conversations, ...importedConversations])
      importedMessages.forEach((msg) => addMessage(msg.conversationId, msg))

      setImportData('')
      setImportError(null)
      setShowImportDialog(false)
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Failed to parse import data')
    }
  }, [importData, conversations, setConversations, addMessage])

  return (
    <>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowExportDialog(true)}
        >
          <Download className="h-4 w-4 mr-1" />
          Export
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowImportDialog(true)}
        >
          <Upload className="h-4 w-4 mr-1" />
          Import
        </Button>
      </div>

      <Dialog open={showExportDialog} onOpenChange={setShowExportDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Export Conversations</DialogTitle>
            <DialogDescription>
              Export your conversations in your preferred format.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Format</Label>
              <Select value={exportFormat} onValueChange={(v) => setExportFormat(v as ExportFormat)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="json">
                    <div className="flex items-center gap-2">
                      <FileJson className="h-4 w-4" />
                      JSON
                    </div>
                  </SelectItem>
                  <SelectItem value="markdown">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Markdown
                    </div>
                  </SelectItem>
                  <SelectItem value="csv">
                    <div className="flex items-center gap-2">
                      <FileSpreadsheet className="h-4 w-4" />
                      CSV
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <p className="text-sm text-muted-foreground">
              {conversationId
                ? 'Export the current conversation'
                : `Export all ${conversations.length} conversations`}
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowExportDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleExport}>Export</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Import Conversations</DialogTitle>
            <DialogDescription>
              Import conversations from a JSON export file.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="import-data">Paste JSON data</Label>
              <Textarea
                id="import-data"
                value={importData}
                onChange={(e) => setImportData(e.target.value)}
                placeholder='{"conversations": [...]}'
                className="min-h-[200px] font-mono text-xs"
              />
            </div>
            {importError && (
              <p className="text-sm text-red-500">{importError}</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowImportDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleImport} disabled={!importData.trim()}>
              Import
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
