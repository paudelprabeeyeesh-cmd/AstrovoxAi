'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { Volume2, Loader2, Check, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface VoiceOutputProps {
  text: string
  autoPlay?: boolean
  onEnd?: () => void
}

const VOICES = [
  { id: 'default', name: 'Default' },
  { id: 'male-1', name: 'Male 1' },
  { id: 'female-1', name: 'Female 1' },
]

export function VoiceOutput({ text, autoPlay = false, onEnd }: VoiceOutputProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [selectedVoice, setSelectedVoice] = useState('default')
  const [supported, setSupported] = useState(true)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  useEffect(() => {
    setSupported(typeof window !== 'undefined' && 'speechSynthesis' in window)
  }, [])

  useEffect(() => {
    if (autoPlay && supported && text) {
      speak()
    }
    return () => {
      if (typeof window !== 'undefined') {
        window.speechSynthesis.cancel()
      }
    }
  }, [autoPlay, text, supported])

  const speak = useCallback(() => {
    if (!supported || !text) return

    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utteranceRef.current = utterance

    utterance.rate = speed
    utterance.pitch = 1

    const voices = window.speechSynthesis.getVoices()
    if (selectedVoice !== 'default' && voices.length > 0) {
      const voiceIndex = Math.min(voices.length - 1, parseInt(selectedVoice) || 0)
      utterance.voice = voices[voiceIndex]
    }

    utterance.onstart = () => {
      setIsPlaying(true)
      setIsPaused(false)
    }

    utterance.onend = () => {
      setIsPlaying(false)
      setIsPaused(false)
      onEnd?.()
    }

    utterance.onerror = () => {
      setIsPlaying(false)
      setIsPaused(false)
    }

    window.speechSynthesis.speak(utterance)
  }, [text, speed, selectedVoice, supported, onEnd])

  const togglePlayPause = () => {
    if (!supported) return

    if (isPlaying && !isPaused) {
      window.speechSynthesis.pause()
      setIsPaused(true)
    } else if (isPaused) {
      window.speechSynthesis.resume()
      setIsPaused(false)
    } else {
      speak()
    }
  }

  const stop = () => {
    window.speechSynthesis.cancel()
    setIsPlaying(false)
    setIsPaused(false)
  }

  if (!supported) return null

  return (
    <div className="inline-flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-3 py-1.5">
      <Button
        variant="ghost"
        size="sm"
        onClick={togglePlayPause}
        className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
        title={isPlaying && !isPaused ? 'Pause' : isPaused ? 'Resume' : 'Play'}
      >
        {isPlaying && !isPaused ? (
          <span className="flex items-center gap-1">
            <span className="h-3 w-3 animate-pulse rounded-full bg-primary" />
            <span className="text-xs">Playing</span>
          </span>
        ) : isPaused ? (
          <Volume2 className="h-4 w-4" />
        ) : (
          <Volume2 className="h-4 w-4" />
        )}
      </Button>

      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Speed:</span>
        <Slider
          value={[speed]}
          onValueChange={(v) => setSpeed(v[0])}
          min={0.5}
          max={2}
          step={0.1}
          className="w-20"
        />
        <span className="text-xs text-muted-foreground w-8">{speed}x</span>
      </div>

      <Select value={selectedVoice} onValueChange={setSelectedVoice}>
        <SelectTrigger className="h-7 w-[100px] text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {VOICES.map((voice) => (
            <SelectItem key={voice.id} value={voice.id} className="text-xs">
              {voice.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {isPlaying && (
        <Button
          variant="ghost"
          size="sm"
          onClick={stop}
          className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
          title="Stop"
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  )
}
