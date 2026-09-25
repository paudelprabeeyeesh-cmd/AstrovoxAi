'use client'
import { Sparkles } from 'lucide-react'
import { Suggestion } from './types'

interface SuggestionChipsProps {
  suggestions: Suggestion[]
  onSelect: (suggestion: Suggestion) => void
}

export function SuggestionChips({ suggestions, onSelect }: SuggestionChipsProps) {
  return (
    <div className="flex flex-wrap justify-center gap-2 px-4">
      {suggestions.map((suggestion) => (
        <button
          key={suggestion.id}
          onClick={() => onSelect(suggestion)}
          className="flex items-center gap-2 rounded-full border bg-background px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <Sparkles className="h-3.5 w-3.5" />
          {suggestion.title}
        </button>
      ))}
    </div>
  )
}
