"use client"

import * as React from "react"
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area"

import { cn } from "@/lib/utils"

const ScrollArea = React.forwardRef<
  React.ElementRef<any>,
  React.ComponentPropsWithoutRef<any>
>(({ className, children, ...props }: any, ref: any) => {
  const ScrollAreaRoot = (ScrollAreaPrimitive as any).ScrollArea || (ScrollAreaPrimitive as any).Root
  const ScrollAreaViewport = (ScrollAreaPrimitive as any).Viewport
  const ScrollAreaCorner = (ScrollAreaPrimitive as any).Corner
  const ScrollAreaScrollbar = (ScrollAreaPrimitive as any).ScrollAreaScrollbar
  const ScrollAreaThumb = (ScrollAreaPrimitive as any).ScrollAreaThumb
  return (
    <ScrollAreaRoot ref={ref} className={cn("relative overflow-hidden", className)} {...props}>
      {ScrollAreaViewport ? <ScrollAreaViewport className="h-full w-full rounded-[inherit]">{children}</ScrollAreaViewport> : <div className="h-full w-full rounded-[inherit]">{children}</div>}
      {ScrollAreaScrollbar ? <ScrollAreaScrollbar orientation="vertical" className="h-full w-2 border-l border-l-transparent">{ScrollAreaThumb ? <ScrollAreaThumb className="relative flex-1 rounded-full bg-border" /> : null}</ScrollAreaScrollbar> : null}
      {ScrollAreaCorner ? <ScrollAreaCorner /> : null}
    </ScrollAreaRoot>
  )
})
ScrollArea.displayName = "ScrollArea"

const ScrollBar = React.forwardRef<
  React.ElementRef<any>,
  React.ComponentPropsWithoutRef<any>
>(({ className, orientation = "vertical", ...props }: any, ref: any) => {
  const ScrollAreaScrollbar = (ScrollAreaPrimitive as any).ScrollAreaScrollbar
  const ScrollAreaThumb = (ScrollAreaPrimitive as any).ScrollAreaThumb
  if (!ScrollAreaScrollbar) return null
  return (
    <ScrollAreaScrollbar ref={ref} orientation={orientation} className={cn("flex touch-none select-none p-[1px]", orientation === "vertical" && "h-full w-2 border-l border-l-transparent", orientation === "horizontal" && "h-2 flex-col border-t border-t-transparent", className)} {...props}>
      {ScrollAreaThumb ? <ScrollAreaThumb className="relative flex-1 rounded-full bg-border" /> : null}
    </ScrollAreaScrollbar>
  )
})
ScrollBar.displayName = "ScrollBar"

export { ScrollArea, ScrollBar }
