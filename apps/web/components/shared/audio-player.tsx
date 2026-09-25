'use client'
import { useState, useRef, useEffect } from 'react'
import { Play, Pause } from 'lucide-react'

interface AudioPlayerProps {
  src: string
  autoPlay?: boolean
}

export function AudioPlayer({ src, autoPlay = false }: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    if (autoPlay && audioRef.current) {
      audioRef.current.play()
      setIsPlaying(true)
    }
  }, [src, autoPlay])

  const togglePlay = () => {
    if (!audioRef.current) return
    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }

  return (
    <div className="inline-flex items-center gap-2 rounded-lg border bg-muted/50 px-3 py-1.5">
      <button
        onClick={togglePlay}
        className="flex items-center justify-center rounded-full bg-primary p-1 text-primary-foreground"
      >
        {isPlaying ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
      </button>
      <audio ref={audioRef} src={src} onEnded={() => setIsPlaying(false)} className="hidden" />
      <span className="text-xs text-muted-foreground">TTS Audio</span>
    </div>
  )
}
