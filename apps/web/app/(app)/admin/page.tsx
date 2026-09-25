'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Loader2, Shield, UserPlus, Users } from 'lucide-react'
import { api } from '@/lib/api'

interface User {
  id: string
  name: string
  email: string
  role: string
  status: string
}

interface Role {
  id: string
  name: string
  permissions: string[]
}

const PERMISSIONS = [
  'read:documents',
  'write:documents',
  'delete:documents',
  'read:memories',
  'write:memories',
  'read:search',
  'write:search',
  'admin:users',
  'admin:roles',
  'admin:settings',
]

const DEFAULT_ROLES: Role[] = [
  { id: 'admin', name: 'Admin', permissions: [...PERMISSIONS] },
  { id: 'editor', name: 'Editor', permissions: ['read:documents', 'write:documents', 'read:memories', 'write:memories', 'read:search'] },
  { id: 'viewer', name: 'Viewer', permissions: ['read:documents', 'read:memories', 'read:search'] },
]

const MOCK_USERS: User[] = [
  { id: '1', name: 'Alice Johnson', email: 'alice@example.com', role: 'admin', status: 'active' },
  { id: '2', name: 'Bob Smith', email: 'bob@example.com', role: 'editor', status: 'active' },
  { id: '3', name: 'Carol White', email: 'carol@example.com', role: 'viewer', status: 'active' },
  { id: '4', name: 'David Lee', email: 'david@example.com', role: 'viewer', status: 'inactive' },
]

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [isUserDialogOpen, setIsUserDialogOpen] = useState(false)
  const [isRoleDialogOpen, setIsRoleDialogOpen] = useState(false)
  const [selectedRole, setSelectedRole] = useState<Role | null>(null)
  const [userName, setUserName] = useState('')
  const [userEmail, setUserEmail] = useState('')
  const [userRole, setUserRole] = useState('viewer')
  const [roleName, setRoleName] = useState('')
  const [rolePermissions, setRolePermissions] = useState<string[]>([])

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [usersData, rolesData] = await Promise.all([
        api.get<User[]>('/admin/users').catch(() => MOCK_USERS),
        api.get<Role[]>('/admin/roles').catch(() => DEFAULT_ROLES),
      ])
      setUsers(usersData)
      setRoles(rolesData)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load admin data'))
      setUsers(MOCK_USERS)
      setRoles(DEFAULT_ROLES)
    } finally {
      setLoading(false)
    }
  }

  const handleAddUser = async () => {
    if (!userName.trim() || !userEmail.trim()) return
    const newUser: User = {
      id: crypto.randomUUID(),
      name: userName,
      email: userEmail,
      role: userRole,
      status: 'active',
    }
    setUsers((prev) => [...prev, newUser])
    setIsUserDialogOpen(false)
    setUserName('')
    setUserEmail('')
    setUserRole('viewer')
  }

  const handleUpdateRole = async () => {
    if (!selectedRole) return
    setRoles((prev) => prev.map((r) => (r.id === selectedRole.id ? { ...selectedRole, permissions: rolePermissions } : r)))
    setIsRoleDialogOpen(false)
    setSelectedRole(null)
    setRolePermissions([])
  }

  const handleDeleteUser = async (id: string) => {
    setUsers((prev) => prev.filter((u) => u.id !== id))
  }

  const openRoleDialog = (role: Role) => {
    setSelectedRole(role)
    setRolePermissions([...role.permissions])
    setIsRoleDialogOpen(true)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Admin & RBAC</h1>
        <p className="text-muted-foreground">Manage users, roles, and permissions.</p>
      </div>

      {error && (
        <Card className="p-4 border-destructive/50 bg-destructive/5">
          <p className="text-sm text-destructive">{error.message}</p>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold">Users</h2>
            </div>
            <Button size="sm" onClick={() => setIsUserDialogOpen(true)}>
              <UserPlus className="h-4 w-4 mr-2" />
              Add User
            </Button>
          </div>
          <div className="space-y-2">
            {users.map((user) => (
              <div key={user.id} className="flex items-center justify-between p-3 rounded-md bg-muted/30">
                <div>
                  <p className="font-medium text-sm">{user.name}</p>
                  <p className="text-xs text-muted-foreground">{user.email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Select value={user.role} onValueChange={(newRole) => setUsers((prev) => prev.map((u) => (u.id === user.id ? { ...u, role: newRole } : u)))}>
                    <SelectTrigger className="w-[120px] h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {roles.map((role) => (
                        <SelectItem key={role.id} value={role.id}>{role.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleDeleteUser(user.id)}>
                    <Users className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Roles & Permissions</h2>
          </div>
          <div className="space-y-3">
            {roles.map((role) => (
              <div key={role.id} className="p-3 rounded-md bg-muted/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-sm">{role.name}</span>
                  <Button variant="ghost" size="sm" onClick={() => openRoleDialog(role)}>Edit</Button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {role.permissions.map((perm) => (
                    <Badge key={perm} variant="secondary" className="text-xs">{perm}</Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4">Permission Matrix</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-2">Permission</th>
                {roles.map((role) => (
                  <th key={role.id} className="text-center py-2 px-2">{role.name}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {PERMISSIONS.map((perm) => (
                <tr key={perm} className="border-b last:border-0">
                  <td className="py-2 px-2 font-mono text-xs">{perm}</td>
                  {roles.map((role) => (
                    <td key={role.id} className="text-center py-2 px-2">
                      {role.permissions.includes(perm) ? (
                        <Badge variant="default" className="text-xs">Yes</Badge>
                      ) : (
                        <Badge variant="secondary" className="text-xs">No</Badge>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Dialog open={isUserDialogOpen} onOpenChange={setIsUserDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add User</DialogTitle>
            <DialogDescription>Create a new user account.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Input placeholder="Full name" value={userName} onChange={(e) => setUserName(e.target.value)} />
            <Input placeholder="Email address" type="email" value={userEmail} onChange={(e) => setUserEmail(e.target.value)} />
            <Select value={userRole} onValueChange={setUserRole}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {roles.map((role) => (
                  <SelectItem key={role.id} value={role.id}>{role.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsUserDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAddUser} disabled={!userName.trim() || !userEmail.trim()}>Add User</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isRoleDialogOpen} onOpenChange={setIsRoleDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Role: {selectedRole?.name}</DialogTitle>
            <DialogDescription>Manage permissions for this role.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {PERMISSIONS.map((perm) => (
              <label key={perm} className="flex items-center gap-2 p-2 rounded-md hover:bg-muted/50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={rolePermissions.includes(perm)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setRolePermissions((prev) => [...prev, perm])
                    } else {
                      setRolePermissions((prev) => prev.filter((p) => p !== perm))
                    }
                  }}
                  className="rounded"
                />
                <span className="text-sm font-mono">{perm}</span>
              </label>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRoleDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleUpdateRole}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
