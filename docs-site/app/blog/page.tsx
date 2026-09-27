import DocsLayout from '@/app/(docs)/layout'

export default function BlogPage() {
  const posts = [
    {
      title: 'Announcing AstrovoxAI Phase 17: Ecosystem Expansion',
      description: 'Introducing our new API portal, SDKs, enterprise features, and marketplace.',
      date: '2026-09-27',
      author: 'AstrovoxAI Team',
      href: '/blog/announcing-phase17',
    },
    {
      title: 'Building Scalable AI Applications with AstrovoxAI',
      description: 'Best practices for building production-ready AI applications.',
      date: '2026-09-20',
      author: 'Jane Doe',
      href: '/blog/scalable-ai-apps',
    },
    {
      title: 'Understanding Rate Limits and Usage Billing',
      description: 'How to optimize your API usage and manage costs effectively.',
      date: '2026-09-15',
      author: 'John Smith',
      href: '/blog/rate-limits-billing',
    },
    {
      title: 'Enterprise SSO with AstrovoxAI',
      description: 'Setting up SAML 2.0 single sign-on for your organization.',
      date: '2026-09-10',
      author: 'Alice Johnson',
      href: '/blog/enterprise-sso',
    },
  ]

  return (
    <DocsLayout>
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Blog</h1>
        <p className="mt-4 text-lg text-slate-600">
          News, updates, and insights from the AstrovoxAI team.
        </p>

        <div className="mt-8 space-y-8">
          {posts.map((post) => (
            <article key={post.title} className="border-b border-slate-200 pb-8 last:border-0">
              <a href={post.href} className="group block">
                <h2 className="text-xl font-semibold text-slate-900 group-hover:text-astrovox-600 transition-colors">
                  {post.title}
                </h2>
                <p className="mt-2 text-slate-600">{post.description}</p>
                <div className="mt-3 flex items-center gap-4 text-sm text-slate-500">
                  <span>{post.author}</span>
                  <span>&middot;</span>
                  <time dateTime={post.date}>{new Date(post.date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</time>
                </div>
              </a>
            </article>
          ))}
        </div>
      </div>
    </DocsLayout>
  )
}
