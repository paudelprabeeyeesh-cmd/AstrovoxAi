'use client'
import { useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  GitBranch,
  GitFork,
  GitMerge,
  MoreHorizontal,
  Plus,
  Trash2,
  Copy,
  ArrowRight,
} from 'lucide-react'
import { useChatStore } from '@/lib/store/chat-store'
import type { Conversation } from '@/types'

interface Branch {
  id: string
  conversationId: string
  parentMessageId: string
  name: string
  createdAt: Date
}

interface ChatBranchingProps {
  conversationId: string
}

export function ChatBranching({ conversationId }: ChatBranchingProps) {
  const [branches, setBranches] = useState<Branch[]>([])
  const [showBranchDialog, setShowBranchDialog] = useState(false)
  const [branchName, setBranchName] = useState('')
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null)
  const { conversations, createConversation } = useChatStore()

  const handleBranch = useCallback(
    async (messageId: string, messageContent: string) => {
      setSelectedMessageId(messageId)
      setShowBranchDialog(true)
    },
    []
  )

  const createBranch = useCallback(async () => {
    if (!selectedMessageId) return

    const newConversation = await createConversation(
      branchName || `Branch ${branches.length + 1}`,
      'gpt-4'
    )

    const newBranch: Branch = {
      id: crypto.randomUUID(),
      conversationId: newConversation.conversation.id,
      parentMessageId: selectedMessageId,
      name: branchName || `Branch ${branches.length + 1}`,
      createdAt: new Date(),
    }

    setBranches((prev) => [...prev, newBranch])
    setShowBranchDialog(false)
    setBranchName('')
    setSelectedMessageId(null)
  }, [selectedMessageId, branchName, branches.length, createConversation])

  const handleFork = useCallback(
    async (conversationId: string, messageId: string) => {
      const sourceConversation = conversations.find((c) => c.id === conversationId)
      if (!sourceConversation) return

      const newConversation = await createConversation(
        `${sourceConversation.title} (Fork)`,
        sourceConversation.model || 'gpt-4'
      )

      const newBranch: Branch = {
        id: crypto.randomUUID(),
        conversationId: newConversation.conversation.id,
        parentMessageId: messageId,
        name: `${sourceConversation.title} (Fork)`,
        createdAt: new Date(),
      }

      setBranches((prev) => [...prev, newBranch])
    },
    [conversations, createConversation]
  )

  const handleMerge = useCallback(
    async (sourceConversationId: string, targetConversationId: string) => {
      const sourceConv = conversations.find((c) => c.id === sourceConversationId)
      if (!sourceConv) return

      const targetConv = conversations.find((c) => c.id === targetConversationId)
      if (!targetConv) return

      const mergedTitle = `${targetConv.title} + ${sourceConv.title}`
      const mergedConversation = await createConversation(mergedTitle, targetConv.model || 'gpt-4')

      const newBranch: Branch = {
        id: crypto.randomUUID(),
        conversationId: mergedConversation.conversation.id,
        parentMessageId: '',
        name: mergedTitle,
        createdAt: new Date(),
      }

      setBranches((prev) => [...prev, newBranch])
    },
    [conversations, createConversation]
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">Conversation Branches</h3>
          <p className="text-xs text-muted-foreground">
            Create alternative paths from any message
          </p>
        </div>
        <Dialog open={showBranchDialog} onOpenChange={setShowBranchDialog}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" disabled={!selectedMessageId}>
              <GitBranch className="h-4 w-4 mr-1" />
              New Branch
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Branch</DialogTitle>
              <DialogDescription>
                Create a new conversation branch from the selected message.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="branch-name">Branch Name</Label>
                <Input
                  id="branch-name"
                  value={branchName}
                  onChange={(e) => setBranchName(e.target.value)}
                  placeholder="Enter branch name..."
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowBranchDialog(false)}>
                Cancel
              </Button>
              <Button onClick={createBranch}>Create Branch</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {branches.length === 0 ? (
        <Card className="p-6 text-center">
          <GitBranch className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground">
            No branches yet. Use the message actions to create a branch.
          </p>
        </Card>
      ) : (
        <div className="space-y-2">
          {branches.map((branch) => (
            <Card key={branch.id} className="p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitFork className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{branch.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(branch.createdAt).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleMerge(conversationId, branch.conversationId)}
                >
                  <GitMerge className="h-4 w-4 mr-1" />
                  Merge
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleFork(branch.conversationId, branch.parentMessageId)}
                >
                  <Copy className="h-4 w-4 mr-1" />
                  Fork
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
