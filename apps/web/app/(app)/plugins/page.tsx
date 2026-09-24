'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Search, Star, Download, Plug, Zap, Shield } from 'lucide-react'

const MOCK_PLUGINS = [
  {
    id: '1',
    name: 'Web Search',
    description: 'Search the web for real-time information',
    author: 'Astrovox',
    version: '1.2.0',
    downloads: '12.5K',
    rating: 4.8,
    installed: true,
    capabilities: ['search', 'web'],
  },
  {
    id: '2',
    name: 'Code Interpreter',
    description: 'Execute and analyze code in multiple languages',
    author: 'Astrovox',
    version: '2.1.0',
    downloads: '8.3K',
    rating: 4.9,
    installed: true,
    capabilities: ['code', 'analysis'],
  },
  {
    id: '3',
    name: 'Image Analyzer',
    description: 'Analyze and describe images using vision models',
    author: 'Astrovox',
    version: '1.0.0',
    downloads: '5.1K',
    rating: 4.5,
    installed: false,
    capabilities: ['image', 'vision'],
  },
  {
    id: '4',
    name: 'Memory Saver',
    description: 'Automatically save important information to memory',
    author: 'Community',
    version: '0.9.0',
    downloads: '2.8K',
    rating: 4.2,
    installed: false,
    capabilities: ['memory', 'automation'],
  },
  {
    id: '5',
    name: 'Document Parser',
    description: 'Parse PDF, DOCX, and other document formats',
    author: 'Astrovox',
    version: '1.5.0',
    downloads: '9.7K',
    rating: 4.7,
    installed: true,
    capabilities: ['documents', 'parsing'],
  },
]

export default function PluginsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [plugins, setPlugins] = useState(MOCK_PLUGINS)

  const handleToggleInstall = (pluginId: string) => {
    setPlugins((prev) =>
      prev.map((p) => (p.id === pluginId ? { ...p, installed: !p.installed } : p)),
    )
  }

  const filteredPlugins = plugins.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.description.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  const installedPlugins = filteredPlugins.filter((p) => p.installed)
  const availablePlugins = filteredPlugins.filter((p) => !p.installed)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Plugins</h1>
        <p className="text-muted-foreground">Extend Astrovox with plugins and integrations.</p>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search plugins..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      <Tabs defaultValue="installed" className="space-y-4">
        <TabsList>
          <TabsTrigger value="installed">
            Installed ({installedPlugins.length})
          </TabsTrigger>
          <TabsTrigger value="available">
            Available ({availablePlugins.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="installed" className="space-y-4">
          {installedPlugins.length === 0 ? (
            <Card className="p-8 text-center">
              <Plug className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No plugins installed yet.</p>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {installedPlugins.map((plugin) => (
                <Card key={plugin.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{plugin.name}</h3>
                        <Badge variant="secondary" className="text-xs">
                          v{plugin.version}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{plugin.description}</p>
                      <div className="flex items-center gap-2 pt-2">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                          {plugin.rating}
                        </div>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Download className="h-3 w-3" />
                          {plugin.downloads}
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleToggleInstall(plugin.id)}
                    >
                      Disable
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-3">
                    {plugin.capabilities.map((cap) => (
                      <Badge key={cap} variant="outline" className="text-xs">
                        {cap}
                      </Badge>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="available" className="space-y-4">
          {availablePlugins.length === 0 ? (
            <Card className="p-8 text-center">
              <Zap className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">All available plugins are installed.</p>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {availablePlugins.map((plugin) => (
                <Card key={plugin.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{plugin.name}</h3>
                        <Badge variant="outline" className="text-xs">
                          v{plugin.version}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{plugin.description}</p>
                      <div className="flex items-center gap-2 pt-2">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                          {plugin.rating}
                        </div>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Download className="h-3 w-3" />
                          {plugin.downloads}
                        </div>
                      </div>
                    </div>
                    <Button size="sm" onClick={() => handleToggleInstall(plugin.id)}>
                      Install
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-3">
                    {plugin.capabilities.map((cap) => (
                      <Badge key={cap} variant="outline" className="text-xs">
                        {cap}
                      </Badge>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
