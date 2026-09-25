const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function getToken() {
  const { supabase } = await import('../supabase')
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token
}

async function api(path, options = {}) {
  const token = await getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...(options.headers || {}),
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export async function createPipeline(config = {}) {
  return api('/neural/pipelines', {
    method: 'POST',
    body: JSON.stringify(config),
  })
}

export async function startPipeline(pipelineId) {
  return api(`/neural/pipelines/${pipelineId}/start`, { method: 'POST' })
}

export async function stopPipeline(pipelineId) {
  return api(`/neural/pipelines/${pipelineId}/stop`, { method: 'POST' })
}

export async function getRecentEpochs(count = 20) {
  return api(`/neural/epochs?count=${count}`)
}

export async function thoughtToText(neuralEmbedding, topK = 1) {
  return api('/neural/thought-to-text', {
    method: 'POST',
    body: JSON.stringify({ neural_embedding: neuralEmbedding, top_k: topK }),
  })
}

export async function emotionToUI(valence, arousal, context = {}) {
  return api('/neural/emotion-to-ui', {
    method: 'POST',
    body: JSON.stringify({ valence, arousal, context }),
  })
}

export async function getCurrentEmotion() {
  return api('/neural/emotion')
}

export async function attentionAdapt(focusScore, distractionSignals = [], uiContext = {}) {
  return api('/neural/attention-adapt', {
    method: 'POST',
    body: JSON.stringify({ focus_score: focusScore, distraction_signals: distractionSignals, ui_context: uiContext }),
  })
}

export async function motorImageryCommand(epochData = [], channels = []) {
  return api('/neural/motor-imagery/command', {
    method: 'POST',
    body: JSON.stringify({ epoch_data: epochData, channels }),
  })
}

export async function motorImageryHistory(limit = 50) {
  return api(`/neural/motor-imagery/history?limit=${limit}`)
}

export async function neurofeedbackMetrics() {
  return api('/neural/neurofeedback/metrics')
}

export async function memoryPalaceRegister(palaceId = '', nodes = []) {
  return api('/neural/memory-palace/register', {
    method: 'POST',
    body: JSON.stringify({ palace_id: palaceId, nodes }),
  })
}

export async function memoryPalaceNavigate(palaceId, nodeId) {
  return api('/neural/memory-palace/navigate', {
    method: 'POST',
    body: JSON.stringify({ palace_id: palaceId, node_id: nodeId }),
  })
}

export async function memoryPalaceCurrent() {
  return api('/neural/memory-palace/current')
}

export async function dreamAssist(epochData = [], channels = []) {
  return api('/neural/dream/assist', {
    method: 'POST',
    body: JSON.stringify({ epoch_data: epochData, channels }),
  })
}

export async function dreamHistory(limit = 50) {
  return api(`/neural/dream/history?limit=${limit}`)
}

export async function lucidStart(active = true) {
  return api('/neural/dream/lucid/start', {
    method: 'POST',
    body: JSON.stringify({ active }),
  })
}

export async function lucidTick(epochData = [], channels = []) {
  return api('/neural/dream/lucid/tick', {
    method: 'POST',
    body: JSON.stringify({ epoch_data: epochData, channels }),
  })
}

export async function consciousnessReadout(epochData = [], channels = [], selfReportedClarity = null) {
  return api('/neural/consciousness/readout', {
    method: 'POST',
    body: JSON.stringify({ epoch_data: epochData, channels, self_reported_clarity: selfReportedClarity }),
  })
}

export async function consciousnessHistory(limit = 50) {
  return api(`/neural/consciousness/history?limit=${limit}`)
}

export async function bciConnect(deviceId = 'stub_device', deviceType = 'eeg', sampleRateHz = 250) {
  return api('/neural/bci/connect', {
    method: 'POST',
    body: JSON.stringify({ device_id: deviceId, device_type: deviceType, sample_rate_hz: sampleRateHz }),
  })
}

export async function bciDisconnect(deviceId = 'stub_device') {
  return api(`/neural/bci/disconnect?device_id=${deviceId}`, { method: 'POST' })
}

export async function bciDevices() {
  return api('/neural/bci/devices')
}

export async function signalProcess(signal, pipelineId = '') {
  return api('/neural/signal/process', {
    method: 'POST',
    body: JSON.stringify({ signal, pipeline_id: pipelineId }),
  })
}

export async function signalFilter(signal, pipelineId = '') {
  return api('/neural/signal/filter', {
    method: 'POST',
    body: JSON.stringify({ signal, pipeline_id: pipelineId }),
  })
}

export async function modalityAcquire(modality = 'eeg', channels = [], sampleRateHz = 250) {
  return api('/neural/modality/acquire', {
    method: 'POST',
    body: JSON.stringify({ modality, channels, sample_rate_hz: sampleRateHz }),
  })
}

export async function modalityStatus(modality) {
  return api(`/neural/modality/${modality}/status`)
}

export async function decoderPredict(modelType, inputData = {}) {
  return api('/neural/decoder/predict', {
    method: 'POST',
    body: JSON.stringify({ model_type: modelType, input_data: inputData }),
  })
}

export async function decoderModels() {
  return api('/neural/decoder/models')
}

export async function brainBridgeCommand(command, parameters = {}, confidenceThreshold = 0.7) {
  return api('/neural/bridge/command', {
    method: 'POST',
    body: JSON.stringify({ command, parameters, confidence_threshold: confidenceThreshold }),
  })
}

export async function brainBridgeStatus() {
  return api('/neural/bridge/status')
}
