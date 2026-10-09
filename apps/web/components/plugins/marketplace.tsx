'use client'
import { useState } from 'react'
import { Search, Star, Download, ExternalLink, Package, Shield, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface Plugin {
  id: string
  name: string
  description: string
  version: string
  author: string
  downloads: number
  rating: number
  category: string
  tags: string[]
  icon: string
  installed?: boolean
  verified?: boolean
}

const samplePlugins: Plugin[] = [
  {
    id: 'web-search',
    name: 'Web Search',
    description: 'Search the web and return relevant results with AI-powered summarization.',
    version: '2.1.0',
    author: 'Astrovox Team',
    downloads: 15420,
    rating: 4.8,
    category: 'search',
    tags: ['search', 'web', 'ai'],
    icon: '🌐',
    verified: true,
  },
  {
    id: 'code-interpreter',
    name: 'Code Interpreter',
    description: 'Execute Python, JavaScript, and other languages in a secure sandbox.',
    version: '1.5.3',
    author: 'Astrovox Team',
    downloads: 28300,
    rating: 4.9,
    category: 'development',
    tags: ['code', 'python', 'javascript'],
    icon: '💻',
    verified: true,
  },
  {
    id: 'image-gen',
    name: 'Image Generator',
    description: 'Generate images from text descriptions using state-of-the-art models.',
    version: '3.0.1',
    author: 'Creative AI',
    downloads: 8900,
    rating: 4.5,
    category: 'media',
    tags: ['image', 'generation', 'art'],
    icon: '🎨',
  },
  {
    id: 'pdf-reader',
    name: 'PDF Reader',
    description: 'Extract text, tables, and insights from PDF documents.',
    version: '1.2.0',
    author: 'DocTools',
    downloads: 5600,
    rating: 4.3,
    category: 'documents',
    tags: ['pdf', 'document', 'text'],
    icon: '📄',
    installed: true,
  },
  {
    id: 'database-connector',
    name: 'Database Connector',
    description: 'Connect to PostgreSQL, MySQL, and SQLite databases for data analysis.',
    version: '1.0.4',
    author: 'DataFlow',
    downloads: 3200,
    rating: 4.6,
    category: 'data',
    tags: ['database', 'sql', 'analysis'],
    icon: '🗄️',
    verified: true,
  },
  {
    id: 'weather-api',
    name: 'Weather API',
    description: 'Get real-time weather data and forecasts for any location.',
    version: '2.0.0',
    author: 'WeatherCo',
    downloads: 4100,
    rating: 4.2,
    category: 'api',
    tags: ['weather', 'api', 'data'],
    icon: '🌤️',
  },
]

const categories = [
  { id: 'all', label: 'All', icon: Package },
  { id: 'search', label: 'Search', icon: Search },
  { id: 'development', label: 'Development', icon: Zap },
  { id: 'media', label: 'Media', icon: Star },
  { id: 'documents', label: 'Documents', icon: Package },
  { id: 'data', label: 'Data', icon: Shield },
]

export function PluginMarketplace() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [installedPlugins, setInstalledPlugins] = useState<Set<string>>(new Set(['pdf-reader']))

  const filteredPlugins = samplePlugins.filter((plugin) => {
    const matchesSearch =
      !searchQuery ||
      plugin.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      plugin.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      plugin.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))

    const matchesCategory = selectedCategory === 'all' || plugin.category === selectedCategory

    return matchesSearch && matchesCategory
  })

  const toggleInstall = (pluginId: string) => {
    setInstalledPlugins((prev) => {
      const next = new Set(prev)
      if (next.has(pluginId)) {
        next.delete(pluginId)
      } else {
        next.add(pluginId)
      }
      return next
    })
  }

  const formatDownloads = (downloads: number) => {
    if (downloads >= 1000) {
      return `${(downloads / 1000).toFixed(1)}k`
    }
    return downloads.toString()
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between pb-4">
        <div>
          <h2 className="text-xl font-semibold">Plugin Marketplace</h2>
          <p className="text-sm text-muted-foreground">Discover and install plugins to extend your AI capabilities</p>
        </div>
      </div>

      <div className="flex items-center gap-4 pb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search plugins..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      <Tabs value={selectedCategory} onValueChange={setSelectedCategory} className="flex-1">
        <TabsList className="w-full justify-start">
          {categories.map((category) => (
            <TabsTrigger key={category.id} value={category.id} className="gap-2">
              <category.icon className="h-4 w-4" />
              {category.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value={selectedCategory} className="mt-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredPlugins.map((plugin) => {
              const isInstalled = installedPlugins.has(plugin.id)

              return (
                <Card key={plugin.id} className="flex flex-col">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{plugin.icon}</span>
                        <div>
                          <CardTitle className="text-base">{plugin.name}</CardTitle>
                          <CardDescription className="text-xs">by {plugin.author}</CardDescription>
                        </div>
                      </div>
                      {plugin.verified && (
                        <Badge variant="secondary" className="gap-1">
                          <Shield className="h-3 w-3" />
                          Verified
                        </Badge>
                      )}
                    </div>
                  </CardHeader>

                  <CardContent className="flex-1">
                    <p className="text-sm text-muted-foreground line-clamp-2">{plugin.description}</p>

                    <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Download className="h-3 w-3" />
                        {formatDownloads(plugin.downloads)}
                      </span>
                      <span className="flex items-center gap-1">
                        <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                        {plugin.rating}
                      </span>
                      <span>v{plugin.version}</span>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-1">
                      {plugin.tags.slice(0, 3).map((tag) => (
                        <Badge key={tag} variant="outline" className="text-[10px]">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>

                  <CardContent>
                    <Button
                      variant={isInstalled ? 'outline' : 'default'}
                      size="sm"
                      className="w-full gap-2"
                      onClick={() => toggleInstall(plugin.id)}
                    >
                      {isInstalled ? (
                        <>
                          <span>Installed</span>
                          <ExternalLink className="h-3 w-3" />
                        </>
                      ) : (
                        <>
                          <Download className="h-3 w-3" />
                          <span>Install</span>
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {filteredPlugins.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Package className="h-12 w-12 text-muted-foreground" />
              <h3 className="mt-2 text-sm font-medium">No plugins found</h3>
              <p className="text-sm text-muted-foreground">Try adjusting your search or category filter</p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
