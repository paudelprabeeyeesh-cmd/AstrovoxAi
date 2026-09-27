'use client'

import Link from 'next/link'
import { Github, Twitter, Linkedin } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="col-span-1 md:col-span-2">
            <Link href="/" className="text-xl font-bold text-astrovox-600">
              AstrovoxAI
            </Link>
            <p className="mt-4 text-sm text-slate-600 max-w-md">
              Building the future of AI infrastructure. Empowering developers with powerful APIs, SDKs, and tools for next-generation AI applications.
            </p>
            <div className="flex gap-4 mt-6">
              <a href="https://github.com/YOUR_USERNAME/AstrovoxAi" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-slate-600">
                <span className="sr-only">GitHub</span>
                <Github className="h-6 w-6" />
              </a>
              <a href="https://twitter.com/astrovoxai" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-slate-600">
                <span className="sr-only">Twitter</span>
                <Twitter className="h-6 w-6" />
              </a>
              <a href="https://linkedin.com/company/astrovoxai" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-slate-600">
                <span className="sr-only">LinkedIn</span>
                <Linkedin className="h-6 w-6" />
              </a>
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Resources</h3>
            <ul className="mt-4 space-y-3">
              <li><Link href="/api-docs" className="text-sm text-slate-600 hover:text-astrovox-600">API Reference</Link></li>
              <li><Link href="/tutorials" className="text-sm text-slate-600 hover:text-astrovox-600">Tutorials</Link></li>
              <li><Link href="/examples" className="text-sm text-slate-600 hover:text-astrovox-600">Examples</Link></li>
              <li><Link href="/blog" className="text-sm text-slate-600 hover:text-astrovox-600">Blog</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Community</h3>
            <ul className="mt-4 space-y-3">
              <li><Link href="https://discord.gg/astrovox" target="_blank" className="text-sm text-slate-600 hover:text-astrovox-600">Discord</Link></li>
              <li><Link href="https://github.com/YOUR_USERNAME/AstrovoxAi/discussions" target="_blank" className="text-sm text-slate-600 hover:text-astrovox-600">Discussions</Link></li>
              <li><Link href="https://github.com/YOUR_USERNAME/AstrovoxAi/issues" target="_blank" className="text-sm text-slate-600 hover:text-astrovox-600">Issues</Link></li>
            </ul>
          </div>
        </div>
        <div className="mt-12 border-t border-slate-100 pt-8">
          <p className="text-sm text-slate-500 text-center">
            &copy; {new Date().getFullYear()} AstrovoxAI. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  )
}
