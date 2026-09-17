'use client';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Menu, ChevronDown, User } from 'lucide-react';
import { UserMenu } from '@/components/layout/user-menu';

interface HeaderProps {
  onMenuClick: () => void;
  sidebarCollapsed: boolean;
}

const models = [
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI' },
  { id: 'claude-3.5', name: 'Claude 3.5 Sonnet', provider: 'Anthropic' },
  { id: 'gemini-pro', name: 'Gemini Pro', provider: 'Google' },
  { id: 'llama-3', name: 'Llama 3', provider: 'Meta' },
];

export function Header({ onMenuClick, sidebarCollapsed }: HeaderProps) {
  return (
    <header
      className={cn(
        'flex h-14 items-center justify-between',
        'border-b border-border bg-background/95',
        'px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60'
      )}
    >
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={onMenuClick}
        >
          <Menu className="size-5" />
        </Button>

        <div className="hidden items-center gap-2 md:flex">
          <span
            className={cn(
              'font-bold text-lg transition-all duration-300',
              sidebarCollapsed ? 'lg:ml-2' : 'lg:ml-0'
            )}
          >
            AstrovoxAI
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Model Selector */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <span className="hidden sm:inline">Model:</span>
              <span>GPT-4o</span>
              <ChevronDown className="size-4 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Select Model</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {models.map((model) => (
              <DropdownMenuItem key={model.id}>
                <div className="flex flex-col">
                  <span className="font-medium">{model.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {model.provider}
                  </span>
                </div>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User Menu */}
        <UserMenu />
      </div>
    </header>
  );
}
