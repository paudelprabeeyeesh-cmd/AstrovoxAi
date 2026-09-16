'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Upload, Globe, Github, Loader2, FileText, AlertCircle, CheckCircle, Clock } from 'lucide-react'
import { useDocuments } from '@/lib/hooks/use-documents'
import { useToast } from '@/lib/hooks/use-toast'

const statusIcons: Record<string, React.ElementType> = {
  pending: Clock,
  processing: Loader2,
  completed: CheckCircle,
  failed: AlertCircle,
}

const statusColors: Record<string, string> = {
  pending: 'bg-gray-500/10 text-gray-600',
  processing: 'bg-blue-500/10 text-blue-600',
  completed: 'bg-green-500/10 text-green-600',
  failed: 'bg-red-500/10 text-red-600',
}

function StatusBadge({ status }: { status: string }) {
  const Icon = statusIcons[status] || Clock
  return (
    <Badge variant="secondary" className={`gap-1 ${statusColors[status] || ''}`}>
      <Icon className="h-3 w-3" />
      {status}
    </Badge>
  )
}

export default function DocumentsPage() {
  const {
    documents,
    loading,
    error,
    uploadFile,
    ingestWebsite,
    ingestGitHub,
    searchDocuments,
    searchQuery,
    setSearchQuery,
    loadDocuments,
  } = useDocuments()
  const { toast } = useToast()

  const [isUrlDialogOpen, setIsUrlDialogOpen] = useState(false)
  const [isGitHubDialogOpen, setIsGitHubDialogOpen] = useState(false)
  const [urlValue, setUrlValue] = useState('')
  const [repoValue, setRepoValue] = useState('')
  const [dragActive, setDragActive] = useState(false)

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      const result = await uploadFile(file)
      if (result) {
        toast({ title: 'File uploaded', description: `${file.name} uploaded successfully.` })
      }
    }
  }, [uploadFile, toast])

  const handleFileInput = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      const result = await uploadFile(file)
      if (result) {
        toast({ title: 'File uploaded', description: `${file.name} uploaded successfully.` })
      }
    }
  }, [uploadFile, toast])

  const handleIngestWebsite = async () => {
    if (!urlValue.trim()) return
    const result = await ingestWebsite(urlValue)
    if (result) {
      toast({ title: 'Website ingestion started', description: `Ingesting ${urlValue}` })
      setIsUrlDialogOpen(false)
      setUrlValue('')
    }
  }

  const handleIngestGitHub = async () => {
    if (!repoValue.trim()) return
    const result = await ingestGitHub(repoValue)
    if (result) {
      toast({ title: 'GitHub ingestion started', description: `Ingesting ${repoValue}` })
      setIsGitHubDialogOpen(false)
      setRepoValue('')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Documents & RAG</h1>
        <p className="text-muted-foreground">Upload, ingest, and manage your documents for retrieval-augmented generation.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Button variant="outline" className="h-20 flex-col gap-2" onClick={() => document.getElementById('file-upload')?.click()}>
          <Upload className="h-6 w-6" />
          <span>Upload File</span>
        </Button>
        <input id="file-upload" type="file" className="hidden" onChange={handleFileInput} />
        <Button variant="outline" className="h-20 flex-col gap-2" onClick={() => setIsUrlDialogOpen(true)}>
          <Globe className="h-6 w-6" />
          <span>Ingest Website</span>
        </Button>
        <Button variant="outline" className="h-20 flex-col gap-2" onClick={() => setIsGitHubDialogOpen(true)}>
          <Github className="h-6 w-6" />
          <span>Ingest GitHub</span>
        </Button>
      </div>

      <Card
        className={`border-2 border-dashed p-8 text-center transition-colors ${dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">Drag and drop files here, or use the upload button above</p>
      </Card>

      <div>
        <div className="flex gap-2 mb-4">
          <div className="flex-1 relative">
            <Input
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                searchDocuments(e.target.value)
              }}
            />
          </div>
        </div>

        {error && (
          <Card className="p-4 border-destructive/50 bg-destructive/5 mb-4">
            <p className="text-sm text-destructive">{error.message}</p>
          </Card>
        )}

        <div className="grid gap-4">
          {documents.map((doc) => (
            <Card key={doc.id} className="p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-primary/10 p-2">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium truncate">{doc.filename}</h3>
                    <StatusBadge status={doc.status} />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {doc.chunks} chunks • {new Date(doc.createdAt).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </Card>
          ))}
          {!loading && documents.length === 0 && (
            <Card className="p-8 text-center">
              <p className="text-muted-foreground">No documents uploaded yet.</p>
            </Card>
          )}
        </div>
      </div>

      <Dialog open={isUrlDialogOpen} onOpenChange={setIsUrlDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ingest from URL</DialogTitle>
            <DialogDescription>
              Enter a URL to crawl and ingest content into your knowledge base.
            </DialogDescription>
          </DialogHeader>
          <Input
            placeholder="https://example.com/article"
            value={urlValue}
            onChange={(e) => setUrlValue(e.target.value)}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsUrlDialogOpen(false); setUrlValue('') }}>Cancel</Button>
            <Button onClick={handleIngestWebsite} disabled={!urlValue.trim() || loading}>Ingest</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isGitHubDialogOpen} onOpenChange={setIsGitHubDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ingest from GitHub</DialogTitle>
            <DialogDescription>
              Enter a GitHub repository to ingest its contents.
            </DialogDescription>
          </DialogHeader>
          <Input
            placeholder="owner/repo"
            value={repoValue}
            onChange={(e) => setRepoValue(e.target.value)}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsGitHubDialogOpen(false); setRepoValue('') }}>Cancel</Button>
            <Button onClick={handleIngestGitHub} disabled={!repoValue.trim() || loading}>Ingest</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
