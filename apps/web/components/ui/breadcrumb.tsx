"use client"

import * as React from "react"
import { ChevronRight, Home } from "lucide-react"

import { cn } from "@/lib/utils"

interface BreadcrumbItem {
  label: string
  href?: string
}

interface BreadcrumbProps extends React.HTMLAttributes<HTMLElement> {
  items: BreadcrumbItem[]
}

function Breadcrumb({ items, className, ...props }: BreadcrumbProps) {
  return (
    <nav
      className={cn("flex items-center space-x-1 text-sm text-muted-foreground", className)}
      aria-label="Breadcrumb"
      {...props}
    >
      <ol className="flex items-center space-x-1">
        <li>
          <a
            href="/"
            className="flex items-center hover:text-foreground transition-colors"
          >
            <Home className="h-4 w-4" />
            <span className="sr-only">Home</span>
          </a>
        </li>
        {items.map((item, index) => (
          <li key={index} className="flex items-center">
            <ChevronRight className="h-4 w-4" />
            {item.href ? (
              <a
                href={item.href}
                className="ml-1 hover:text-foreground transition-colors"
              >
                {item.label}
              </a>
            ) : (
              <span className="ml-1 font-medium text-foreground" aria-current="page">
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}

export { Breadcrumb }
