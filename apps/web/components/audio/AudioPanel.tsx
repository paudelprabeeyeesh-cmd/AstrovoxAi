'use client'
import { useState, useCallback } from 'react'

type PanelProps = {
  title: string
  description: string
  children: React.ReactNode
}

export function Panel({ title, description, children }: PanelProps) {
  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
      <div className="mt-4 space-y-3">{children}</div>
    </div>
  )
}

export function FileUpload({ onFile, accept = 'audio/*', label = 'Upload audio' }: { onFile: (file: File) => void; accept?: string; label?: string }) {
  const [name, setName] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) {
      setName(file.name)
      onFile(file)
    }
  }

  return (
    <div className="flex items-center gap-3">
      <input ref={inputRef} type="file" accept={accept} onChange={handleChange} className="hidden" />
      <button type="button" onClick={() => inputRef.current?.click()} className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground">
        {label}
      </button>
      <span className="text-xs text-muted-foreground">{name || 'No file selected'}</span>
    </div>
  )
}

export function ActionButton({ onClick, loading, children, variant = 'primary' }: { onClick: () => void; loading?: boolean; children: React.ReactNode; variant?: 'primary' | 'secondary' | 'danger' }) {
  const base = 'rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50'
  const styles = {
    primary: 'bg-primary text-primary-foreground',
    secondary: 'bg-secondary text-secondary-foreground',
    danger: 'bg-destructive text-destructive-foreground',
  }
  return (
    <button type="button" onClick={onClick} disabled={loading} className={`${base} ${styles[variant]}`}>
      {loading ? 'Processing...' : children}
    </button>
  )
}

export function ResultBlock({ label, data }: { label: string; data: unknown }) {
  const text = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
  return (
    <div className="rounded-md border bg-muted/40 p-3">
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <pre className="mt-1 whitespace-pre-wrap break-words text-xs">{text.slice(0, 4000)}</pre>
    </div>
  )
}
