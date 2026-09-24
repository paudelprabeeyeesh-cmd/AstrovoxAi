'use client'

import * as React from 'react'

interface UsageMeterProps {
  value: number
  max?: number
  label?: string
  unit?: string
  showValue?: boolean
  className?: string
}

export function UsageMeter({
  value,
  max = 100,
  label,
  unit = '%',
  showValue = true,
  className,
}: UsageMeterProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100))

  const getColorClass = () => {
    if (percentage >= 90) return 'bg-red-500'
    if (percentage >= 70) return 'bg-yellow-500'
    return 'bg-primary'
  }

  return (
    <div className={`w-full ${className || ''}`}>
      {(label || showValue) && (
        <div className="flex items-center justify-between mb-1">
          {label && (
            <span className="text-sm font-medium text-muted-foreground">{label}</span>
          )}
          {showValue && (
            <span className="text-sm font-medium tabular-nums">
              {value.toLocaleString()}{unit}
            </span>
          )}
        </div>
      )}
      <div className="h-2 w-full overflow-hidden rounded-full bg-primary/20">
        <div
          className={`h-full rounded-full transition-all duration-300 ${getColorClass()}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
