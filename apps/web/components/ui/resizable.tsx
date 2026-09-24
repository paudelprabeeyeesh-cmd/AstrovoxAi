"use client"

import * as React from "react"
import * as ResizablePrimitive from "@radix-ui/react-resizable"

import { cn } from "@/lib/utils"

const ResizablePanelGroup = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  direction?: "horizontal" | "vertical"
}) => (
  <div
    className={cn(
      "flex h-full w-full",
      className,
    )}
    {...props}
  />
)

const ResizablePanel = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex-1 overflow-hidden", className)} {...props} />
)

const ResizableHandle = ({
  withHandle,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  withHandle?: boolean
}) => (
  <div
    className={cn(
      "relative flex w-px items-center justify-center bg-border after:absolute after:inset-y-0 after:left-1/2 after:w-1 after:-translate-x-1/2 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1 data-[resize-handle-state=hover]:bg-ring data-[resize-handle-state=active]:bg-ring",
      "transition-colors",
      className,
    )}
    {...props}
  >
    {withHandle && (
      <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-2">
        <div className="h-full w-1 rounded-full bg-border mx-auto" />
      </div>
    )}
  </div>
)

export { ResizablePanelGroup, ResizablePanel, ResizableHandle }
