import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'

const API = import.meta.env.VITE_API_URL || '/api'
const initial = { context_length: 32, hidden_size: 16, num_layers: 1, num_heads: 2,
  batch_size: 1, max_steps: 10, checkpoint_interval: 5, seed: 17, memory_budget_mib: 256, reserve_memory_mib: 1536, optimizer: 'adamw' }

function LossChart({ points }) {
  if (!points?.length) return null
  const losses = points.map(point => Number(point.training_loss)).filter(Number.isFinite)
  if (!losses.length) return null
  const low = Math.min(...losses)
  const high = Math.max(...losses)
  const spread = high - low || 1
  const coordinates = losses.map((loss, index) => `${losses.length === 1 ? 300 : 24 + index * (552 / (losses.length - 1))},${124 - ((loss - low) / spread) * 108}`).join(' ')
  return <div style={styles.chartWrap}>
    <div style={styles.metrics}>Measured training loss · {losses.length} recorded steps · range {low.toFixed(4)}–{high.toFixed(4)}</div>
    <svg role="img" aria-label="Measured training loss by recorded training step" viewBox="0 0 600 140" style={styles.chart}>
      <line x1="24" y1="16" x2="24" y2="124" stroke="#334155" />
      <line x1="24" y1="124" x2="576" y2="124" stroke="#334155" />
      {losses.length > 1 && <polyline fill="none" stroke="#22d3ee" strokeWidth="2" points={coordinates} />}
      {losses.length === 1 && <circle cx="300" cy="70" r="4" fill="#22d3ee" />}
    </svg>
  </div>
}

export default function NeuralLabPanel() {
  const [datasets, setDatasets] = useState([])
  const [jobs, setJobs] = useState([])
  const [models, setModels] = useState([])
  const [selection, setSelection] = useState(null)
  const [datasetId, setDatasetId] = useState('')
  const [evaluationDatasetId, setEvaluationDatasetId] = useState('')
  const [config, setConfig] = useState(initial)
  const [file, setFile] = useState(null)
  const [provenance, setProvenance] = useState('User-provided text')
  const [license, setLicense] = useState('Permission confirmed by user')
  const [previewCharacters, setPreviewCharacters] = useState(500)
  const [modelName, setModelName] = useState('Tiny Transformer experiment')
  const [prompt, setPrompt] = useState('')
  const [generated, setGenerated] = useState('')
  const [generationTokens, setGenerationTokens] = useState(64)
  const [temperature, setTemperature] = useState(1)
  const [topK, setTopK] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  const request = useCallback(async (path, options = {}) => {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) throw new Error('Your session expired. Sign in again.')
    const response = await fetch(`${API}/neural-lab${path}`, {
      ...options,
      headers: { Authorization: `Bearer ${session.access_token}`, ...options.headers }
    })
    if (!response.ok) {
      let detail = `Request failed (${response.status})`
      try { detail = (await response.json()).detail || detail } catch { /* keep status message */ }
      throw new Error(detail)
    }
    return response.status === 204 ? null : response.json()
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [datasetResult, jobResult, modelResult] = await Promise.all([request('/datasets'), request('/jobs'), request('/models')])
      setDatasets(datasetResult.datasets || [])
      setJobs(jobResult.jobs || [])
      setModels(modelResult.models || [])
      setSelection(modelResult.selection)
      setDatasetId(current => current || datasetResult.datasets?.[0]?.id || '')
      setEvaluationDatasetId(current => current || datasetResult.datasets?.[0]?.id || '')
      setMessage('')
    } catch (error) { setMessage(error.message) }
  }, [request])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 4000)
    return () => window.clearInterval(timer)
  }, [refresh])

  async function upload(event) {
    event.preventDefault()
    if (!file) return
    setBusy(true)
    try {
      const body = new FormData()
      body.append('file', file)
      body.append('provenance', provenance)
      body.append('license_note', license)
      body.append('preview_characters', String(previewCharacters))
      const result = await request('/datasets', { method: 'POST', body })
      setDatasetId(result.dataset_id)
      setFile(null)
      await refresh()
      setMessage(`Added ${result.characters.toLocaleString()} characters (${result.bytes.toLocaleString()} bytes).`)
    } catch (error) { setMessage(error.message) } finally { setBusy(false) }
  }

  async function start(resumeJob = null) {
    setBusy(true)
    try {
      const resumeConfig = resumeJob?.config
      const parameters = resumeJob ? {
        ...config,
        ...Object.fromEntries(Object.keys(initial).map(key => [key, resumeConfig?.[key] ?? initial[key]])),
        max_steps: Math.max(config.max_steps, (resumeJob.metrics?.step ?? 0) + 10)
      } : config
      const result = await request('/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...parameters, dataset_id: resumeJob?.dataset_id || datasetId,
          ...(resumeJob ? { resume_job_id: resumeJob.id } : {}) }) })
      setMessage(`Queued job ${result.job_id.slice(0, 8)} · estimated ${result.estimated_parameter_count.toLocaleString()} parameters · estimated ${Math.ceil(result.estimated_memory_bytes / 1048576)} MiB`)
      await refresh()
    } catch (error) { setMessage(error.message) } finally { setBusy(false) }
  }

  async function cancel(jobId) {
    try { await request(`/jobs/${jobId}/cancel`, { method: 'POST' }); await refresh() }
    catch (error) { setMessage(error.message) }
  }

  async function register(jobId) {
    try {
      await request('/models', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, name: modelName }) })
      setMessage('Completed checkpoint registered as an experimental model.')
      await refresh()
    } catch (error) { setMessage(error.message) }
  }

  async function selectModel(modelId) {
    try { await request(`/models/${modelId}/select`, { method: 'POST' }); await refresh() }
    catch (error) { setMessage(error.message) }
  }

  async function rollbackModel() {
    try { await request('/models/rollback', { method: 'POST' }); await refresh() }
    catch (error) { setMessage(error.message) }
  }

  async function evaluate(modelId) {
    try {
      const result = await request(`/models/${modelId}/evaluate`, { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ dataset_id: evaluationDatasetId }) })
      setMessage(`Measured next-token cross-entropy ${result.next_token_cross_entropy.toFixed(4)} over ${result.tokens_measured} tokens.`)
      await refresh()
    } catch (error) { setMessage(error.message) }
  }

  async function deleteDataset(id) {
    if (!window.confirm('Delete this dataset and its stored text?')) return
    try {
      await request(`/datasets/${id}`, { method: 'DELETE' })
      if (datasetId === id) setDatasetId('')
      if (evaluationDatasetId === id) setEvaluationDatasetId('')
      setMessage('Dataset deleted.')
      await refresh()
    } catch (error) { setMessage(error.message) }
  }

  async function generate(event) {
    event.preventDefault()
    try {
      const result = await request('/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, max_new_tokens: generationTokens, temperature, top_k: topK === '' ? null : Number(topK) }) })
      setGenerated(result.text)
    } catch (error) { setMessage(error.message) }
  }

  const field = (key, label, min, max) => <label key={key} style={styles.label}>{label}
    <input type="number" min={min} max={max} value={config[key]} onChange={e => setConfig({ ...config, [key]: Number(e.target.value) })} style={styles.input} />
  </label>

  return <section style={styles.panel}>
    <h2 style={styles.heading}>Neural Lab <small style={styles.tag}>Experimental · CPU</small></h2>
    <p style={styles.sub}>Train a tiny character-level Transformer from random initialization. This model does not serve Astrovox chat.</p>
    {message && <div role="status" style={styles.notice}>{message}</div>}
    <div style={styles.columns}>
      <div>
        <h3 style={styles.subheading}>Dataset</h3>
        <form onSubmit={upload} style={styles.form}>
          <input aria-label="UTF-8 text file" type="file" accept=".txt,.md,text/plain" onChange={e => setFile(e.target.files?.[0] || null)} style={styles.input} />
          <input aria-label="Dataset provenance" value={provenance} onChange={e => setProvenance(e.target.value)} placeholder="Provenance" style={styles.input} />
          <input aria-label="Dataset license" value={license} onChange={e => setLicense(e.target.value)} placeholder="License note" style={styles.input} />
          <label style={styles.label}>Preview characters (0–4096)<input aria-label="Preview character limit" type="number" min="0" max="4096" value={previewCharacters} onChange={e => setPreviewCharacters(Number(e.target.value))} style={styles.input} /></label>
          <button disabled={!file || busy} style={styles.button}>Upload UTF-8 text (16 MiB max)</button>
        </form>
        <label style={styles.label}>Training dataset
          <select value={datasetId} onChange={e => setDatasetId(e.target.value)} style={styles.input}>
            <option value="">Choose a dataset</option>
            {datasets.map(d => <option key={d.id} value={d.id}>{d.name} · {d.metadata?.size_bytes ?? '?'} bytes</option>)}
          </select>
        </label>
        {datasetId && <button onClick={() => deleteDataset(datasetId)} style={styles.cancel}>Delete selected dataset</button>}
        {datasets.find(dataset => dataset.id === datasetId)?.metadata && <div style={styles.preview}>
          <div style={styles.metrics}>Stored text: {datasets.find(dataset => dataset.id === datasetId).metadata.character_count.toLocaleString()} characters · {datasets.find(dataset => dataset.id === datasetId).metadata.line_count.toLocaleString()} lines · {datasets.find(dataset => dataset.id === datasetId).metadata.unique_character_count.toLocaleString()} unique characters</div>
          <div style={styles.metrics}>Source: {datasets.find(dataset => dataset.id === datasetId).metadata.provenance} · License: {datasets.find(dataset => dataset.id === datasetId).metadata.license_note}</div>
          <pre style={styles.output}>{datasets.find(dataset => dataset.id === datasetId).metadata.preview}</pre>
        </div>}
      </div>
      <div>
        <h3 style={styles.subheading}>Tiny Transformer settings</h3>
        <div style={styles.grid}>{field('context_length', 'Context', 8, 256)}{field('hidden_size', 'Hidden width', 8, 128)}
          {field('num_layers', 'Layers', 1, 4)}{field('num_heads', 'Attention heads', 1, 8)}
          {field('batch_size', 'Batch', 1, 8)}{field('max_steps', 'Steps', 1, 2000)}{field('checkpoint_interval', 'Checkpoint every N steps', 1, 2000)}{field('seed', 'Random seed', 0, 2147483647)}
          {field('memory_budget_mib', 'Memory budget MiB', 16, 1024)}{field('reserve_memory_mib', 'System reserve MiB', 256, 3072)}</div>
        <label style={styles.label}>Optimizer<select value={config.optimizer} onChange={e => setConfig({ ...config, optimizer: e.target.value })} style={styles.input}>
          <option value="adamw">AdamW</option><option value="adam">Adam</option><option value="sgd">SGD</option>
        </select></label>
        <button disabled={!datasetId || busy} onClick={start} style={styles.button}>Start training</button>
      </div>
    </div>
    <h3 style={styles.subheading}>Training jobs</h3>
    {jobs.length === 0 ? <p style={styles.sub}>No experiments yet. Job metrics and resource readings will appear here after a run starts.</p> : jobs.map(job => {
      const m = job.metrics || {}
      const rows = Array.isArray(m.checkpoints) ? m.checkpoints : []
      return <article key={job.id} style={styles.card}>
        <div style={styles.jobTitle}><strong>{job.id.slice(0, 8)}</strong><span>{m.state || job.status}</span></div>
        <div style={styles.metrics}>Epoch {m.epoch ?? 0} · step {m.step ?? 0} · train loss {m.training_loss ?? 'not measured'} · validation loss {m.validation_loss ?? 'not measured'} · observed RSS {m.observed_rss_bytes ? `${(m.observed_rss_bytes / 1048576).toFixed(1)} MiB` : 'not measured'}</div>
        <div style={styles.metrics}>Checkpoints: {rows.length ? rows.map(path => path.split(/[\\/]/).at(-1)).join(', ') : 'none yet'} · Parameters: {m.parameter_count ?? job.config?.parameter_count ?? 'not measured'}</div>
        <LossChart points={job.loss_history} />
        {['QUEUED', 'PREPARING', 'TRAINING', 'VALIDATING', 'CHECKPOINTING'].includes(m.state || job.status) && <button onClick={() => cancel(job.id)} style={styles.cancel}>Cancel</button>}
        {['CANCELLED', 'FAILED', 'INTERRUPTED', 'QUEUED', 'PREPARING', 'TRAINING'].includes(m.state || job.status) && rows.length > 0 && <button onClick={() => start(job)} style={styles.button}>Resume from latest checkpoint</button>}
        {(m.state || job.status) === 'COMPLETED' && <div style={styles.modelControls}>
          <input aria-label="Registered model name" value={modelName} onChange={e => setModelName(e.target.value)} style={styles.input} />
          {!models.some(model => job.id === model.training_job_id) && <button onClick={() => register(job.id)} style={styles.button}>Register checkpoint</button>}
        </div>}
      </article>
    })}
    <h3 style={styles.subheading}>Model registry and evaluation</h3>
    {models.length === 0 ? <p style={styles.sub}>No registered checkpoints yet. Register a completed run to evaluate or select it for experimental generation.</p> : models.map(model => <article key={model.id} style={styles.card}>
      <div style={styles.jobTitle}><strong>{model.name}</strong><span>{selection?.active_model_id === model.id ? 'Selected for experimental inference' : model.training_status}</span></div>
      <div style={styles.metrics}>{model.architecture} · {model.origin} · {model.compatibility_status}</div>
      <div style={styles.metrics}>Evaluations: {Object.keys(model.evaluation_results || {}).length ? Object.entries(model.evaluation_results).map(([dataset, result]) => `${dataset.slice(0, 8)}: CE ${Number(result.next_token_cross_entropy).toFixed(4)} (${result.tokens_measured} tokens)`).join(' · ') : 'none measured'}</div>
      <div style={styles.modelControls}>
        <button onClick={() => selectModel(model.id)} style={styles.button}>Select experimental model</button>
        <label style={styles.label}>Evaluation dataset<select value={evaluationDatasetId} onChange={e => setEvaluationDatasetId(e.target.value)} style={styles.input}>
          <option value="">Choose a dataset</option>{datasets.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select></label>
        <button disabled={!evaluationDatasetId} onClick={() => evaluate(model.id)} style={styles.button}>Measure loss</button>
      </div>
    </article>)}
    {selection?.previous_model_id && <button onClick={rollbackModel} style={styles.cancel}>Rollback experimental selection</button>}
    <form onSubmit={generate} style={styles.form}>
      <h3 style={styles.subheading}>Experimental generation playground</h3>
      <textarea value={prompt} onChange={e => setPrompt(e.target.value)} maxLength={4000} placeholder="Enter a prompt supported by this model's character vocabulary" style={styles.input} />
      <div style={styles.modelControls}>
        <label style={styles.label}>New tokens (1–256)<input type="number" min="1" max="256" value={generationTokens} onChange={e => setGenerationTokens(Number(e.target.value))} style={styles.input} /></label>
        <label style={styles.label}>Temperature (0.05–2)<input type="number" min="0.05" max="2" step="0.05" value={temperature} onChange={e => setTemperature(Number(e.target.value))} style={styles.input} /></label>
        <label style={styles.label}>Top-k (blank disables)<input type="number" min="1" max="64" value={topK} onChange={e => setTopK(e.target.value)} style={styles.input} /></label>
      </div>
      <button disabled={!selection?.active_model_id || !prompt} style={styles.button}>Generate text</button>
      {generated && <pre style={styles.output}>{generated}</pre>}
    </form>
  </section>
}

const styles = {
  panel: { height: '100%', overflow: 'auto', padding: 24, color: '#e2e8f0', background: 'rgba(4,8,20,.8)', border: '1px solid #1e293b', borderRadius: 12, fontFamily: 'Inter, Segoe UI, sans-serif' },
  heading: { color: '#67e8f9', margin: '0 0 8px', fontSize: 20 }, tag: { color: '#94a3b8', fontSize: 11, marginLeft: 8, fontWeight: 400 },
  sub: { color: '#94a3b8', fontSize: 12, lineHeight: 1.6 }, subheading: { color: '#cbd5e1', fontSize: 14, margin: '20px 0 10px' },
  columns: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 24 }, form: { display: 'grid', gap: 8 },
  label: { display: 'grid', gap: 6, color: '#94a3b8', fontSize: 11, margin: '12px 0' }, input: { background: '#0b1220', color: '#e2e8f0', border: '1px solid #334155', borderRadius: 6, padding: 8, minWidth: 0 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(2,minmax(100px,1fr))', gap: '0 12px' }, button: { marginTop: 10, padding: '10px 14px', color: '#04121a', background: '#06b6d4', border: 0, borderRadius: 6, fontWeight: 700, cursor: 'pointer' },
  notice: { padding: 10, margin: '12px 0', border: '1px solid #155e75', color: '#a5f3fc', borderRadius: 6, fontSize: 12 }, card: { padding: 12, margin: '8px 0', border: '1px solid #1e293b', borderRadius: 8 },
  jobTitle: { display: 'flex', justifyContent: 'space-between', color: '#67e8f9', textTransform: 'uppercase', fontSize: 12 }, metrics: { color: '#94a3b8', fontSize: 11, marginTop: 7, overflowWrap: 'anywhere' }, cancel: { marginTop: 10, color: '#fca5a5', background: 'transparent', border: '1px solid #7f1d1d', borderRadius: 5, padding: '5px 10px', cursor: 'pointer' }, modelControls: { display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'end' }, output: { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', padding: 12, color: '#a5f3fc', background: '#0b1220', borderRadius: 6 }, chartWrap: { marginTop: 12 }, chart: { width: '100%', maxHeight: 180 }, preview: { marginTop: 10, padding: 10, border: '1px solid #1e293b', borderRadius: 6 }
}
