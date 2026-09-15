'use client'
import { Bot } from 'lucide-react'
import { SuggestionChips } from './suggestion-chips'
import { Suggestion } from './types'

interface EmptyStateProps {
  onSuggestionClick: (prompt: string) => void
}

const defaultSuggestions: Suggestion[] = [
  { id: '1', title: 'Explain quantum computing', prompt: 'Explain quantum computing in simple terms' },
  { id: '2', title: 'Write a poem', prompt: 'Write a poem about the stars' },
  { id: '3', title: 'Debug my code', prompt: 'Help me debug this code' },
  { id: '4', title: 'Plan a trip', prompt: 'Plan a weekend trip for me' },
]

export function EmptyState({ onSuggestionClick }: EmptyStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 px-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <Bot className="h-8 w-8" />
      </div>
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-semibold">How can I help you today?</h2>
        <p className="text-muted-foreground">Choose a suggestion below or type your own message.</p>
      </div>
      <SuggestionChips
        suggestions={defaultSuggestions}
        onSelect={(s) => onSuggestionClick(s.prompt)}
      />
    </div>
  )
}
