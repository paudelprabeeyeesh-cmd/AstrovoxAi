'use client'

import { useState, useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Sidebar } from './sidebar'
import { Header } from './header'
import { cn } from '@/lib/utils'
import { ThemeProvider } from '@/components/shared/theme-provider'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Search, Plus, Command } from 'lucide-react'
import { NotificationCenter } from '@/components/shared/notification-center'
import { AccessibilityProvider } from '@/components/shared/accessibility-provider'

interface AppShellProps {
  children: React.ReactNode
}

const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
} as const

type Breakpoint = keyof typeof BREAKPOINTS

export function AppShell({ children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [breakpoint, setBreakpoint] = useState<Breakpoint>('lg')
  const [showCommandPalette, setShowCommandPalette] = useState(false)

  const pathname = usePathname()
  const router = useRouter()

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      if (width < BREAKPOINTS.sm) {
        setBreakpoint('sm')
      } else if (width < BREAKPOINTS.md) {
        setBreakpoint('md')
      } else if (width < BREAKPOINTS.lg) {
        setBreakpoint('lg')
      } else {
        setBreakpoint('xl')
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setShowCommandPalette(true)
      }

      if (e.key === 'Escape') {
        setShowCommandPalette(false)
      }

      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault()
        router.push('/chat')
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [router])

  const handleCommandAction = (action: string) => {
    setShowCommandPalette(false)
    switch (action) {
      case 'new-chat':
        router.push('/chat')
        break
      case 'memory':
        router.push('/memory')
        break
      case 'plugins':
        router.push('/plugins')
        break
      case 'settings':
        router.push('/settings')
        break
      case 'search':
        router.push('/search')
        break
      default:
        break
    }
  }

  const isMobile = breakpoint === 'sm' || breakpoint === 'md'

  return (
    <AccessibilityProvider>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <div className="flex h-screen overflow-hidden bg-background">
          <Sidebar
            open={sidebarOpen}
            setOpen={setSidebarOpen}
            collapsed={sidebarCollapsed}
            setCollapsed={setSidebarCollapsed}
          />

          <div className="flex flex-1 flex-col overflow-hidden">
            <Header
              onMenuClick={() => setSidebarOpen(!sidebarOpen)}
              sidebarCollapsed={sidebarCollapsed}
            />

            <main
              className={cn(
                'flex-1 overflow-y-auto',
                'p-4 md:p-6',
                'transition-all duration-300'
              )}
            >
              {children}
            </main>
          </div>

          <NotificationCenter />

          <Dialog open={showCommandPalette} onOpenChange={setShowCommandPalette}>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Command Palette</DialogTitle>
              </DialogHeader>
              <div className="space-y-2">
                <Button
                  variant="outline"
                  className="w-full justify-between"
                  onClick={() => handleCommandAction('new-chat')}
                >
                  <div className="flex items-center gap-2">
                    <Plus className="h-4 w-4" />
                    New Chat
                  </div>
                  <span className="text-xs text-muted-foreground">⌘N</span>
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-between"
                  onClick={() => handleCommandAction('search')}
                >
                  <div className="flex items-center gap-2">
                    <Search className="h-4 w-4" />
                    Search
                  </div>
                  <span className="text-xs text-muted-foreground">⌘K</span>
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-between"
                  onClick={() => handleCommandAction('memory')}
                >
                  <div className="flex items-center gap-2">
                    <Command className="h-4 w-4" />
                    Memory
                  </div>
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-between"
                  onClick={() => handleCommandAction('plugins')}
                >
                  <div className="flex items-center gap-2">
                    <Command className="h-4 w-4" />
                    Plugins
                  </div>
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-between"
                  onClick={() => handleCommandAction('settings')}
                >
                  <div className="flex items-center gap-2">
                    <Command className="h-4 w-4" />
                    Settings
                  </div>
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </ThemeProvider>
    </AccessibilityProvider>
  )
}

