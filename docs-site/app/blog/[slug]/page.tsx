import DocsLayout from '@/app/(docs)/layout'

export default function AnnouncePost() {
  return (
    <DocsLayout>
      <article className="prose prose-slate max-w-none">
        <h1>Announcing AstrovoxAI Phase 17: Ecosystem Expansion</h1>
        <p className="text-sm text-slate-500">
          Published on September 27, 2026 by the AstrovoxAI Team
        </p>

        <p>
          Today we are thrilled to announce Phase 17 of AstrovoxAI, our most comprehensive
          release yet. This release expands the AstrovoxAI platform into a full business and
          ecosystem package, empowering developers and enterprises alike.
        </p>

        <h2>What is new</h2>
        <ul>
          <li><strong>Public API Portal</strong> - A developer-friendly portal with comprehensive API documentation, key management, and usage analytics.</li>
          <li><strong>Multi-Language SDKs</strong> - Official SDKs for Python, TypeScript, Go, Java, and Rust.</li>
          <li><strong>Enterprise Features</strong> - SSO/SAML, audit logging, compliance reports, SLA guarantees, and private deployments.</li>
          <li><strong>Billing & Subscriptions</strong> - Usage-based billing, Stripe integration, and flexible subscription management.</li>
          <li><strong>Usage Analytics</strong> - Real-time dashboards, cost tracking, performance metrics, and user behavior analysis.</li>
          <li><strong>Marketplace</strong> - Model and plugin marketplace with revenue sharing for creators.</li>
          <li><strong>Documentation Site</strong> - A brand new docs site with tutorials, examples, and a community blog.</li>
        </ul>

        <h2>Getting Started</h2>
        <p>
          Visit our <a href="/tutorials/getting-started">Getting Started guide</a> to create your
          developer account, generate an API key, and make your first request.
        </p>

        <h2>Enterprise Inquiries</h2>
        <p>
          For enterprise SSO, private deployments, and SLA agreements, contact
          <a href="mailto:enterprise@astrovox.ai">enterprise@astrovox.ai</a>.
        </p>
      </article>
    </DocsLayout>
  )
}
