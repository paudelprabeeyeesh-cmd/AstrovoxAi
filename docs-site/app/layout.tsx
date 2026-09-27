import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: {
    default: 'AstrovoxAI Documentation',
    template: '%s | AstrovoxAI Docs',
  },
  description: 'Official documentation for AstrovoxAI - APIs, SDKs, tutorials, and guides.',
  keywords: ['astrovox', 'astrovoxai', 'AI', 'API', 'SDK', 'documentation'],
  authors: [{ name: 'AstrovoxAI Team' }],
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://docs.astrovox.ai',
    siteName: 'AstrovoxAI Documentation',
    title: 'AstrovoxAI Documentation',
    description: 'Official documentation for AstrovoxAI - APIs, SDKs, tutorials, and guides.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AstrovoxAI Documentation',
    description: 'Official documentation for AstrovoxAI - APIs, SDKs, tutorials, and guides.',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className={`${inter.className} antialiased bg-slate-50 text-slate-900`}>
        {children}
      </body>
    </html>
  )
}
