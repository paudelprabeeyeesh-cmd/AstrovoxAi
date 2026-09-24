'use client'

import { useState } from 'react'
import { FolderOpen, ChevronRight, GripVertical, MoreHorizontal, Plus, Trash2, Pencil, Pin, PinOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { useChatStore } from '@/lib/store/chat-store'

interface Project {
  id: string
  name: string
  description?: string
  color?: string
  pinned?: boolean
  conversationCount: number
  lastUpdated: Date
}

interface Folder {
  id: string
  name: string
  color?: string
  projectIds: string[]
}

const initialProjects: Project[] = [
  {
    id: '1',
    name: 'AstrovoxAI Web App',
    description: 'Main web application for AstrovoxAI',
    color: 'bg-blue-500',
    pinned: true,
    conversationCount: 12,
    lastUpdated: new Date(Date.now() - 86400000),
  },
  {
    id: '2',
    name: 'Mobile App',
    description: 'React Native mobile application',
    color: 'bg-green-500',
    conversationCount: 5,
    lastUpdated: new Date(Date.now() - 172800000),
  },
  {
    id: '3',
    name: 'API Server',
    description: 'Backend API and services',
    color: 'bg-purple-500',
    conversationCount: 8,
    lastUpdated: new Date(Date.now() - 3600000),
  },
  {
    id: '4',
    name: 'Documentation',
    description: 'Project documentation and guides',
    color: 'bg-amber-500',
    conversationCount: 3,
    lastUpdated: new Date(Date.now() - 604800000),
  },
]

const initialFolders: Folder[] = [
  { id: 'active', name: 'Active Projects', color: 'bg-green-500', projectIds: ['1', '3'] },
  { id: 'archived', name: 'Archived', color: 'bg-gray-500', projectIds: ['2', '4'] },
  { id: 'recent', name: 'Recently Updated', color: 'bg-blue-500', projectIds: ['1', '2', '3'] },
]

export function ProjectOrganizer() {
  const [projects, setProjects] = useState<Project[]>(initialProjects)
  const [folders, setFolders] = useState<Folder[]>(initialFolders)
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null)
  const [editingProject, setEditingProject] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [newFolderName, setNewFolderName] = useState('')
  const [showNewFolder, setShowNewFolder] = useState(false)

  const { conversations } = useChatStore()

  const handleCreateFolder = () => {
    if (newFolderName.trim()) {
      const newFolder: Folder = {
        id: crypto.randomUUID(),
        name: newFolderName.trim(),
        color: 'bg-gray-500',
        projectIds: [],
      }
      setFolders((prev) => [...prev, newFolder])
      setNewFolderName('')
      setShowNewFolder(false)
    }
  }

  const handleDeleteFolder = (folderId: string) => {
    setFolders((prev) => prev.filter((f) => f.id !== folderId))
    if (selectedFolder === folderId) {
      setSelectedFolder(null)
    }
  }

  const handleCreateProject = () => {
    const newProject: Project = {
      id: crypto.randomUUID(),
      name: 'New Project',
      description: '',
      color: 'bg-gray-500',
      conversationCount: 0,
      lastUpdated: new Date(),
    }
    setProjects((prev) => [...prev, newProject])
    setEditingProject(newProject.id)
    setEditName(newProject.name)
  }

  const handleRenameProject = (id: string, newName: string) => {
    if (newName.trim()) {
      setProjects((prev) =>
        prev.map((project) =>
          project.id === id ? { ...project, name: newName.trim() } : project
        )
      )
    }
    setEditingProject(null)
    setEditName('')
  }

  const handleDeleteProject = (id: string) => {
    setProjects((prev) => prev.filter((project) => project.id !== id))
    setFolders((prev) =>
      prev.map((folder) => ({
        ...folder,
        projectIds: folder.projectIds.filter((projectId) => projectId !== id),
      }))
    )
  }

  const handlePinProject = (id: string) => {
    setProjects((prev) =>
      prev.map((project) =>
        project.id === id ? { ...project, pinned: !project.pinned } : project
      )
    )
  }

  const handleMoveToFolder = (projectId: string, folderId: string) => {
    setFolders((prev) =>
      prev.map((folder) => ({
        ...folder,
        projectIds:
          folder.id === folderId
            ? [...folder.projectIds, projectId]
            : folder.projectIds.filter((id) => id !== projectId),
      }))
    )
  }

  const filteredProjects = selectedFolder
    ? projects.filter((p) =>
        folders
          .find((f) => f.id === selectedFolder)
          ?.projectIds.includes(p.id)
      )
    : projects

  const formatTimeAgo = (date: Date) => {
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
    if (seconds < 60) return 'Just now'
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    if (days < 7) return `${days}d ago`
    const weeks = Math.floor(days / 7)
    return `${weeks}w ago`
  }

  return (
    <div className="flex h-full">
      <div className="w-64 border-r border-border">
        <div className="p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">Workspace</h3>
            <Button
              variant="ghost"
              size="icon"
              className="size-7"
              onClick={() => setShowNewFolder(true)}
            >
              <Plus className="size-3.5" />
            </Button>
          </div>

          {showNewFolder && (
            <div className="mt-2">
              <Input
                placeholder="Folder name..."
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateFolder()
                  }
                  if (e.key === 'Escape') {
                    setShowNewFolder(false)
                    setNewFolderName('')
                  }
                }}
                onBlur={() => {
                  if (!newFolderName.trim()) {
                    setShowNewFolder(false)
                  }
                }}
                autoFocus
                className="text-sm"
              />
            </div>
          )}

          <ScrollArea className="h-[calc(100vh-200px)]">
            <div className="space-y-1">
              <button
                onClick={() => setSelectedFolder(null)}
                className={cn(
                  'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                  selectedFolder === null
                    ? 'bg-accent text-accent-foreground'
                    : 'hover:bg-accent/50'
                )}
              >
                <FolderOpen className="size-4" />
                <span className="flex-1">All Projects</span>
                <Badge variant="secondary" className="text-[10px]">
                  {projects.length}
                </Badge>
              </button>

              {folders.map((folder) => (
                <div key={folder.id} className="group">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setSelectedFolder(folder.id)}
                      className={cn(
                        'flex flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                        selectedFolder === folder.id
                          ? 'bg-accent text-accent-foreground'
                          : 'hover:bg-accent/50'
                      )}
                    >
                      <FolderOpen className="size-4" />
                      <span className="flex-1 truncate">{folder.name}</span>
                      <Badge variant="secondary" className="text-[10px]">
                        {folder.projectIds.length}
                      </Badge>
                    </button>

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <MoreHorizontal className="size-3" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => handleDeleteFolder(folder.id)}>
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete Folder
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      </div>

      <div className="flex-1 p-6 overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold">
              {selectedFolder
                ? folders.find((f) => f.id === selectedFolder)?.name || 'Folder'
                : 'All Projects'}
            </h2>
            <p className="text-sm text-muted-foreground">
              {filteredProjects.length} project{filteredProjects.length !== 1 ? 's' : ''}
            </p>
          </div>

          <Button onClick={handleCreateProject} className="gap-2">
            <Plus className="size-4" />
            New Project
          </Button>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredProjects.map((project) => (
            <Card key={project.id} className="flex flex-col">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className={cn('h-3 w-3 rounded-full', project.color || 'bg-gray-500')} />
                    <CardTitle className="text-base">{project.name}</CardTitle>
                    {project.pinned && (
                      <Pin className="h-3 w-3 text-muted-foreground" />
                    )}
                  </div>

                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <MoreHorizontal className="size-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={() => {
                          setEditingProject(project.id)
                          setEditName(project.name)
                        }}
                      >
                        <Pencil className="mr-2 h-4 w-4" />
                        Rename
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handlePinProject(project.id)}>
                        {project.pinned ? (
                          <>
                            <PinOff className="mr-2 h-4 w-4" />
                            Unpin
                          </>
                        ) : (
                          <>
                            <Pin className="mr-2 h-4 w-4" />
                            Pin
                          </>
                        )}
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => handleDeleteProject(project.id)}
                        className="text-destructive"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>

              <CardContent className="flex-1">
                {project.description && (
                  <CardDescription className="line-clamp-2">
                    {project.description}
                  </CardDescription>
                )}

                <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
                  <span>{project.conversationCount} conversations</span>
                  <span>{formatTimeAgo(project.lastUpdated)}</span>
                </div>
              </CardContent>

              {editingProject === project.id && (
                <CardContent>
                  <Input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onBlur={() => handleRenameProject(project.id, editName)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleRenameProject(project.id, editName)
                      }
                      if (e.key === 'Escape') {
                        setEditingProject(null)
                        setEditName('')
                      }
                    }}
                    className="text-sm"
                    autoFocus
                  />
                </CardContent>
              )}
            </Card>
          ))}
        </div>

        {filteredProjects.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <FolderOpen className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-2 text-sm font-medium">No projects found</h3>
            <p className="text-sm text-muted-foreground">
              {selectedFolder
                ? 'This folder is empty'
                : 'Create your first project to get started'}
            </p>
            {!selectedFolder && (
              <Button onClick={handleCreateProject} className="mt-4 gap-2">
                <Plus className="size-4" />
                Create Project
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
