'use client'
import * as React from 'react'
import { Check, ChevronDown } from 'lucide-react'
import * as Select from '@radix-ui/react-select'
import { ModelOption } from './types'

interface ModelSelectorProps {
  models: ModelOption[]
  value: string
  onChange: (value: string) => void
}

export function ModelSelector({ models, value, onChange }: ModelSelectorProps) {
  const selected = models.find((m) => m.id === value)

  return (
    <Select.Root value={value} onValueChange={onChange}>
      <Select.Trigger className="flex h-8 items-center gap-1 rounded-lg px-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors outline-none">
        <Select.Value>{selected?.name || 'Select model'}</Select.Value>
        <Select.Icon>
          <ChevronDown className="h-4 w-4" />
        </Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content className="overflow-hidden rounded-lg border bg-popover text-popover-foreground shadow-md z-50">
          <Select.Viewport>
            {models.map((model) => (
              <Select.Item
                key={model.id}
                value={model.id}
                className="flex items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground cursor-pointer"
              >
                <Select.ItemText>{model.name}</Select.ItemText>
                <Select.ItemIndicator>
                  <Check className="h-4 w-4" />
                </Select.ItemIndicator>
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  )
}
