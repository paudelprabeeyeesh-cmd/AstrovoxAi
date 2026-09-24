'use client'
import { useState, useMemo } from 'react'
import { Grid, Image, FileAudio, Film, FileText, Search, Filter, Download, Trash2, ExternalLink } from 'lucide-react'

interface MediaItem {
  id: string
  type: 'image' | 'audio' | 'video' | 'text'
  url: string
  thumbnail?: string
  title: string
  modality: string
  timestamp: Date
  similarity?: number
  tags: string[]
}

interface MultimodalGalleryProps {
  items?: MediaItem[]
  onSelect?: (item: MediaItem) => void
  onDelete?: (id: string) => void
  onDownload?: (item: MediaItem) => void
  searchable?: boolean
  filterable?: boolean
}

const MODALITY_ICONS = {
  image: Image,
  audio: FileAudio,
  video: Film,
  text: FileText,
}

const MODALITY_COLORS = {
  image: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  audio: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  video: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  text: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300',
}

export function MultimodalGallery({
  items = [],
  onSelect,
  onDelete,
  onDownload,
  searchable = true,
  filterable = true,
}: MultimodalGalleryProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [modalityFilter, setModalityFilter] = useState<string>('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null)

  const filteredItems = useMemo(() => {
    let result = items
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter(
        (item) =>
          item.title.toLowerCase().includes(q) ||
          item.modality.toLowerCase().includes(q) ||
          item.tags.some((t) => t.toLowerCase().includes(q))
      )
    }
    if (modalityFilter !== 'all') {
      result = result.filter((item) => item.type === modalityFilter)
    }
    return result.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
  }, [items, searchQuery, modalityFilter])

  const modalityCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    items.forEach((item) => {
      counts[item.type] = (counts[item.type] || 0) + 1
    })
    return counts
  }, [items])

  const formatTime = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return date.toLocaleDateString()
  }

  const handleItemClick = (item: MediaItem) => {
    setSelectedItem(item)
    onSelect?.(item)
  }

  return (
    <div className="flex flex-col gap-4 w-full">
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        {searchable && (
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search media..."
              className="w-full pl-9 pr-4 py-2 text-sm bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        )}
        {filterable && (
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={modalityFilter}
              onChange={(e) => setModalityFilter(e.target.value)}
              className="text-sm bg-background border border-input rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">All Modalities ({items.length})</option>
              {Object.entries(modalityCounts).map(([type, count]) => (
                <option key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}s ({count})
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="flex rounded-lg border border-input overflow-hidden">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2 ${viewMode === 'grid' ? 'bg-muted' : 'hover:bg-muted/50'} transition-colors`}
            title="Grid view"
          >
            <Grid className="h-4 w-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-2 ${viewMode === 'list' ? 'bg-muted' : 'hover:bg-muted/50'} transition-colors`}
            title="List view"
          >
            <FileText className="h-4 w-4" />
          </button>
        </div>
      </div>

      {filteredItems.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <Image className="h-12 w-12 mb-3 opacity-30" />
          <p className="text-sm">No media found</p>
          {searchQuery && (
            <p className="text-xs mt-1">Try adjusting your search or filters</p>
          )}
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {filteredItems.map((item) => {
            const Icon = MODALITY_ICONS[item.type] || FileText
            return (
              <div
                key={item.id}
                onClick={() => handleItemClick(item)}
                className="group relative bg-background border border-input rounded-xl overflow-hidden cursor-pointer hover:shadow-md hover:border-primary/30 transition-all"
              >
                <div className="aspect-square bg-muted/30 flex items-center justify-center">
                  {item.thumbnail ? (
                    <img src={item.thumbnail} alt={item.title} className="w-full h-full object-cover" />
                  ) : (
                    <Icon className="h-12 w-12 text-muted-foreground/50" />
                  )}
                </div>
                <div className="p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${MODALITY_COLORS[item.type]}`}>
                      {item.type}
                    </span>
                    {item.similarity !== undefined && (
                      <span className="text-[10px] text-muted-foreground">
                        {(item.similarity * 100).toFixed(0)}% match
                      </span>
                    )}
                  </div>
                  <p className="text-xs font-medium truncate">{item.title}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">{formatTime(item.timestamp)}</p>
                </div>
                <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => { e.stopPropagation(); onDownload?.(item) }}
                    className="rounded-full bg-background/80 p-1.5 hover:bg-background"
                    title="Download"
                  >
                    <Download className="h-3 w-3" />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); onDelete?.(item.id) }}
                    className="rounded-full bg-background/80 p-1.5 hover:bg-red-100 text-red-500"
                    title="Delete"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="space-y-2">
          {filteredItems.map((item) => {
            const Icon = MODALITY_ICONS[item.type] || FileText
            return (
              <div
                key={item.id}
                onClick={() => handleItemClick(item)}
                className="flex items-center gap-3 bg-background border border-input rounded-lg p-3 cursor-pointer hover:shadow-sm hover:border-primary/30 transition-all"
              >
                <div className="w-12 h-12 rounded-lg bg-muted/30 flex items-center justify-center shrink-0">
                  {item.thumbnail ? (
                    <img src={item.thumbnail} alt={item.title} className="w-full h-full object-cover rounded-lg" />
                  ) : (
                    <Icon className="h-6 w-6 text-muted-foreground/50" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${MODALITY_COLORS[item.type]}`}>
                      {item.type}
                    </span>
                    <p className="text-sm font-medium truncate">{item.title}</p>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {item.modality} · {formatTime(item.timestamp)}
                  </p>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={(e) => { e.stopPropagation(); onDownload?.(item) }}
                    className="rounded-lg p-1.5 hover:bg-muted text-muted-foreground"
                    title="Download"
                  >
                    <Download className="h-4 w-4" />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); onDelete?.(item.id) }}
                    className="rounded-lg p-1.5 hover:bg-muted text-muted-foreground"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setSelectedItem(null)}>
          <div className="bg-background rounded-2xl p-6 max-w-lg w-full shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">{selectedItem.title}</h3>
              <button onClick={() => setSelectedItem(null)} className="text-muted-foreground hover:text-foreground">
                ×
              </button>
            </div>
            <div className="aspect-video bg-muted/30 rounded-lg flex items-center justify-center mb-4">
              {selectedItem.thumbnail ? (
                <img src={selectedItem.thumbnail} alt={selectedItem.title} className="w-full h-full object-cover rounded-lg" />
              ) : (
                <span className="text-muted-foreground text-sm capitalize">{selectedItem.type} preview</span>
              )}
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Modality</span>
                <span className="font-medium capitalize">{selectedItem.modality}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type</span>
                <span className="font-medium capitalize">{selectedItem.type}</span>
              </div>
              {selectedItem.similarity !== undefined && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Similarity</span>
                  <span className="font-medium">{(selectedItem.similarity * 100).toFixed(1)}%</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Timestamp</span>
                <span className="font-medium">{selectedItem.timestamp.toLocaleString()}</span>
              </div>
              {selectedItem.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {selectedItem.tags.map((tag) => (
                    <span key={tag} className="text-xs bg-muted px-2 py-1 rounded-full">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => onDownload?.(selectedItem)}
                className="flex-1 rounded-lg bg-primary text-primary-foreground py-2 text-sm hover:bg-primary/90 transition-colors"
              >
                Download
              </button>
              <button
                onClick={() => setSelectedItem(null)}
                className="flex-1 rounded-lg border border-input py-2 text-sm hover:bg-muted transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
