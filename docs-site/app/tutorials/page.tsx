import DocsLayout from '@/app/(docs)/layout'

export default function TutorialsPage() {
  const tutorials = [
    {
      title: 'Getting Started',
      description: 'Learn the basics of AstrovoxAI and make your first API call.',
      href: '/tutorials/getting-started',
      level: 'Beginner',
    },
    {
      title: 'Chat Completion',
      description: 'Build a chat application with streaming responses.',
      href: '/tutorials/chat-completion',
      level: 'Beginner',
    },
    {
      title: 'Streaming Responses',
      description: 'Implement real-time streaming for better UX.',
      href: '/tutorials/streaming',
      level: 'Intermediate',
    },
    {
      title: 'Function Calling',
      description: 'Enable structured outputs and function calling.',
      href: '/tutorials/function-calling',
      level: 'Intermediate',
    },
    {
      title: 'Embeddings',
      description: 'Generate and use embeddings for semantic search.',
      href: '/tutorials/embeddings',
      level: 'Intermediate',
    },
    {
      title: 'Advanced Agents',
      description: 'Build multi-step autonomous agents with tool use.',
      href: '/tutorials/advanced-agents',
      level: 'Advanced',
    },
  ]

  return (
    <DocsLayout>
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Tutorials</h1>
        <p className="mt-4 text-lg text-slate-600">
          Step-by-step guides to help you master AstrovoxAI.
        </p>

        <div className="mt-8 grid grid-cols-1 gap-6">
          {tutorials.map((tutorial) => (
            <a
              key={tutorial.title}
              href={tutorial.href}
              className="group block p-6 bg-white rounded-lg border border-slate-200 hover:border-astrovox-300 hover:shadow-md transition-all"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 group-hover:text-astrovox-600">
                    {tutorial.title}
                  </h3>
                  <p className="mt-1 text-sm text-slate-600">{tutorial.description}</p>
                </div>
                <span className="inline-flex items-center rounded-full bg-astrovox-50 px-2 py-1 text-xs font-medium text-astrovox-700">
                  {tutorial.level}
                </span>
              </div>
            </a>
          ))}
        </div>
      </div>
    </DocsLayout>
  )
}
