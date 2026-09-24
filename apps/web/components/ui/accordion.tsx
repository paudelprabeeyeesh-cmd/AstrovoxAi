"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { ChevronDown } from "lucide-react"

import { cn } from "@/lib/utils"

const accordionVariants = cva("w-full", {
  variants: {
    type: {
      single: "border-b",
      multiple: "border-b",
    },
  },
  defaultVariants: {
    type: "single",
  },
})

interface AccordionContextValue {
  openItems: string[]
  toggleItem: (item: string) => void
  type: "single" | "multiple"
}

const AccordionContext = React.createContext<AccordionContextValue | null>(null)

function useAccordionContext() {
  const context = React.useContext(AccordionContext)
  if (!context) {
    throw new Error("Accordion compound components must be used within Accordion")
  }
  return context
}

function Accordion({
  className,
  type = "single",
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { type?: "single" | "multiple" }) {
  const [openItems, setOpenItems] = React.useState<string[]>([])

  const toggleItem = React.useCallback(
    (item: string) => {
      setOpenItems((prev) => {
        if (type === "single") {
          return prev.includes(item) ? [] : [item]
        }
        return prev.includes(item) ? prev.filter((i) => i !== item) : [...prev, item]
      })
    },
    [type],
  )

  return (
    <AccordionContext.Provider value={{ openItems, toggleItem, type }}>
      <div className={cn(accordionVariants({ type }), className)} {...props}>
        {children}
      </div>
    </AccordionContext.Provider>
  )
}

function AccordionItem({
  className,
  value,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { value: string }) {
  return (
    <div className={cn("border-b last:border-b-0", className)} data-value={value} {...props} />
  )
}

function AccordionTrigger({
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { children: React.ReactNode }) {
  const { openItems, toggleItem } = useAccordionContext()
  const itemValue = props["data-value"] as string
  const isOpen = openItems.includes(itemValue)

  return (
    <button
      className={cn(
        "flex flex-1 items-center justify-between py-4 font-medium transition-all hover:underline w-full text-left",
        className,
      )}
      onClick={() => toggleItem(itemValue)}
      {...props}
    >
      {children}
      <ChevronDown
        className={cn("h-4 w-4 shrink-0 transition-transform duration-200", isOpen && "rotate-180")}
      />
    </button>
  )
}

function AccordionContent({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { children: React.ReactNode }) {
  const { openItems } = useAccordionContext()
  const itemValue = props["data-value"] as string
  const isOpen = openItems.includes(itemValue)

  if (!isOpen) return null

  return (
    <div
      className={cn("overflow-hidden text-sm transition-all", className)}
      data-state="open"
      {...props}
    >
      <div className="pb-4 pt-0">{children}</div>
    </div>
  )
}

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }
