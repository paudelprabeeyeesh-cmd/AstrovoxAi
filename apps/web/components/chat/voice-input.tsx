'use client'
import { useState, useRef, useEffect } from 'react'
import { Mic, Square, Loader2 } from 'lucide-react'

interface VoiceInputProps {
  onTranscribe: (text: string) => void
  isProcessing?: boolean
}

export function VoiceInput({ onTranscribe, isProcessing }: VoiceInputProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [isSupported, setIsSupported] = useState(true)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  useEffect(() => {
    setIsSupported(typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia)
  }, [])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorderRef.current = new MediaRecorder(stream)
      chunksRef.current = []
      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const formData = new FormData()
        formData.append('file', blob, 'recording.webm')
        try {
          const res = await fetch('/api/voice/transcribe', { method: 'POST', body: formData })
          const data = await res.json()
          onTranscribe(data.text || '')
        } catch (err) {
          console.error('Transcription failed', err)
        } finally {
          stream.getTracks().forEach(t => t.stop())
        }
      }
      mediaRecorderRef.current.start()
      setIsRecording(true)
    } catch (err) {
      console.error('Microphone access denied', err)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  if (!isSupported) return null

  return (
    <button
      type="button"
      onClick={isRecording ? stopRecording : startRecording}
      disabled={isProcessing}
      className={`rounded-lg p-2 transition-colors ${
        isRecording ? 'bg-red-500 text-white' : 'hover:bg-muted text-muted-foreground'
      }`}
      title={isRecording ? 'Stop recording' : 'Start voice input'}
    >
      {isProcessing ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : isRecording ? (
        <Square className="h-4 w-4" />
      ) : (
        <Mic className="h-4 w-4" />
      )}
    </button>
  )
}
