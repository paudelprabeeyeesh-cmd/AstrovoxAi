import { useState, useEffect, useCallback } from 'react'
import { supabase } from './supabase'

export default function SettingsPanel({ session, onModelChange }) {
  const [settings, setSettings] = useState({
    theme: 'dark',
    ai_preferences: {
      defaultModel: 'gpt-4',
      temperature: 0.7,
      maxTokens: 2000,
      voiceEnabled: true,
      memoryEnabled: true
    },
    notifications_enabled: true
  })

  const MODELS = [
    { id: 'gpt-4', name: 'GPT-4', provider: 'OpenAI' },
    { id: 'gpt-4o-mini', name: 'GPT-4o Mini', provider: 'OpenAI' },
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'OpenAI' },
    { id: 'claude-3-5-sonnet', name: 'Claude 3.5 Sonnet', provider: 'Anthropic' },
    { id: 'claude-3-opus', name: 'Claude 3 Opus', provider: 'Anthropic' },
    { id: 'claude-3-haiku', name: 'Claude 3 Haiku', provider: 'Anthropic' },
    { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', provider: 'Google' },
    { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', provider: 'Google' },
    { id: 'gemini-1.0-pro', name: 'Gemini 1.0 Pro', provider: 'Google' },
    { id: 'llama3', name: 'Llama 3 (Local)', provider: 'Ollama' },
    { id: 'llama3.1', name: 'Llama 3.1 (Local)', provider: 'Ollama' },
    { id: 'mistral', name: 'Mistral (Local)', provider: 'Ollama' },
    { id: 'mixtral', name: 'Mixtral (Local)', provider: 'Ollama' },
    { id: 'codellama', name: 'Code Llama (Local)', provider: 'Ollama' },
    { id: 'phi3', name: 'Phi-3 (Local)', provider: 'Ollama' },
    { id: 'gemma2', name: 'Gemma 2 (Local)', provider: 'Ollama' },
  ]

  const providers = [...new Set(MODELS.map(m => m.provider))]
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (session) {
      loadSettings()
    }
  }, [session, loadSettings])

  const loadSettings = useCallback(async () => {
    try {
      setLoading(true)
      const { data, error: fetchError } = await supabase
        .from('user_settings')
        .select('*')
        .eq('user_id', session.user.id)
        .single()

      if (fetchError && fetchError.code !== 'PGRST116') throw fetchError
      
      if (data) {
        setSettings(data)
      }
      setError(null)
    } catch (err) {
      setError(`Failed to load settings: ${err.message}`)
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [session.user.id])

  async function handleSaveSettings() {
    try {
      setLoading(true)
      const { error: upsertError } = await supabase
        .from('user_settings')
        .upsert({
          user_id: session.user.id,
          ...settings
        })

      if (upsertError) throw upsertError
      
      setSuccess(true)
      setError(null)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError(`Failed to save settings: ${err.message}`)
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleAIPreferenceChange = (key, value) => {
    setSettings(prev => ({
      ...prev,
      ai_preferences: {
        ...prev.ai_preferences,
        [key]: value
      }
    }))
    if (key === 'defaultModel' && onModelChange) onModelChange(value)
  }

  return (
    <div style={{
      backgroundColor: '#040814',
      border: '1px solid #1e293b',
      borderRadius: '12px',
      padding: '16px',
      fontFamily: 'monospace',
      maxHeight: '400px',
      overflowY: 'auto'
    }}>
      <h3 style={{
        margin: '0 0 16px 0',
        fontSize: '12px',
        color: '#94a3b8',
        letterSpacing: '1px',
        textTransform: 'uppercase'
      }}>
        ⚙️ SYSTEM SETTINGS
      </h3>

      {error && (
        <div style={{
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid #ef4444',
          borderRadius: '6px',
          padding: '8px',
          fontSize: '10px',
          color: '#f87171',
          marginBottom: '12px'
        }}>
          ⚠️ {error}
        </div>
      )}

      {success && (
        <div style={{
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          border: '1px solid #22c55e',
          borderRadius: '6px',
          padding: '8px',
          fontSize: '10px',
          color: '#22c55e',
          marginBottom: '12px'
        }}>
          ✅ Settings saved successfully
        </div>
      )}

      {/* Theme Setting */}
      <div style={{ marginBottom: '12px' }}>
        <label style={{
          display: 'block',
          fontSize: '10px',
          color: '#94a3b8',
          marginBottom: '6px',
          letterSpacing: '0.5px'
        }}>
          THEME
        </label>
        <select
          value={settings.theme}
          onChange={(e) => setSettings(prev => ({ ...prev, theme: e.target.value }))}
          style={{
            width: '100%',
            padding: '8px',
            borderRadius: '6px',
            backgroundColor: '#050a18',
            border: '1px solid #1e293b',
            color: '#67e8f9',
            fontFamily: 'monospace',
            fontSize: '11px'
          }}
        >
          <option value="dark">Dark</option>
          <option value="light">Light</option>
          <option value="auto">Auto</option>
        </select>
      </div>

      {/* AI Model Setting */}
      <div style={{ marginBottom: '12px' }}>
        <label style={{
          display: 'block',
          fontSize: '10px',
          color: '#94a3b8',
          marginBottom: '6px',
          letterSpacing: '0.5px'
        }}>
          DEFAULT AI MODEL: {settings.ai_preferences.defaultModel}
        </label>
        <select
          value={settings.ai_preferences.defaultModel}
          onChange={(e) => handleAIPreferenceChange('defaultModel', e.target.value)}
          style={{
            width: '100%',
            padding: '8px',
            borderRadius: '6px',
            backgroundColor: '#050a18',
            border: '1px solid #1e293b',
            color: '#67e8f9',
            fontFamily: 'monospace',
            fontSize: '11px'
          }}
        >
          {providers.map(provider => (
            <optgroup key={provider} label={provider}>
              {MODELS.filter(m => m.provider === provider).map(m => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      {/* Temperature Setting */}
      <div style={{ marginBottom: '12px' }}>
        <label style={{
          display: 'block',
          fontSize: '10px',
          color: '#94a3b8',
          marginBottom: '6px',
          letterSpacing: '0.5px'
        }}>
          TEMPERATURE: {settings.ai_preferences.temperature.toFixed(2)}
        </label>
        <input
          type="range"
          min="0"
          max="2"
          step="0.1"
          value={settings.ai_preferences.temperature}
          onChange={(e) => handleAIPreferenceChange('temperature', parseFloat(e.target.value))}
          style={{
            width: '100%',
            cursor: 'pointer'
          }}
        />
        <div style={{
          fontSize: '9px',
          color: '#64748b',
          marginTop: '4px'
        }}>
          Lower = more focused, Higher = more creative
        </div>
      </div>

      {/* Max Tokens Setting */}
      <div style={{ marginBottom: '12px' }}>
        <label style={{
          display: 'block',
          fontSize: '10px',
          color: '#94a3b8',
          marginBottom: '6px',
          letterSpacing: '0.5px'
        }}>
          MAX TOKENS
        </label>
        <input
          type="number"
          min="100"
          max="4000"
          value={settings.ai_preferences.maxTokens}
          onChange={(e) => handleAIPreferenceChange('maxTokens', parseInt(e.target.value))}
          style={{
            width: '100%',
            padding: '8px',
            borderRadius: '6px',
            backgroundColor: '#050a18',
            border: '1px solid #1e293b',
            color: '#67e8f9',
            fontFamily: 'monospace',
            fontSize: '11px',
            boxSizing: 'border-box'
          }}
        />
      </div>

      {/* Toggles */}
      <div style={{ marginBottom: '12px' }}>
        <label style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '11px',
          color: '#cbd5e1',
          cursor: 'pointer'
        }}>
          <input
            type="checkbox"
            checked={settings.ai_preferences.voiceEnabled}
            onChange={(e) => handleAIPreferenceChange('voiceEnabled', e.target.checked)}
            style={{ cursor: 'pointer' }}
          />
          Enable Voice Input
        </label>
      </div>

      <div style={{ marginBottom: '16px' }}>
        <label style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '11px',
          color: '#cbd5e1',
          cursor: 'pointer'
        }}>
          <input
            type="checkbox"
            checked={settings.ai_preferences.memoryEnabled}
            onChange={(e) => handleAIPreferenceChange('memoryEnabled', e.target.checked)}
            style={{ cursor: 'pointer' }}
          />
          Enable Memory System
        </label>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSaveSettings}
        disabled={loading}
        style={{
          width: '100%',
          padding: '10px',
          backgroundColor: '#06b6d4',
          color: '#02040a',
          border: 'none',
          borderRadius: '8px',
          cursor: 'pointer',
          fontWeight: '600',
          fontSize: '11px',
          letterSpacing: '0.5px',
          opacity: loading ? 0.5 : 1,
          transition: 'all 0.2s'
        }}
        onMouseEnter={(e) => {
          if (!loading) {
            e.target.style.transform = 'scale(1.02)'
            e.target.style.boxShadow = '0 0 15px rgba(6,182,212,0.4)'
          }
        }}
        onMouseLeave={(e) => {
          e.target.style.transform = 'scale(1)'
          e.target.style.boxShadow = 'none'
        }}
      >
        {loading ? 'SAVING...' : 'SAVE SETTINGS'}
      </button>
    </div>
  )
}
