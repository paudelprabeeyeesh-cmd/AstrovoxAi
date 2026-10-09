'use client'
import { Paperclip, Mic, Camera, Monitor, Pencil, Type } from 'lucide-react'

interface ComposerToolsProps {
  onAttach?: () => void
  onVoice?: () => void
  onCamera?: () => void
  onScreenShare?: () => void
  onWhiteboard?: () => void
  onMath?: () => void
  disabled?: boolean
}

export function ComposerTools({ onAttach, onVoice, onCamera, onScreenShare, onWhiteboard, onMath, disabled }: ComposerToolsProps) {
  return (
    <div className="flex items-center gap-1 px-1">
      <button
        onClick={onAttach}
        disabled={disabled}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
        aria-label="Attach file"
      >
        <Paperclip className="h-4 w-4" />
      </button>
      <button
        onClick={onVoice}
        disabled={disabled}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
        aria-label="Voice input"
      >
        <Mic className="h-4 w-4" />
      </button>
      <button
        onClick={onCamera}
        disabled={disabled}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
        aria-label="Camera input"
      >
        <Camera className="h-4 w-4" />
      </button>
      <button
        onClick={onScreenShare}
        disabled={disabled}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
        aria-label="Screen sharing"
      >
        <Monitor className="h-4 w-4" />
      </button>
      <button
        onClick={onWhiteboard}
        disabled={disabled}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
        aria-label="Whiteboard"
      >
        <Pencil className="h-4 w-4" />
      </button>
      <button
        onClick={onMath}
        disabled={disabled}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
        aria-label="Math input"
      >
        <Type className="h-4 w-4" />
      </button>
    </div>
  )
}
