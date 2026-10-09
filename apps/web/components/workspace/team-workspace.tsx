'use client'
import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  Users,
  Plus,
  MoreHorizontal,
  Trash2,
  UserPlus,
  Settings,
  Crown,
  Shield,
  User,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface TeamMember {
  id: string
  name: string
  email: string
  role: 'owner' | 'admin' | 'member' | 'viewer'
  avatar?: string
  joinedAt: Date
  status: 'online' | 'offline' | 'away'
}

interface TeamWorkspace {
  id: string
  name: string
  description: string
  members: TeamMember[]
  createdAt: Date
  ownerId: string
}

interface TeamWorkspaceProps {
  workspace?: TeamWorkspace
  onUpdate?: (workspace: TeamWorkspace) => void
}

const INITIAL_WORKSPACE: TeamWorkspace = {
  id: '1',
  name: 'AstrovoxAI Team',
  description: 'Main team workspace for AstrovoxAI',
  ownerId: 'user-1',
  createdAt: new Date('2024-01-01'),
  members: [
    {
      id: 'user-1',
      name: 'Alice Johnson',
      email: 'alice@example.com',
      role: 'owner',
      joinedAt: new Date('2024-01-01'),
      status: 'online',
    },
    {
      id: 'user-2',
      name: 'Bob Smith',
      email: 'bob@example.com',
      role: 'admin',
      joinedAt: new Date('2024-01-15'),
      status: 'online',
    },
    {
      id: 'user-3',
      name: 'Carol White',
      email: 'carol@example.com',
      role: 'member',
      joinedAt: new Date('2024-02-01'),
      status: 'away',
    },
    {
      id: 'user-4',
      name: 'David Lee',
      email: 'david@example.com',
      role: 'viewer',
      joinedAt: new Date('2024-02-15'),
      status: 'offline',
    },
  ],
}

const ROLE_COLORS: Record<string, string> = {
  owner: 'bg-purple-500 text-white',
  admin: 'bg-blue-500 text-white',
  member: 'bg-green-500 text-white',
  viewer: 'bg-gray-500 text-white',
}

const ROLE_ICONS: Record<string, React.ReactNode> = {
  owner: <Crown className="h-3 w-3" />,
  admin: <Shield className="h-3 w-3" />,
  member: <User className="h-3 w-3" />,
  viewer: <User className="h-3 w-3" />,
}

export function TeamWorkspace({ workspace = INITIAL_WORKSPACE, onUpdate }: TeamWorkspaceProps) {
  const [currentWorkspace, setCurrentWorkspace] = useState<TeamWorkspace>(workspace)
  const [inviteEmail, setInviteEmail] = useState('')
  const [showInvite, setShowInvite] = useState(false)

  const handleInvite = () => {
    if (!inviteEmail.trim()) return

    const newMember: TeamMember = {
      id: crypto.randomUUID(),
      name: inviteEmail.split('@')[0],
      email: inviteEmail,
      role: 'member',
      joinedAt: new Date(),
      status: 'offline',
    }

    const updated = {
      ...currentWorkspace,
      members: [...currentWorkspace.members, newMember],
    }
    setCurrentWorkspace(updated)
    onUpdate?.(updated)
    setInviteEmail('')
    setShowInvite(false)
  }

  const handleRemoveMember = (memberId: string) => {
    const updated = {
      ...currentWorkspace,
      members: currentWorkspace.members.filter((m) => m.id !== memberId),
    }
    setCurrentWorkspace(updated)
    onUpdate?.(updated)
  }

  const handleChangeRole = (memberId: string, newRole: TeamMember['role']) => {
    const updated = {
      ...currentWorkspace,
      members: currentWorkspace.members.map((m) =>
        m.id === memberId ? { ...m, role: newRole } : m
      ),
    }
    setCurrentWorkspace(updated)
    onUpdate?.(updated)
  }

  const onlineMembers = currentWorkspace.members.filter((m) => m.status === 'online')
  const awayMembers = currentWorkspace.members.filter((m) => m.status === 'away')
  const offlineMembers = currentWorkspace.members.filter((m) => m.status === 'offline')

  return (
    <div className="flex h-full">
      <div className="w-64 border-r border-border">
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium">Workspace</h3>
            <Button
              variant="ghost"
              size="icon"
              className="size-7"
              onClick={() => setShowInvite(!showInvite)}
            >
              <UserPlus className="size-3.5" />
            </Button>
          </div>

          {showInvite && (
            <div className="mb-3 space-y-2">
              <Input
                placeholder="Invite by email..."
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleInvite()
                  if (e.key === 'Escape') setShowInvite(false)
                }}
                className="text-sm"
              />
              <Button size="sm" className="w-full" onClick={handleInvite}>
                Send Invite
              </Button>
            </div>
          )}

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">
                Online ({onlineMembers.length})
              </span>
              <Badge variant="secondary" className="text-[10px]">
                {onlineMembers.length}
              </Badge>
            </div>
            {onlineMembers.map((member) => (
              <div
                key={member.id}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted/50 transition-colors"
              >
                <div className="relative">
                  <Avatar className="h-6 w-6">
                    <AvatarFallback className="text-xs">
                      {member.name.split(' ').map((n) => n[0]).join('')}
                    </AvatarFallback>
                  </Avatar>
                  <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-background bg-green-500" />
                </div>
                <span className="flex-1 truncate text-xs">{member.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 p-6 overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold">{currentWorkspace.name}</h2>
            <p className="text-sm text-muted-foreground">
              {currentWorkspace.description}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">
              <Users className="h-3 w-3 mr-1" />
              {currentWorkspace.members.length} members
            </Badge>
          </div>
        </div>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Members</h3>
          <ScrollArea className="h-[400px]">
            <div className="space-y-1">
              {onlineMembers.map((member) => (
                <MemberRow
                  key={member.id}
                  member={member}
                  onRemove={handleRemoveMember}
                  onChangeRole={handleChangeRole}
                  isOwner={member.id === currentWorkspace.ownerId}
                />
              ))}
              <Separator className="my-2" />
              {awayMembers.map((member) => (
                <MemberRow
                  key={member.id}
                  member={member}
                  onRemove={handleRemoveMember}
                  onChangeRole={handleChangeRole}
                  isOwner={member.id === currentWorkspace.ownerId}
                />
              ))}
              <Separator className="my-2" />
              {offlineMembers.map((member) => (
                <MemberRow
                  key={member.id}
                  member={member}
                  onRemove={handleRemoveMember}
                  onChangeRole={handleChangeRole}
                  isOwner={member.id === currentWorkspace.ownerId}
                />
              ))}
            </div>
          </ScrollArea>
        </Card>
      </div>
    </div>
  )
}

function MemberRow({
  member,
  onRemove,
  onChangeRole,
  isOwner,
}: {
  member: TeamMember
  onRemove: (id: string) => void
  onChangeRole: (id: string, role: TeamMember['role']) => void
  isOwner: boolean
}) {
  const statusColors = {
    online: 'bg-green-500',
    away: 'bg-amber-500',
    offline: 'bg-gray-400',
  }

  return (
    <div className="flex items-center justify-between p-2 rounded-md hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className="relative">
          <Avatar className="h-8 w-8">
            <AvatarFallback>
              {member.name.split(' ').map((n) => n[0]).join('')}
            </AvatarFallback>
          </Avatar>
          <span
            className={cn(
              'absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-background',
              statusColors[member.status]
            )}
          />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{member.name}</span>
            {isOwner && <Crown className="h-3 w-3 text-amber-500" />}
          </div>
          <p className="text-xs text-muted-foreground">{member.email}</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Badge variant="secondary" className={cn('text-xs', ROLE_COLORS[member.role])}>
          {ROLE_ICONS[member.role]}
          <span className="ml-1">{member.role}</span>
        </Badge>

        {!isOwner && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-7 w-7">
                <MoreHorizontal className="h-3.5 w-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onChangeRole(member.id, 'admin')}>
                <Shield className="mr-2 h-4 w-4" />
                Make Admin
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onChangeRole(member.id, 'member')}>
                <User className="mr-2 h-4 w-4" />
                Make Member
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onChangeRole(member.id, 'viewer')}>
                <User className="mr-2 h-4 w-4" />
                Make Viewer
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => onRemove(member.id)}
                className="text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Remove
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </div>
  )
}
