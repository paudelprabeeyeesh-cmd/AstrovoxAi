import { useState } from 'react'

function CodeBlock({ value, language }) {
  const [copied, setCopied] = useState(false)

  async function copyCode() {
    await navigator.clipboard?.writeText(value)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div style={{ marginTop: '10px', border: '1px solid #334155', borderRadius: '8px', overflow: 'hidden', background: '#020617' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', color: '#94a3b8', fontSize: '10px', borderBottom: '1px solid #334155' }}>
        <span>{language || 'code'}</span>
        <button type="button" onClick={copyCode} style={{ color: '#67e8f9', border: 0, background: 'transparent', cursor: 'pointer', fontSize: '10px' }}>
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre style={{ margin: 0, padding: '12px', overflowX: 'auto', fontSize: '12px', color: '#e2e8f0', fontFamily: "'Cascadia Code', Consolas, monospace" }}><code>{value}</code></pre>
    </div>
  )
}

/**
 * A deliberately small, safe renderer for the most useful chat content.
 * Content stays as React text nodes, so model output can never inject HTML.
 */
export default function MessageContent({ content }) {
  const blocks = String(content || '').split(/```/)

  return (
    <div style={{ whiteSpace: 'pre-wrap' }}>
      {blocks.map((block, index) => {
        if (index % 2 === 0) return <span key={index}>{block}</span>
        const [firstLine = '', ...lines] = block.split('\n')
        const isLanguage = /^[a-zA-Z0-9+#._-]{1,20}$/.test(firstLine.trim())
        return <CodeBlock key={index} language={isLanguage ? firstLine.trim() : ''} value={(isLanguage ? lines : [firstLine, ...lines]).join('\n').trim()} />
      })}
    </div>
  )
}
