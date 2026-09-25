import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

type Theme = 'light' | 'dark' | 'system'

interface ModalState {
  id: string
  isOpen: boolean
  data?: Record<string, unknown>
}

interface UIState {
  sidebarOpen: boolean
  theme: Theme
  resolvedTheme: 'light' | 'dark'
  modals: ModalState[]
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setTheme: (theme: Theme) => void
  openModal: (id: string, data?: Record<string, unknown>) => void
  closeModal: (id: string) => void
  closeAllModals: () => void
}

export const useUIStore = create<UIState>()(
  devtools(
    persist(
      (set, get) => ({
        sidebarOpen: true,
        theme: 'system',
        resolvedTheme: 'light',
        modals: [],

        toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
        setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
        setTheme: (theme) => set({ theme }),

        openModal: (id, data) =>
          set((state) => ({
            modals: state.modals.some((m) => m.id === id)
              ? state.modals.map((m) => (m.id === id ? { ...m, isOpen: true, data } : m))
              : [...state.modals, { id, isOpen: true, data }],
          })),

        closeModal: (id) =>
          set((state) => ({
            modals: state.modals.map((m) => (m.id === id ? { ...m, isOpen: false } : m)),
          })),

        closeAllModals: () => set({ modals: [] }),
      }),
      {
        name: 'ui-storage',
        onRehydrateStorage: () => (state) => {
          if (state) {
            state.resolvedTheme = state.theme === 'system'
              ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
              : state.theme
          }
        },
      }
    ),
    { name: 'UIStore' }
  )
)
