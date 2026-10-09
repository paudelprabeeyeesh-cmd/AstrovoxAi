'use client'
import { useMemo } from 'react'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'

export interface ConfidenceMeterProps {
  value: number
  label?: string
  showLabel?: boolean
  thresholds?: {
    high: number
    medium: number
  }
}

export function ConfidenceMeter({
  value,
  label = 'Confidence',
  showLabel = true,
  thresholds = { high: 0.7, medium: 0.4 },
}: ConfidenceMeterProps) {
  const clamped = Math.max(0, Math.min(1, value))
  const color = useMemo(() => {
    if (clamped >= thresholds.high) return 'bg-green-500'
    if (clamped >= thresholds.medium) return 'bg-yellow-500'
    return 'bg-red-500'
  }, [clamped, thresholds])

  const statusIcon = useMemo(() => {
    if (clamped >= thresholds.high) return <CheckCircle2 className="h-4 w-4 text-green-500" />
    if (clamped >= thresholds.medium) return <CheckCircle2 className="h-4 w-4 text-yellow-500" />
    return <AlertTriangle className="h-4 w-4 text-red-500" />
  }, [clamped, thresholds])

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        {showLabel && <span className="text-sm font-medium">{label}</span>}
        {statusIcon}
      </div>
      <div className="mt-2">
        <Progress value={clamped * 100} className="h-2" indicatorClassName={color} />
      </div>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="text-xs text-muted-foreground cursor-help">
            {(clamped * 100).toFixed(1)}%
          </span>
        </TooltipTrigger>
        <TooltipContent>
          <p>
            {clamped >= thresholds.high
              ? 'High confidence'
              : clamped >= thresholds.medium
              ? 'Medium confidence - verify if possible'
              : 'Low confidence - treat with caution'}
          </p>
        </TooltipContent>
      </Tooltip>
    </Card>
  )
}
