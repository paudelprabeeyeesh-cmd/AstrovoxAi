'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  PanelLeftClose,
  PanelLeftOpen,
  MessageSquarePlus,
  Search,
  Trash2,
  MoreVertical,
  Brain,
  FileText,
  Network,
  Wrench,
  Shield,
} from 'lucide-react';

interface SidebarProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

function NavItem({ href, icon: Icon, label }: { href: string; icon: React.ElementType; label: string }) {
  return (
    <a
      href={href}
      className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
    >
      <Icon className="size-4 shrink-0" />
      <span className="flex-1 truncate">{label}</span>
    </a>
  )
}

const conversations = [
  { id: '1', title: 'React Hooks Discussion', active: true },
  { id: '2', title: 'TypeScript Best Practices', active: false },
  { id: '3', title: 'Next.js App Router', active: false },
  { id: '4', title: 'Tailwind CSS Tips', active: false },
  { id: '5', title: 'API Integration Help', active: false },
  { id: '6', title: 'Database Schema Design', active: false },
  { id: '7', title: 'Authentication Flow', active: false },
  { id: '8', title: 'Performance Optimization', active: false },
];

export function Sidebar({ open, setOpen, collapsed, setCollapsed }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col',
          'border-r border-border bg-muted/40',
          'transition-all duration-300',
          'lg:relative lg:z-0',
          collapsed ? 'w-16' : 'w-64',
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Header */}
        <div className="flex h-14 items-center justify-between px-3">
          {!collapsed && (
            <span className="font-semibold text-sm">Conversations</span>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto size-8"
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-4" />
            ) : (
              <PanelLeftClose className="size-4" />
            )}
          </Button>
        </div>

        <Separator />

        {/* Actions */}
        <div className="p-2">
          <Button
            variant="default"
            size="sm"
            className="w-full justify-start gap-2"
          >
            <MessageSquarePlus className="size-4" />
            {!collapsed && <span>New Chat</span>}
          </Button>
        </div>

        {/* Navigation */}
        {!collapsed && (
          <div className="px-2 py-2 space-y-1">
            <NavItem href="/memory" icon={Brain} label="Memory" />
            <NavItem href="/search" icon={Search} label="Search" />
            <NavItem href="/documents" icon={FileText} label="Documents" />
            <NavItem href="/knowledge" icon={Network} label="Knowledge" />
            <NavItem href="/tools" icon={Wrench} label="Tools" />
            <NavItem href="/security" icon={Shield} label="Security" />
            <NavItem href="/admin" icon={Shield} label="Admin" />
          </div>
        )}

        {/* Search */}
        {!collapsed && (
          <div className="px-2 pb-2">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 size-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search conversations..."
                className="w-full rounded-md border border-input bg-background pl-8 pr-3 py-2 text-sm"
              />
            </div>
          </div>
        )}

        <Separator />

        {/* Conversation List */}
        <ScrollArea className="flex-1 px-2 py-1">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={cn(
                'group flex items-center gap-2 rounded-md px-2 py-2 text-sm cursor-pointer transition-colors',
                conv.active
                  ? 'bg-accent text-accent-foreground'
                  : 'hover:bg-accent/50'
              )}
            >
              <MessageSquarePlus className="size-4 shrink-0" />
              {!collapsed && (
                <>
                  <span className="flex-1 truncate">{conv.title}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Trash2 className="size-3" />
                  </Button>
                </>
              )}
            </div>
          ))}
        </ScrollArea>

        {/* Footer */}
        <Separator />
        <div className="p-2">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2"
          >
            <MoreVertical className="size-4" />
            {!collapsed && <span>Settings</span>}
          </Button>
        </div>
      </aside>
    </>
  );
}
