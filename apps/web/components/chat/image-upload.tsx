'use client'
import { useState, useRef } from 'react'
import { ImagePlus, X, Loader2 } from 'lucide-react'

interface ImageUploadProps {
  onImageSelect: (url: string) => void
  onAnalyze?: (url: string) => void
}

export function ImageUpload({ onImageSelect, onAnalyze }: ImageUploadProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [preview, setPreview] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setIsUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('/api/files/upload', { method: 'POST', body: formData })
      const data = await res.json()
      const url = data.url
      onImageSelect(url)
      setPreview(url)
      onAnalyze?.(url)
    } catch (err) {
      console.error('Upload failed', err)
    } finally {
      setIsUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const clearPreview = () => {
    setPreview(null)
    onImageSelect('')
  }

  return (
    <div className="relative inline-flex items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileChange}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        className="rounded-lg p-2 hover:bg-muted text-muted-foreground transition-colors"
        title="Upload image for vision"
      >
        {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ImagePlus className="h-4 w-4" />}
      </button>
      {preview && (
        <div className="relative inline-flex items-center">
          <img src={preview} alt="Preview" className="h-8 w-8 rounded object-cover" />
          <button
            type="button"
            onClick={clearPreview}
            className="absolute -top-1 -right-1 rounded-full bg-background p-0.5"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      )}
    </div>
  )
}
