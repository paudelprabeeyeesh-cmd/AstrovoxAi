'use client';

import { useState } from 'react';
import { Key, Plus, Copy, Trash2, Eye, EyeOff, Loader2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { cn } from '@/lib/utils';

function formatDate(date: Date) {
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
}

interface ApiKey {
  id: string;
  name: string;
  key: string;
  createdAt: Date;
  lastUsed?: Date;
  expiresAt?: Date;
}

interface ApiKeyManagerProps {
  keys?: ApiKey[];
  onCreateKey?: (name: string) => Promise<ApiKey>;
  onRevokeKey?: (id: string) => Promise<void>;
  onCreateDialogOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function ApiKeyManager({
  keys = [],
  onCreateKey,
  onRevokeKey,
  onCreateDialogOpen,
  onOpenChange,
}: ApiKeyManagerProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [keyName, setKeyName] = useState('');
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set());
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [revokeDialogOpen, setRevokeDialogOpen] = useState(false);
  const [keyToRevoke, setKeyToRevoke] = useState<string | null>(null);

  const toggleKeyVisibility = (id: string) => {
    setVisibleKeys((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedKey(text);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const maskKey = (key: string) => {
    if (key.length <= 12) return key;
    return key.slice(0, 8) + '*'.repeat(24) + key.slice(-4);
  };

  const handleCreate = async () => {
    if (!keyName.trim()) return;
    setIsCreating(true);
    try {
      await onCreateKey?.(keyName);
      setKeyName('');
      onOpenChange?.(false);
    } finally {
      setIsCreating(false);
    }
  };

  const handleRevokeClick = (id: string) => {
    setKeyToRevoke(id);
    setRevokeDialogOpen(true);
  };

  const confirmRevoke = async () => {
    if (keyToRevoke) {
      await onRevokeKey?.(keyToRevoke);
      setKeyToRevoke(null);
    }
    setRevokeDialogOpen(false);
  };

  const isExpired = (expiresAt?: Date) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">API Keys</h3>
          <p className="text-sm text-muted-foreground">
            Manage API keys for programmatic access
          </p>
        </div>
        <Dialog open={onCreateDialogOpen} onOpenChange={onOpenChange}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create Key
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create API Key</DialogTitle>
              <DialogDescription>
                Give your API key a name to identify it later.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="key-name">Key Name</Label>
                <Input
                  id="key-name"
                  placeholder="e.g. Production API Key"
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => onOpenChange?.(false)}
                disabled={isCreating}
              >
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={isCreating || !keyName.trim()}>
                {isCreating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Key
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-3">
        {keys.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="rounded-full bg-muted p-3">
              <Key className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="mt-3 text-sm font-medium text-muted-foreground">No API keys</p>
            <p className="text-xs text-muted-foreground">
              Create an API key to get started
            </p>
          </div>
        ) : (
          keys.map((apiKey) => {
            const isVisible = visibleKeys.has(apiKey.id);
            const expired = isExpired(apiKey.expiresAt);
            const displayKey = isVisible ? apiKey.key : maskKey(apiKey.key);

            return (
              <div
                key={apiKey.id}
                className={cn(
                  'flex items-center justify-between rounded-lg border p-4',
                  expired && 'border-destructive/50'
                )}
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="rounded-md bg-primary/10 p-2">
                    <Key className="h-4 w-4 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{apiKey.name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <code className="text-xs text-muted-foreground font-mono truncate">
                        {displayKey}
                      </code>
                      <button
                        onClick={() => copyToClipboard(apiKey.key)}
                        className="shrink-0 text-muted-foreground hover:text-foreground"
                        title="Copy key"
                      >
                        {copiedKey === apiKey.key ? (
                          <span className="text-xs text-green-600">Copied!</span>
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </button>
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-muted-foreground">
                        Created {formatDate(new Date(apiKey.createdAt))}
                      </span>
                      {apiKey.lastUsed && (
                        <span className="text-xs text-muted-foreground">
                          Last used {formatDate(new Date(apiKey.lastUsed))}
                        </span>
                      )}
                      {expired && (
                        <span className="flex items-center gap-1 text-xs text-destructive">
                          <AlertTriangle className="h-3 w-3" />
                          Expired
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleKeyVisibility(apiKey.id)}
                  >
                    {isVisible ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRevokeClick(apiKey.id)}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            );
          })
        )}
      </div>

      <AlertDialog open={revokeDialogOpen} onOpenChange={setRevokeDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke API Key</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The API key will be permanently revoked and
              can no longer be used to access the API.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmRevoke} className="bg-destructive text-white hover:bg-destructive/90">
              Revoke
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}