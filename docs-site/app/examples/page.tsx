import DocsLayout from '@/app/(docs)/layout'

export default function ExamplesPage() {
  const examples = [
    {
      title: 'Basic Chatbot',
      description: 'A simple chatbot using AstrovoxAI Python SDK.',
      href: '/examples/chatbot',
      language: 'Python',
    },
    {
      title: 'RAG Pipeline',
      description: 'Build a retrieval-augmented generation pipeline.',
      href: '/examples/rag',
      language: 'Python',
    },
    {
      title: 'Multi-Agent System',
      description: 'Coordinate multiple AI agents for complex tasks.',
      href: '/examples/multi-agent',
      language: 'TypeScript',
    },
    {
      title: 'Streaming UI',
      description: 'Real-time streaming interface with React.',
      href: '/examples/streaming-ui',
      language: 'TypeScript',
    },
    {
      title: 'Batch Processing',
      description: 'Process large datasets with async workers.',
      href: '/examples/batch',
      language: 'Go',
    },
    {
      title: 'Embeddings Search',
      description: 'Semantic search using vector embeddings.',
      href: '/examples/search',
      language: 'Python',
    },
  ]

  return (
    <DocsLayout>
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Examples</h1>
        <p className="mt-4 text-lg text-slate-600">
          Explore sample applications and code snippets for common use cases.
        </p>

        <div className="mt-8 grid grid-cols-1 gap-6">
          {examples.map((example) => (
            <a
              key={example.title}
              href={example.href}
              className="group block p-6 bg-white rounded-lg border border-slate-200 hover:border-astrovox-300 hover:shadow-md transition-all"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 group-hover:text-astrovox-600">
                    {example.title}
                  </h3>
                  <p className="mt-1 text-sm text-slate-600">{example.description}</p>
                </div>
                <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                  {example.language}
                </span>
              </div>
            </a>
          ))}
        </div>
      </div>
    </DocsLayout>
  )
}
