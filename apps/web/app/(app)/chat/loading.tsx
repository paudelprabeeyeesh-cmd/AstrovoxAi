import { Skeleton } from "@/components/ui/skeleton"

export default function ChatLoading() {
  return (
    <div className="flex h-full">
      <div className="flex w-64 flex-col border-r border-border bg-muted/40 p-4 space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-10 w-full" />
        <div className="space-y-2 mt-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      </div>
      <div className="flex flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-border p-4">
          <Skeleton className="h-6 w-32" />
        </div>
        <div className="flex-1 space-y-4 p-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-3/4" />
        </div>
        <div className="border-t border-border p-4">
          <Skeleton className="h-10 w-full" />
        </div>
      </div>
    </div>
  )
}
