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
      <div style={{ display: 'flex', gap: '8px', padding: '12px', borderBottom: '1px solid #1e293b', flexWrap: 'wrap' }}>
        {[
          { id: 'tickets', label: '🎫 Tickets' },
          { id: 'help', label: '📚 Help Center' },
          { id: 'chat', label: '💬 Live Chat' },
          { id: 'feedback', label: '💡 Feedback' },
          { id: 'bugs', label: '🐛 Bugs' },
          { id: 'features', label: '✨ Features' },
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
        {tab === 'chat' && <LiveChat headers={headers} session={session} />}
        {tab === 'feedback' && <FeedbackForm headers={headers} />}
        {tab === 'bugs' && <BugReportList headers={headers} />}
        {tab === 'features' && <FeatureRequestList headers={headers} />}
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
            style={{ padding: '12px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px', cursor: 'pointer' }}
          >
            <div style={{ fontWeight: 600, fontSize: '14px' }}>{t.subject}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>{t.status} · {t.priority} · {t.category}</div>
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
      if (res.ok) { setTicket(data.ticket); setComments(data.comments || []) }
    }
    load()
  }, [ticketId, headers])

  const postComment = async () => {
    if (!comment.trim()) return
    await fetch(`${API_BASE}/support/tickets/${ticketId}/comments`, { method: 'POST', headers, body: JSON.stringify({ comment: comment.trim(), is_internal: false }) })
    setComment('')
    const res = await fetch(`${API_BASE}/support/tickets/${ticketId}`, { headers })
    const data = await res.json()
    setComments(data.comments || [])
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <button onClick={onBack} style={{ marginBottom: '12px', background: 'transparent', border: '1px solid #1e293b', color: '#94a3b8', borderRadius: '6px', cursor: 'pointer', padding: '6px 12px', fontSize: '12px' }}>← Back</button>
      {ticket && (
        <>
          <h3 style={{ margin: '0 0 8px 0', color: '#06b6d4' }}>{ticket.subject}</h3>
          <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '12px' }}>Status: {ticket.status} · Priority: {ticket.priority} · Assigned: {ticket.assigned_to || 'Unassigned'}</div>
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
            <input value={comment} onChange={e => setComment(e.target.value)} placeholder="Write a comment..." style={{ flex: 1, padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }} onKeyDown={e => e.key === 'Enter' && postComment()} />
            <button onClick={postComment} style={{ padding: '10px 16px', backgroundColor: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer' }}>Send</button>
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
    fetch(`${API_BASE}/support/articles`, { headers }).then(r => r.json()).then(d => setArticles(d.articles || []))
    fetch(`${API_BASE}/support/categories`, { headers }).then(r => r.json()).then(d => setCategories(d.categories || []))
  }, [headers])

  if (selected) return <ArticleDetail slug={selected} headers={headers} onBack={() => setSelected(null)} />

  return (
    <div>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>Help Center</h3>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <button onClick={() => setSelected(null)} style={{ padding: '4px 12px', fontSize: '11px', background: '#06b6d4', border: 'none', borderRadius: '4px', color: '#02040a', cursor: 'pointer' }}>All</button>
        {categories.map(c => (
          <button key={c.id} onClick={() => setSelected(c.name)} style={{ padding: '4px 12px', fontSize: '11px', background: 'transparent', border: '1px solid #1e293b', borderRadius: '4px', color: '#94a3b8', cursor: 'pointer' }}>{c.name}</button>
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
    fetch(`${API_BASE}/support/articles/${encodeURIComponent(slug)}`, { headers }).then(r => r.json()).then(d => setArticle(d.article))
  }, [slug, headers])

  if (!article) return <div style={{ color: '#64748b' }}>Loading...</div>

  return (
    <div>
      <button onClick={onBack} style={{ marginBottom: '12px', background: 'transparent', border: '1px solid #1e293b', color: '#94a3b8', borderRadius: '6px', cursor: 'pointer', padding: '6px 12px', fontSize: '12px' }}>← Back</button>
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
    await fetch(`${API_BASE}/support/articles/${encodeURIComponent(slug)}/feedback`, { method: 'POST', headers, body: JSON.stringify({ helpful }) })
    setVoted(helpful)
  }
  return (
    <>
      <button onClick={() => vote(true)} disabled={voted !== null} style={{ padding: '6px 12px', background: voted === true ? '#22c55e' : 'transparent', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', cursor: 'pointer', fontSize: '12px' }}>👍 Helpful</button>
      <button onClick={() => vote(false)} disabled={voted !== null} style={{ padding: '6px 12px', background: voted === false ? '#ef4444' : 'transparent', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', cursor: 'pointer', fontSize: '12px' }}>👎 Not helpful</button>
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
      const res = await fetch(`${API_BASE}/support/tickets`, { method: 'POST', headers, body: JSON.stringify({ subject, description, priority, category, tags: [] }) })
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

function LiveChat({ headers, session }) {
  const [sessions, setSessions] = useState([])
  const [active, setActive] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [creating, setCreating] = useState(false)

  const loadSessions = useCallback(async () => {
    const res = await fetch(`${API_BASE}/cx/chat/sessions`, { headers })
    const data = await res.json()
    if (res.ok) setSessions(data.sessions || [])
  }, [headers])

  useEffect(() => { loadSessions() }, [loadSessions])

  const createSession = async () => {
    setCreating(true)
    const res = await fetch(`${API_BASE}/cx/chat/sessions`, { method: 'POST', headers, body: JSON.stringify({}) })
    const data = await res.json()
    if (res.ok) {
      setSessions(prev => [data.session, ...prev])
      setActive(data.session)
    }
    setCreating(false)
  }

  const loadMessages = async (sessionId) => {
    const res = await fetch(`${API_BASE}/cx/chat/sessions/${sessionId}/messages`, { headers })
    const data = await res.json()
    if (res.ok) setMessages(data.messages || [])
  }

  useEffect(() => { if (active) loadMessages(active.id) }, [active, loadMessages])

  const send = async () => {
    if (!input.trim() || !active) return
    await fetch(`${API_BASE}/cx/chat/sessions/${active.id}/messages`, { method: 'POST', headers, body: JSON.stringify({ message: input.trim() }) })
    setInput('')
    loadMessages(active.id)
  }

  if (active) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3 style={{ margin: 0, color: '#06b6d4' }}>Live Chat</h3>
          <button onClick={() => setActive(null)} style={{ background: 'transparent', border: '1px solid #1e293b', color: '#94a3b8', borderRadius: '6px', cursor: 'pointer', padding: '6px 12px', fontSize: '12px' }}>End Chat</button>
        </div>
        <div style={{ flex: 1, overflow: 'auto', border: '1px solid #1e293b', borderRadius: '8px', padding: '12px', marginBottom: '12px' }}>
          {messages.map(m => (
            <div key={m.id} style={{ marginBottom: '8px', padding: '8px', backgroundColor: m.sender_id === session?.user?.id ? 'rgba(6, 182, 212, 0.1)' : 'rgba(15, 23, 42, 0.6)', borderRadius: '6px', textAlign: m.sender_id === session?.user?.id ? 'right' : 'left' }}>
              <div style={{ fontSize: '13px' }}>{m.message}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input value={input} onChange={e => setInput(e.target.value)} placeholder="Type a message..." style={{ flex: 1, padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }} onKeyDown={e => e.key === 'Enter' && send()} />
          <button onClick={send} style={{ padding: '10px 16px', backgroundColor: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer' }}>Send</button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>Live Chat</h3>
      <button onClick={createSession} disabled={creating} style={{ padding: '10px 16px', backgroundColor: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer', marginBottom: '16px' }}>
        {creating ? 'Starting...' : 'Start New Chat'}
      </button>
      {sessions.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {sessions.map(s => (
            <div key={s.id} onClick={() => setActive(s)} style={{ padding: '12px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px', cursor: 'pointer' }}>
              <div style={{ fontWeight: 600, fontSize: '14px' }}>Session {s.id.slice(0, 8)}</div>
              <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>{s.status} · {new Date(s.started_at).toLocaleString()}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function FeedbackForm({ headers }) {
  const [type, setType] = useState('general')
  const [rating, setRating] = useState('')
  const [comment, setComment] = useState('')
  const [pageUrl, setPageUrl] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    await fetch(`${API_BASE}/cx/feedback`, { method: 'POST', headers, body: JSON.stringify({ type, rating: rating ? parseInt(rating) : null, comment, page_url: pageUrl || null }) })
    setSubmitted(true)
  }

  if (submitted) return <div style={{ color: '#22c55e' }}>Thank you for your feedback!</div>

  return (
    <div>
      <h3 style={{ marginTop: 0, color: '#06b6d4' }}>Submit Feedback</h3>
      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '600px' }}>
        <div>
          <label style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Type</label>
          <select value={type} onChange={e => setType(e.target.value)} style={{ width: '100%', padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }}>
            <option value="general">General</option>
            <option value="bug">Bug</option>
            <option value="feature">Feature</option>
            <option value="ux">UX</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Rating (1-5)</label>
          <input type="number" min="1" max="5" value={rating} onChange={e => setRating(e.target.value)} style={{ width: '100%', padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }} />
        </div>
        <div>
          <label style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Comment</label>
          <textarea value={comment} onChange={e => setComment(e.target.value)} rows={4} style={{ width: '100%', padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px', resize: 'vertical' }} />
        </div>
        <div>
          <label style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Page URL</label>
          <input value={pageUrl} onChange={e => setPageUrl(e.target.value)} style={{ width: '100%', padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }} />
        </div>
        <button type="submit" style={{ padding: '10px 16px', backgroundColor: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer', alignSelf: 'flex-start' }}>Submit Feedback</button>
      </form>
    </div>
  )
}

function BugReportList({ headers }) {
  const [bugs, setBugs] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', severity: 'medium', steps: '' })

  const load = async () => {
    const res = await fetch(`${API_BASE}/cx/bugs`, { headers })
    const data = await res.json()
    if (res.ok) setBugs(data.bugs || [])
  }

  useEffect(() => { load() }, [headers])

  const submit = async (e) => {
    e.preventDefault()
    await fetch(`${API_BASE}/cx/bugs`, { method: 'POST', headers, body: JSON.stringify({ ...form, steps_to_reproduce: form.steps || null }) })
    setForm({ title: '', description: '', severity: 'medium', steps: '' })
    setShowForm(false)
    load()
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, color: '#06b6d4' }}>Bug Reports</h3>
        <button onClick={() => setShowForm(!showForm)} style={{ padding: '6px 12px', background: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', cursor: 'pointer', fontSize: '12px' }}>{showForm ? 'Cancel' : 'Report Bug'}</button>
      </div>
      {showForm && (
        <form onSubmit={submit} style={{ marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '600px' }}>
          <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Title" required style={{ padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }} />
          <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Description" required rows={3} style={{ padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px', resize: 'vertical' }} />
          <select value={form.severity} onChange={e => setForm({ ...form, severity: e.target.value })} style={{ padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <textarea value={form.steps} onChange={e => setForm({ ...form, steps: e.target.value })} placeholder="Steps to reproduce (optional)" rows={2} style={{ padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px', resize: 'vertical' }} />
          <button type="submit" style={{ padding: '10px 16px', backgroundColor: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer', alignSelf: 'flex-start' }}>Submit Bug Report</button>
        </form>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {bugs.map(b => (
          <div key={b.id} style={{ padding: '12px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
            <div style={{ fontWeight: 600, fontSize: '14px' }}>{b.title}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>{b.status} · {b.severity}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function FeatureRequestList({ headers }) {
  const [requests, setRequests] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', description: '' })

  const load = async () => {
    const res = await fetch(`${API_BASE}/cx/features`, { headers })
    const data = await res.json()
    if (res.ok) setRequests(data.requests || [])
  }

  useEffect(() => { load() }, [headers])

  const submit = async (e) => {
    e.preventDefault()
    await fetch(`${API_BASE}/cx/features`, { method: 'POST', headers, body: JSON.stringify(form) })
    setForm({ title: '', description: '' })
    setShowForm(false)
    load()
  }

  const vote = async (id) => {
    await fetch(`${API_BASE}/cx/features/${id}/vote`, { method: 'POST', headers })
    load()
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, color: '#06b6d4' }}>Feature Requests</h3>
        <button onClick={() => setShowForm(!showForm)} style={{ padding: '6px 12px', background: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', cursor: 'pointer', fontSize: '12px' }}>{showForm ? 'Cancel' : 'Request Feature'}</button>
      </div>
      {showForm && (
        <form onSubmit={submit} style={{ marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '600px' }}>
          <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Feature title" required style={{ padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px' }} />
          <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Describe your feature" required rows={3} style={{ padding: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', color: '#e2e8f0', fontSize: '13px', resize: 'vertical' }} />
          <button type="submit" style={{ padding: '10px 16px', backgroundColor: '#06b6d4', border: 'none', borderRadius: '6px', color: '#02040a', fontWeight: 600, cursor: 'pointer', alignSelf: 'flex-start' }}>Submit Request</button>
        </form>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {requests.map(r => (
          <div key={r.id} style={{ padding: '12px', backgroundColor: 'rgba(30, 41, 59, 0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
            <div style={{ fontWeight: 600, fontSize: '14px' }}>{r.title}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>{r.status} · {r.votes} votes</div>
            <button onClick={() => vote(r.id)} style={{ marginTop: '8px', padding: '4px 10px', background: 'transparent', border: '1px solid #1e293b', borderRadius: '4px', color: '#94a3b8', cursor: 'pointer', fontSize: '11px' }}>Upvote</button>
          </div>
        ))}
      </div>
    </div>
  )
}
