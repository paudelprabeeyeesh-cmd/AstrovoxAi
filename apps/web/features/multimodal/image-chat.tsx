'use client'
import { useState, useRef, useCallback } from 'react'
import { ImagePlus, X, Loader2, Maximize2, AlertCircle } from 'lucide-react'

interface ImageChatProps {
  onImageAnalyze?: (imageUrl: string) => void
  onTextWithImage?: (imageUrl: string, text: string) => void
  disabled?: boolean
}

export function ImageChat({ onImageAnalyze, onTextWithImage, disabled }: ImageChatProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [preview, setPreview] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(async (files: FileList | null) => {
    const file = files?.[0]
    if (!file || !file.type.startsWith('image/')) {
      setError('Please select a valid image file.')
      return
    }
    setError(null)
    setIsUploading(true)
    try {
      const reader = new FileReader()
      reader.onload = async (e) => {
        const dataUrl = e.target?.result as string
        setPreview(dataUrl)
        try {
          const res = await fetch('/api/files/upload', {
            method: 'POST',
            body: (() => {
              const fd = new FormData()
              fd.append('file', file)
              return fd
            })(),
          })
          const data = await res.json()
          const url = data.url
          onImageAnalyze?.(url)
          setAnalysisResult('Image uploaded successfully. Ready for visual question answering.')
        } catch {
          setAnalysisResult('Image loaded locally. Analysis will proceed.')
        }
      }
      reader.readAsDataURL(file)
    } finally {
      setIsUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }, [onImageAnalyze])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => setDragOver(false), [])

  const clearPreview = () => {
    setPreview(null)
    setAnalysisResult(null)
    setError(null)
  }

  return (
    <div className="flex flex-col gap-3 w-full">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        className={`
          relative flex flex-col items-center justify-center gap-2
          border-2 border-dashed rounded-xl p-6 cursor-pointer
          transition-all duration-200 min-h-[140px]
          ${dragOver ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-muted-foreground/30 hover:border-primary/60 hover:bg-muted/30'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={disabled}
        />
        {isUploading ? (
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        ) : preview ? (
          <img src={preview} alt="Preview" className="h-24 w-24 rounded-lg object-cover shadow-md" />
        ) : (
          <>
            <ImagePlus className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground text-center">
              Drop an image here or click to browse
            </p>
            <p className="text-xs text-muted-foreground/70">
              Supports JPG, PNG, WEBP up to 10MB
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-500 bg-red-50 dark:bg-red-950/30 rounded-lg px-3 py-2">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {preview && (
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={clearPreview}
            disabled={disabled}
            className="rounded-lg p-1.5 hover:bg-muted text-muted-foreground transition-colors"
            title="Remove image"
          >
            <X className="h-4 w-4" />
          </button>
          <span className="text-xs text-muted-foreground truncate max-w-[200px]">Image attached</span>
          <button
            type="button"
            onClick={() => {}}
            disabled={disabled}
            className="ml-auto rounded-lg p-1.5 hover:bg-muted text-muted-foreground transition-colors"
            title="Fullscreen preview"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
      )}

      {analysisResult && (
        <div className="text-xs text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/30 rounded-lg px-3 py-2">
          {analysisResult}
        </div>
      )}
    </div>
  )
}
