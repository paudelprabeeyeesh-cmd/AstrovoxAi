'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Search, Loader2, Filter } from 'lucide-react'
import { useSearch } from '@/lib/hooks/use-search'

const typeOptions = [
  { value: '', label: 'All Types' },
  { value: 'document', label: 'Document' },
  { value: 'code', label: 'Code' },
  { value: 'image', label: 'Image' },
  { value: 'memory', label: 'Memory' },
  { value: 'conversation', label: 'Conversation' },
]

function SearchResultCard({ result }: { result: { id: string; title: string; content: string; score: number; type: string; createdAt: string } }) {
  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-medium truncate">{result.title}</h3>
            <Badge variant="secondary" className="text-xs shrink-0">{result.type}</Badge>
          </div>
          <p className="text-sm text-muted-foreground line-clamp-2">{result.content}</p>
          <p className="text-xs text-muted-foreground mt-2">
            {new Date(result.createdAt).toLocaleDateString()}
          </p>
        </div>
        <div className="text-right shrink-0">
          <div className="text-sm font-mono font-medium text-primary">{(result.score * 100).toFixed(1)}%</div>
          <p className="text-xs text-muted-foreground">score</p>
        </div>
      </div>
    </Card>
  )
}

export default function SearchPage() {
  const {
    query,
    setQuery,
    mode,
    setMode,
    results,
    loading,
    error,
    search,
    dateFilter,
    setDateFilter,
    typeFilter,
    setTypeFilter,
    hasSearched,
  } = useSearch()

  const [localSearch, setLocalSearch] = useState(query)
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    setLocalSearch(query)
  }, [query])

  const handleSearch = () => {
    setQuery(localSearch)
    search()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Search</h1>
        <p className="text-muted-foreground">Search across your knowledge base using semantic, keyword, or hybrid search.</p>
      </div>

      <Card className="p-4">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search documents, memories, conversations..."
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              onKeyDown={handleKeyDown}
              className="pl-9"
            />
          </div>
          <Button onClick={handleSearch} disabled={loading || !localSearch.trim()}>
            {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Search
          </Button>
          <Button variant="outline" onClick={() => setShowFilters(!showFilters)}>
            <Filter className="h-4 w-4" />
          </Button>
        </div>

        {showFilters && (
          <div className="flex gap-4 mt-4 pt-4 border-t">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Date:</span>
              <Input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="w-[160px]"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Type:</span>
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="All Types" />
                </SelectTrigger>
                <SelectContent>
                  {typeOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}
      </Card>

      <Tabs value={mode} onValueChange={(v) => setMode(v as typeof mode)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="semantic">Semantic</TabsTrigger>
          <TabsTrigger value="keyword">Keyword</TabsTrigger>
          <TabsTrigger value="hybrid">Hybrid</TabsTrigger>
        </TabsList>

        <TabsContent value={mode} className="space-y-4 mt-4">
          {error && (
            <Card className="p-4 border-destructive/50 bg-destructive/5">
              <p className="text-sm text-destructive">{error.message}</p>
            </Card>
          )}

          {!hasSearched && !loading && (
            <Card className="p-8 text-center">
              <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Enter a search query to get started.</p>
            </Card>
          )}

          {loading && (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {!loading && hasSearched && results.length === 0 && (
            <Card className="p-8 text-center">
              <p className="text-muted-foreground">No results found for your query.</p>
            </Card>
          )}

          <div className="grid gap-3">
            {results.map((result) => (
              <SearchResultCard key={result.id} result={result} />
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
