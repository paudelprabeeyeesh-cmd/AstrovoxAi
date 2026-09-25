"use client"
import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Globe, Code2 } from "lucide-react"

interface OAuthButtonsProps extends React.HTMLAttributes<HTMLDivElement> {
  onGoogleClick?: () => void
  onGitHubClick?: () => void
}

function OAuthButtons({ className, onGoogleClick, onGitHubClick, ...props }: OAuthButtonsProps) {
  return (
    <div className={cn("grid grid-cols-2 gap-2", className)} {...props}>
      <Button variant="outline" type="button" onClick={onGoogleClick}>
        <Globe className="mr-2 size-4" />
        Google
      </Button>
      <Button variant="outline" type="button" onClick={onGitHubClick}>
        <Code2 className="mr-2 size-4" />
        GitHub
      </Button>
    </div>
  )
}

export { OAuthButtons }
