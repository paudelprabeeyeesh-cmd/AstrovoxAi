"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

interface CommandProps extends React.HTMLAttributes<HTMLDivElement> {
  filter?: boolean
}

function Command({ className, filter, ...props }: CommandProps) {
  return (
    <div
      className={cn(
        "flex h-full w-full flex-col overflow-hidden rounded-md bg-popover text-popover-foreground",
        className,
      )}
      {...props}
    />
  )
}

interface CommandInputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

function CommandInput({ className, ...props }: CommandInputProps) {
  return (
    <div className="flex items-center border-b px-3">
      <input
        className={cn(
          "flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        {...props}
      />
    </div>
  )
}

interface CommandListProps extends React.HTMLAttributes<HTMLDivElement> {}

function CommandList({ className, ...props }: CommandListProps) {
  return (
    <div
      className={cn("max-h-[300px] overflow-y-auto overflow-x-hidden p-1", className)}
      {...props}
    />
  )
}

interface CommandEmptyProps extends React.HTMLAttributes<HTMLDivElement> {}

function CommandEmpty({ className, ...props }: CommandEmptyProps) {
  return (
    <div className={cn("py-6 text-center text-sm text-muted-foreground", className)} {...props} />
  )
}

interface CommandGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  heading?: string
}

function CommandGroup({ className, heading, ...props }: CommandGroupProps) {
  return (
    <div className={cn("overflow-hidden p-1 text-foreground", className)} {...props}>
      {heading && (
        <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
          {heading}
        </div>
      )}
      {props.children}
    </div>
  )
}

interface CommandItemProps extends React.HTMLAttributes<HTMLDivElement> {
  onSelect?: (value: string) => void
  disabled?: boolean
}

function CommandItem({
  className,
  onSelect,
  disabled,
  ...props
}: CommandItemProps) {
  const handleSelect = () => {
    if (!disabled && onSelect) {
      onSelect((props as unknown as { value?: string }).value || "")
    }
  }

  return (
    <div
      className={cn(
        "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50",
        className,
      )}
      onClick={handleSelect}
      {...props}
    />
  )
}

interface CommandSeparatorProps extends React.HTMLAttributes<HTMLDivElement> {}

function CommandSeparator({ className, ...props }: CommandSeparatorProps) {
  return (
    <div className={cn("-mx-1 h-px bg-border", className)} {...props} />
  )
}

export {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
}
