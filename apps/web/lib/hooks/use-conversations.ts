"use client"

import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

export function useConversations() {
  const router = useRouter()

  return useQuery({
    queryKey: ["conversations"],
    queryFn: async () => {
      const data = await api.get<{ conversations: any[] }>("/conversations")
      return data.conversations
    },
  })
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: ["conversation", id],
    queryFn: async () => {
      const data = await api.get<{ conversation: any }>(`/conversations/${id}`)
      return data.conversation
    },
    enabled: !!id,
  })
}

export function useDeleteConversation() {
  const router = useRouter()

  return useQuery({
    queryKey: ["delete-conversation"],
    queryFn: async (id: string) => {
      await api.delete(`/conversations/${id}`)
      return id
    },
    enabled: false,
    onSuccess: () => {
      router.refresh()
    },
  })
}
