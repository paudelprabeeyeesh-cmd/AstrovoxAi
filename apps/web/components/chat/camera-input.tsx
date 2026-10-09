'use client'
import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Camera, X, RefreshCw } from 'lucide-react'
import { toast } from '@/hooks/use-toast'

interface CameraInputProps {
  onCapture: (dataUrl: string) => void
  onClose?: () => void
}

export function CameraInput({ onCapture, onClose }: CameraInputProps) {
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [error, setError] = useState<string | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    let active = true

    async function startCamera() {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' },
          audio: false,
        })
        if (active) {
          setStream(mediaStream)
          if (videoRef.current) {
            videoRef.current.srcObject = mediaStream
          }
        }
      } catch (err) {
        if (active) {
          setError('Camera access denied or not available')
          toast({
            title: 'Camera Error',
            description: 'Could not access camera',
            variant: 'destructive',
          })
        }
      }
    }

    startCamera()

    return () => {
      active = false
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
      }
    }
  }, [])

  const capturePhoto = () => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return

    const context = canvas.getContext('2d')
    if (!context) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    const dataUrl = canvas.toDataURL('image/jpeg', 0.9)
    onCapture(dataUrl)

    if (stream) {
      stream.getTracks().forEach((track) => track.stop())
    }
    onClose?.()
  }

  const switchCamera = async () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop())
    }
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: stream ? 'user' : 'environment' },
        audio: false,
      })
      setStream(mediaStream)
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
      }
    } catch (err) {
      setError('Could not switch camera')
    }
  }

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Camera</h3>
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      {error ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Camera className="h-12 w-12 text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" size="sm" onClick={switchCamera} className="mt-3">
            <RefreshCw className="h-4 w-4 mr-1" />
            Retry
          </Button>
        </div>
      ) : (
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
            <Button onClick={capturePhoto}>
              <Camera className="h-4 w-4 mr-1" />
              Capture
            </Button>
            <Button variant="outline" onClick={switchCamera}>
              <RefreshCw className="h-4 w-4 mr-1" />
              Switch Camera
            </Button>
          </div>
        </>
      )}
    </Card>
  )
}
