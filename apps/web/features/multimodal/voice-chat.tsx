'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { Mic, Square, Loader2, Volume2, VolumeX } from 'lucide-react'

interface VoiceChatProps {
  onTranscribe?: (text: string) => void
  onSynthesize?: (text: string) => void
  disabled?: boolean
  autoSend?: boolean
}

export function VoiceChat({ onTranscribe, onSynthesize, disabled, autoSend = false }: VoiceChatProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isSupported, setIsSupported] = useState(true)
  const [transcript, setTranscript] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationRef = useRef<number>(0)
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    const hasGetUserMedia = typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia
    const hasSpeechRecognition = typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)
    setIsSupported(hasGetUserMedia || hasSpeechRecognition)
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current)
      if (recognitionRef.current) recognitionRef.current.abort()
    }
  }, [])

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const audioContext = new AudioContext()
      const source = audioContext.createMediaStreamSource(stream)
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      const dataArray = new Uint8Array(analyser.frequencyBinCount)
      const updateLevel = () => {
        analyser.getByteFrequencyData(dataArray)
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
        setAudioLevel(avg / 255)
        animationRef.current = requestAnimationFrame(updateLevel)
      }
      updateLevel()

      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition()
        recognition.continuous = true
        recognition.interimResults = true
        recognition.lang = 'en-US'
        recognitionRef.current = recognition

        let finalTranscript = ''
        recognition.onresult = (event: any) => {
          let interim = ''
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript
            if (event.results[i].isFinal) {
              finalTranscript += transcript + ' '
            } else {
              interim += transcript
            }
          }
          setTranscript(finalTranscript + interim)
        }
        recognition.onerror = () => {}
        recognition.onend = () => {
          if (finalTranscript.trim() && autoSend) {
            onTranscribe?.(finalTranscript.trim())
          }
        }
        recognition.start()
      } else {
        mediaRecorderRef.current = new MediaRecorder(stream)
        chunksRef.current = []
        mediaRecorderRef.current.ondataavailable = (e) => {
          if (e.data.size > 0) chunksRef.current.push(e.data)
        }
        mediaRecorderRef.current.onstop = async () => {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
          try {
            const fd = new FormData()
            fd.append('file', blob, 'recording.webm')
            const res = await fetch('/api/voice/transcribe', { method: 'POST', body: fd })
            const data = await res.json()
            const text = data.text || ''
            setTranscript(text)
            if (text && autoSend) onTranscribe?.(text)
          } catch {
            console.error('Transcription failed')
          } finally {
            stream.getTracks().forEach(t => t.stop())
          }
        }
        mediaRecorderRef.current.start()
      }
      setIsRecording(true)
      setTranscript('')
    } catch {
      console.error('Microphone access denied')
    }
  }, [onTranscribe, autoSend])

  const stopRecording = useCallback(() => {
    if (animationRef.current) cancelAnimationFrame(animationRef.current)
    setAudioLevel(0)
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current = null
    }
    setIsRecording(false)
    if (transcript.trim()) {
      onTranscribe?.(transcript.trim())
    }
  }, [isRecording, transcript, onTranscribe])

  const speakText = useCallback((text: string) => {
    if (!('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)
    window.speechSynthesis.speak(utterance)
    onSynthesize?.(text)
  }, [onSynthesize])

  const stopSpeaking = useCallback(() => {
    window.speechSynthesis?.cancel()
    setIsSpeaking(false)
  }, [])

  if (!isSupported) return null

  return (
    <div className="flex flex-col gap-3 w-full">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={isRecording ? stopRecording : startRecording}
          disabled={disabled || isProcessing}
          className={`
            relative rounded-full p-3 transition-all duration-200
            ${isRecording ? 'bg-red-500 text-white scale-110 shadow-lg shadow-red-500/30' : 'bg-primary text-primary-foreground hover:scale-105'}
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}
          title={isRecording ? 'Stop recording' : 'Start voice input'}
        >
          {isProcessing ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : isRecording ? (
            <Square className="h-5 w-5" />
          ) : (
            <Mic className="h-5 w-5" />
          )}
          {isRecording && (
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
            </span>
          )}
        </button>

        {isRecording && (
          <div className="flex items-center gap-1 h-8">
            {[...Array(12)].map((_, i) => (
              <div
                key={i}
                className="w-1 bg-primary rounded-full transition-all duration-75"
                style={{
                  height: `${Math.max(4, audioLevel * 32)}px`,
                  animationDelay: `${i * 50}ms`,
                }}
              />
            ))}
          </div>
        )}

        {transcript && !isRecording && (
          <button
            type="button"
            onClick={() => isSpeaking ? stopSpeaking() : speakText(transcript)}
            disabled={disabled}
            className="rounded-full p-2 hover:bg-muted text-muted-foreground transition-colors"
            title={isSpeaking ? 'Stop speaking' : 'Play response'}
          >
            {isSpeaking ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>
        )}
      </div>

      {transcript && (
        <div className="text-sm text-foreground bg-muted/50 rounded-lg px-3 py-2 border border-muted">
          {transcript}
        </div>
      )}
    </div>
  )
}
