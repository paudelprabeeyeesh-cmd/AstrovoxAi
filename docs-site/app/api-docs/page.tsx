import DocsLayout from '@/app/(docs)/layout'

export default function APIDocsPage() {
  return (
    <DocsLayout>
      <div className="prose prose-slate max-w-none">
        <h1>API Reference</h1>
        <p className="text-slate-600">
          Complete reference for the AstrovoxAI REST API. All requests require authentication via Bearer token.
        </p>

        <h2>Base URL</h2>
        <pre><code>https://api.astrovox.ai/v1</code></pre>

        <h2>Authentication</h2>
        <p>Include your API key in the Authorization header:</p>
        <pre><code>Authorization: Bearer avx_...</code></pre>

        <h2>Endpoints</h2>

        <h3>Chat Completions</h3>
        <pre><code>POST /chat/completions</code></pre>
        <p>Create a chat completion. Supports streaming and function calling.</p>

        <h3>Embeddings</h3>
        <pre><code>POST /embeddings</code></pre>
        <p>Generate embeddings for input text.</p>

        <h3>Models</h3>
        <pre><code>GET /models</code></pre>
        <p>List available models and their capabilities.</p>

        <h3>Conversations</h3>
        <pre><code>GET /conversations
POST /conversations
GET /conversations/{id}
DELETE /conversations/{id}</code></pre>

        <h3>Webhooks</h3>
        <pre><code>POST /webhooks
GET /webhooks
DELETE /webhooks/{id}</code></pre>

        <h2>Error Codes</h2>
        <table className="min-w-full divide-y divide-slate-200">
          <thead>
            <tr>
              <th className="px-4 py-2 text-left text-sm font-medium text-slate-500">Code</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-slate-500">Meaning</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            <tr><td className="px-4 py-2 text-sm">400</td><td className="px-4 py-2 text-sm">Bad Request</td></tr>
            <tr><td className="px-4 py-2 text-sm">401</td><td className="px-4 py-2 text-sm">Unauthorized</td></tr>
            <tr><td className="px-4 py-2 text-sm">403</td><td className="px-4 py-2 text-sm">Forbidden</td></tr>
            <tr><td className="px-4 py-2 text-sm">404</td><td className="px-4 py-2 text-sm">Not Found</td></tr>
            <tr><td className="px-4 py-2 text-sm">429</td><td className="px-4 py-2 text-sm">Rate Limit Exceeded</td></tr>
            <tr><td className="px-4 py-2 text-sm">500</td><td className="px-4 py-2 text-sm">Internal Server Error</td></tr>
          </tbody>
        </table>
      </div>
    </DocsLayout>
  )
}
