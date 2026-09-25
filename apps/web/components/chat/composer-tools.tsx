'use client'
import { Paperclip, Mic } from 'lucide-react'

interface ComposerToolsProps {
  onAttach?: () => void
  onVoice?: () => void
}

export function ComposerTools({ onAttach, onVoice }: ComposerToolsProps) {
  return (
    <div className="flex items-center gap-1 px-1">
      <button
        onClick={onAttach}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        aria-label="Attach file"
      >
        <Paperclip className="h-4 w-4" />
      </button>
      <button
        onClick={onVoice}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        aria-label="Voice input"
      >
        <Mic className="h-4 w-4" />
      </button>
    </div>
  )
}
