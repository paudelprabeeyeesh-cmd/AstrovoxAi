import DocsLayout from '@/app/(docs)/layout'

export default function Page() {
  return (
    <DocsLayout>
      <div className="prose prose-slate max-w-none">
        <h1>AstrovoxAI Documentation</h1>
        <p className="text-xl text-slate-600">
          Welcome to the AstrovoxAI documentation. Here you will find comprehensive guides,
          API references, tutorials, and examples to help you integrate AstrovoxAI into your applications.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 my-8 not-prose">
          <a href="/tutorials/getting-started" className="group block p-6 bg-white rounded-lg border border-slate-200 hover:border-astrovox-300 hover:shadow-md transition-all">
            <h3 className="text-lg font-semibold text-slate-900 group-hover:text-astrovox-600">Getting Started</h3>
            <p className="mt-2 text-sm text-slate-600">Learn the basics of AstrovoxAI and make your first API call.</p>
          </a>
          <a href="/api-docs" className="group block p-6 bg-white rounded-lg border border-slate-200 hover:border-astrovox-300 hover:shadow-md transition-all">
            <h3 className="text-lg font-semibold text-slate-900 group-hover:text-astrovox-600">API Reference</h3>
            <p className="mt-2 text-sm text-slate-600">Complete reference for all AstrovoxAI REST API endpoints.</p>
          </a>
          <a href="/examples" className="group block p-6 bg-white rounded-lg border border-slate-200 hover:border-astrovox-300 hover:shadow-md transition-all">
            <h3 className="text-lg font-semibold text-slate-900 group-hover:text-astrovox-600">Examples</h3>
            <p className="mt-2 text-sm text-slate-600">Explore sample applications and code snippets.</p>
          </a>
        </div>

        <h2>Quick Links</h2>
        <ul>
          <li><a href="/tutorials/getting-started">Getting Started Guide</a></li>
          <li><a href="/api-docs">API Reference</a></li>
          <li><a href="/sdk/python">Python SDK</a></li>
          <li><a href="/sdk/typescript">TypeScript SDK</a></li>
          <li><a href="/sdk/go">Go SDK</a></li>
          <li><a href="/sdk/java">Java SDK</a></li>
          <li><a href="/sdk/rust">Rust SDK</a></li>
          <li><a href="/blog">Blog</a></li>
        </ul>
      </div>
    </DocsLayout>
  )
}
