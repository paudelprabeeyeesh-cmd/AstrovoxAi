"use client"
import * as React from "react"
import { useRouter, usePathname } from "next/navigation"
import { useSession } from "next-auth/react"

interface AuthGuardProps extends React.HTMLAttributes<HTMLDivElement> {
  fallback?: React.ReactNode
  redirectTo?: string
}

function AuthGuard({ children, fallback, redirectTo = "/login" }: AuthGuardProps) {
  const { data: session, status } = useSession()
  const router = useRouter()
  const pathname = usePathname()

  React.useEffect(() => {
    if (status === "loading") return
    if (!session) {
      router.push(`${redirectTo}?callbackUrl=${encodeURIComponent(pathname)}`)
    }
  }, [session, status, router, pathname, redirectTo])

  if (status === "loading") {
    return <>{fallback ?? <div className="flex items-center justify-center p-8">Loading...</div>}</>
  }

  if (!session) return null

  return <>{children}</>
}

export { AuthGuard }
