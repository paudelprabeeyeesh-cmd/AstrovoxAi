'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Monitor, X, Square } from 'lucide-react'
import { toast } from '@/hooks/use-toast'

interface ScreenShareProps {
  onStop?: (dataUrl?: string) => void
}

export function ScreenShare({ onStop }: ScreenShareProps) {
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [isSharing, setIsSharing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const startSharing = useCallback(async () => {
    try {
      setError(null)
      const mediaStream = await navigator.mediaDevices.getDisplayMedia({
        video: { cursor: 'always' },
        audio: true,
      })

      setStream(mediaStream)
      setIsSharing(true)

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
      }

      mediaStream.getVideoTracks()[0].onended = () => {
        stopSharing()
      }

      toast({
        title: 'Screen sharing started',
        description: 'Your screen is now being shared',
      })
    } catch (err) {
      setError('Screen sharing denied or not available')
      toast({
        title: 'Screen Share Error',
        description: 'Could not start screen sharing',
        variant: 'destructive',
      })
    }
  }, [toast])

  const stopSharing = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop())
    }

    if (canvasRef.current && videoRef.current && isSharing) {
      const context = canvasRef.current.getContext('2d')
      if (context) {
        canvasRef.current.width = videoRef.current.videoWidth
        canvasRef.current.height = videoRef.current.videoHeight
        context.drawImage(videoRef.current, 0, 0)
        setPreviewUrl(canvasRef.current.toDataURL('image/png'))
      }
    }

    setStream(null)
    setIsSharing(false)

    toast({
      title: 'Screen sharing stopped',
      description: 'Your screen is no longer being shared',
    })

    onStop?.(previewUrl || undefined)
  }, [stream, isSharing, previewUrl, onStop, toast])

  const captureFrame = useCallback(() => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return

    const context = canvas.getContext('2d')
    if (!context) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    setPreviewUrl(canvas.toDataURL('image/png'))
  }, [])

  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
      }
    }
  }, [stream])

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Monitor className="h-4 w-4" />
          <h3 className="text-sm font-medium">Screen Share</h3>
        </div>
        {isSharing && (
          <Button variant="ghost" size="icon" onClick={stopSharing}>
            <Square className="h-4 w-4" />
          </Button>
        )}
      </div>

      {error ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Monitor className="h-12 w-12 text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" size="sm" onClick={startSharing} className="mt-3">
            Retry
          </Button>
        </div>
      ) : isSharing ? (
        <>
          <div className="relative rounded-lg overflow-hidden bg-black">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full"
              style={{ maxHeight: 300 }}
            />
          </div>
          <canvas ref={canvasRef} className="hidden" />
          <div className="flex items-center justify-center gap-2">
            <Button variant="outline" onClick={captureFrame}>
              <Monitor className="h-4 w-4 mr-1" />
              Capture Frame
            </Button>
            <Button variant="destructive" onClick={stopSharing}>
              <Square className="h-4 w-4 mr-1" />
              Stop Sharing
            </Button>
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Monitor className="h-12 w-12 text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground mb-3">
            Share your screen with the AI assistant
          </p>
          <Button onClick={startSharing}>
            <Monitor className="h-4 w-4 mr-1" />
            Start Sharing
          </Button>
        </div>
      )}

      {previewUrl && (
        <div className="mt-3 rounded-lg border border-border p-2">
          <p className="text-xs text-muted-foreground mb-2">Captured Frame:</p>
          <img
            src={previewUrl}
            alt="Screen capture"
            className="w-full rounded-md"
          />
        </div>
      )}
    </Card>
  )
}
