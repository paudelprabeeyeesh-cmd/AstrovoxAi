import { useState, useEffect, useCallback } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

function useAuthHeaders() {
  const [headers, setHeaders] = useState({ 'Content-Type': 'application/json' })

  useEffect(() => {
    const init = async () => {
      try {
        const { supabase } = await import('./supabase')
        const { data: { session } } = await supabase.auth.getSession()
        if (session?.access_token) {
          setHeaders({ 'Content-Type': 'application/json', Authorization: `Bearer ${session.access_token}` })
        }
      } catch {
        // not authenticated
      }
    }
    init()
  }, [])

  return headers
}

export default function SupportPanel({ session }) {
  const [tab, setTab] = useState('tickets')
  const headers = useAuthHeaders()

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', color: '#e2e8f0' }}>
      <div style={{ display: 'flex', gap: '8px', padding: '12px', borderBottom: '1px solid #1e293b' }}>
        {[
          { id: 'tickets', label: '🎫 Tickets' },
          { id: 'help', label: '📚 Help Center' },
          { id: 'new', label: '➕ New Ticket' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: '8px 16px',
              backgroundColor: tab === t.id ? '#06b6d4' : 'transparent',
              border: '1px solid #1e293b',
              color: tab === t.id ? '#02040a' : '#94a3b8',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: '600',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
        {tab === 'tickets' && <TicketList headers={headers} />}
        {tab === 'help' && <HelpCenter headers={headers} />}
        {tab === 'new' && <NewTicketForm headers={headers} onCreated={() => setTab('tickets')} />}
      </div>
    </div>
  )
}

function TicketList({ headers }) {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/support/tickets`, { headers })
      const data = await res.json()
      if (res.ok) setTickets(data.tickets || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => { load() }, [load])

  if (loading) return <div style={{ color: '#64748b' }}>Loading tickets...</div>
  if (selected) return <TicketDetail ticketId={selected.id} headers={headers} onBack={() => setSelected(null)} />

  return (
    <div>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>My Tickets</h3>
      {tickets.length === 0 && <p style={{ color: '#64748b' }}>No tickets yet.</p>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {tickets.map(t => (
          <div
            key={t.id}
            onClick={() => setSelected(t)}
            style={{
              padding: '12px',
              backgroundColor: 'rgba(30, 41, 59, 0.5)',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            <div style={{ fontWeight: 600, fontSize: '14px' }}>{t.subject}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              {t.status} · {t.priority} · {t.category}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function TicketDetail({ ticketId, headers, onBack }) {
  const [ticket, setTicket] = useState(null)
  const [comments, setComments] = useState([])
  const [comment, setComment] = useState('')

  useEffect(() => {
    const load = async () => {
      const res = await fetch(`${API_BASE}/support/tickets/${ticketId}`, { headers })
      const data = await res.json()
      if (res.ok) {
        setTicket(data.ticket)
        setComments(data.comments || [])
      }
    }
    load()
  }, [ticketId, headers])

  const postComment = async () => {
    if (!comment.trim()) return
    await fetch(`${API_BASE}/support/tickets/${ticketId}/comments`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ comment: comment.trim(), is_internal: false }),
    })
    setComment('')
    const res = await fetch(`${API_BASE}/support/tickets/${ticketId}`, { headers })
    const data = await res.json()
    setComments(data.comments || [])
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <button onClick={onBack} style={{ marginBottom: '12px', background: 'transparent', border: '1px solid #1e293b', color: '#94a3b8', borderRadius: '6px', cursor: 'pointer', padding: '6px 12px', fontSize: '12px' }}>
        ← Back
      </button>
      {ticket && (
        <>
          <h3 style={{ margin: '0 0 8px 0', color: '#06b6d4' }}>{ticket.subject}</h3>
          <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '12px' }}>
            Status: {ticket.status} · Priority: {ticket.priority} · Assigned: {ticket.assigned_to || 'Unassigned'}
          </div>
          <p style={{ fontSize: '13px', lineHeight: 1.5, color: '#cbd5e1', marginBottom: '16px' }}>{ticket.description}</p>
          <div style={{ flex: 1, overflow: 'auto', border: '1px solid #1e293b', borderRadius: '8px', padding: '12px', marginBottom: '12px' }}>
            {comments.map(c => (
              <div key={c.id} style={{ marginBottom: '8px', padding: '8px', backgroundColor: 'rgba(15, 23, 42, 0.6)', borderRadius: '6px' }}>
                <div style={{ fontSize: '10px', color: '#64748b' }}>{c.user_id === session?.user?.id ? 'You' : 'Agent'} · {new Date(c.created_at).toLocaleString()}</div>
                <div style={{ fontSize: '13px', marginTop: '4px' }}>{c.comment}</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder="Write a comment..."
              style={{ flex: 1, padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }}
              onKeyDown={e => e.key === 'Enter' && postComment()}
            />
            <button onClick={postComment} style={{ padding: '10px 16px', backgroundColor: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer' }}>
              Send
            </button>
          </div>
        </>
      )}
    </div>
  )
}

function HelpCenter({ headers }) {
  const [articles, setArticles] = useState([])
  const [categories, setCategories] = useState([])
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/support/articles`, { headers })
      .then(r => r.json())
      .then(d => setArticles(d.articles || []))
    fetch(`${API_BASE}/support/categories`, { headers })
      .then(r => r.json())
      .then(d => setCategories(d.categories || []))
  }, [headers])

  if (selected) return <ArticleDetail slug={selected} headers={headers} onBack={() => setSelected(null)} />

  return (
    <div>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>Help Center</h3>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <button onClick={() => setSelected(null)} style={{ padding: '4px 12px', fontSize: '11px', background: '#06b6d4', border: 'none', borderRadius: '4px', color: '#02040a', cursor: 'pointer' }}>
          All
        </button>
        {categories.map(c => (
          <button key={c.id} onClick={() => setSelected(c.name)} style={{ padding: '4px 12px', fontSize: '11px', background: 'transparent', border: '1px solid #1e293b', borderRadius: '4px', color: '#94a3b8', cursor: 'pointer' }}>
            {c.name}
          </button>
        ))}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {articles.map(a => (
          <div key={a.id} onClick={() => setSelected(a.slug)} style={{ padding: '12px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px', cursor: 'pointer' }}>
            <div style={{ fontWeight: 600, fontSize: '14px' }}>{a.title}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>{a.category} · {a.views} views</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ArticleDetail({ slug, headers, onBack }) {
  const [article, setArticle] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/support/articles/${encodeURIComponent(slug)}`, { headers })
      .then(r => r.json())
      .then(d => setArticle(d.article))
  }, [slug, headers])

  if (!article) return <div style={{ color: '#64748b' }}>Loading...</div>

  return (
    <div>
      <button onClick={onBack} style={{ marginBottom: '12px', background: 'transparent', border: '1px solid #1e293b', color: '#94a3b8', borderRadius: '6px', cursor: 'pointer', padding: '6px 12px', fontSize: '12px' }}>
        ← Back
      </button>
      <h3 style={{ margin: '0 0 8px 0', color: '#06b6d4' }}>{article.title}</h3>
      <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '16px' }}>{article.category} · {article.views} views</div>
      <div style={{ fontSize: '13px', lineHeight: 1.7, color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>{article.content}</div>
      <div style={{ marginTop: '16px', display: 'flex', gap: '8px' }}>
        <FeedbackButtons slug={slug} headers={headers} />
      </div>
    </div>
  )
}

function FeedbackButtons({ slug, headers }) {
  const [voted, setVoted] = useState(null)
  const vote = async (helpful) => {
    await fetch(`${API_BASE}/support/articles/${encodeURIComponent(slug)}/feedback`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ helpful }),
    })
    setVoted(helpful)
  }
  return (
    <>
      <button onClick={() => vote(true)} disabled={voted !== null} style={{ padding: '6px 12px', background: voted === true ? '#22c55e' : 'transparent', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', cursor: 'pointer', fontSize: '12px' }}>
        👍 Helpful
      </button>
      <button onClick={() => vote(false)} disabled={voted !== null} style={{ padding: '6px 12px', background: voted === false ? '#ef4444' : 'transparent', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', cursor: 'pointer', fontSize: '12px' }}>
        👎 Not helpful
      </button>
    </>
  )
}

function NewTicketForm({ headers, onCreated }) {
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('medium')
  const [category, setCategory] = useState('general')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const submit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/support/tickets`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ subject, description, priority, category, tags: [] }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to create ticket')
      setSubject('')
      setDescription('')
      onCreated?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>Create Support Ticket</h3>
      {error && <div style={{ color: '#ef4444', fontSize: '12px', marginBottom: '12px' }}>{error}</div>}
      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '600px' }}>
        <div>
          <label style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Subject</label>
          <input value={subject} onChange={e => setSubject(e.target.value)} required style={{ width: '100%', padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }} />
        </div>
        <div>
          <label style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Category</label>
          <select value={category} onChange={e => setCategory(e.target.value)} style={{ width: '100%', padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }}>
            <option value="general">General</option>
            <option value="billing">Billing</option>
            <option value="technical">Technical</option>
            <option value="access">Access</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Priority</label>
          <select value={priority} onChange={e => setPriority(e.target.value)} style={{ width: '100%', padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Description</label>
          <textarea value={description} onChange={e => setDescription(e.target.value)} required rows={5} style={{ width: '100%', padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px', resize: 'vertical' }} />
        </div>
        <button type="submit" disabled={submitting} style={{ padding: '10px 16px', backgroundColor: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer', alignSelf: 'flex-start' }}>
          {submitting ? 'Submitting...' : 'Submit Ticket'}
        </button>
      </form>
    </div>
  )
}
