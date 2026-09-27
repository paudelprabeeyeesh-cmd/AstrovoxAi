'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronRight } from 'lucide-react'

const sidebarGroups = [
  {
    title: 'Getting Started',
    links: [
      { name: 'Introduction', href: '/tutorials/getting-started' },
      { name: 'Installation', href: '/tutorials/getting-started#installation' },
      { name: 'Quick Start', href: '/tutorials/getting-started#quick-start' },
    ],
  },
  {
    title: 'Core Concepts',
    links: [
      { name: 'API Overview', href: '/api-docs' },
      { name: 'Authentication', href: '/api-docs#authentication' },
      { name: 'Rate Limits', href: '/api-docs#rate-limits' },
      { name: 'Error Handling', href: '/api-docs#errors' },
    ],
  },
  {
    title: 'Tutorials',
    links: [
      { name: 'Chat Completion', href: '/tutorials/chat-completion' },
      { name: 'Streaming Responses', href: '/tutorials/streaming' },
      { name: 'Function Calling', href: '/tutorials/function-calling' },
      { name: 'Embeddings', href: '/tutorials/embeddings' },
    ],
  },
  {
    title: 'Examples',
    links: [
      { name: 'Basic Chatbot', href: '/examples/chatbot' },
      { name: 'RAG Pipeline', href: '/examples/rag' },
      { name: 'Multi-Agent', href: '/examples/multi-agent' },
    ],
  },
  {
    title: 'SDKs',
    links: [
      { name: 'Python', href: '/sdk/python' },
      { name: 'TypeScript', href: '/sdk/typescript' },
      { name: 'Go', href: '/sdk/go' },
      { name: 'Java', href: '/sdk/java' },
      { name: 'Rust', href: '/sdk/rust' },
    ],
  },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="hidden lg:block fixed top-16 left-0 w-64 h-[calc(100vh-4rem)] overflow-y-auto border-r border-slate-200 bg-white">
      <nav className="p-4 space-y-6">
        {sidebarGroups.map((group) => (
          <div key={group.title}>
            <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-2">
              {group.title}
            </h3>
            <ul className="space-y-1">
              {group.links.map((link) => {
                const isActive = pathname === link.href || pathname.startsWith(link.href.split('#')[0])
                return (
                  <li key={link.name}>
                    <Link
                      href={link.href}
                      className={`group flex items-center rounded-md px-2 py-1.5 text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-astrovox-50 text-astrovox-700'
                          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                      }`}
                    >
                      {link.name}
                      {isActive && <ChevronRight className="ml-auto h-4 w-4 text-astrovox-600" />}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  )
}
