import { useEffect } from 'react'

const LIBS_LOADED = { katex: false, mermaid: false }

export function useMathAndDiagrams() {
  useEffect(() => {
    let cancelled = false

    async function loadKatex() {
      if (typeof window !== 'undefined' && !window.katex && !LIBS_LOADED.katex) {
        try {
          const katex = await import('katex')
          window.katex = katex.default || katex
          LIBS_LOADED.katex = true
        } catch (err) {
          console.warn('KaTeX load failed:', err)
        }
      }
    }

    async function loadMermaid() {
      if (typeof window !== 'undefined' && !window.mermaid && !LIBS_LOADED.mermaid) {
        try {
          const mermaid = await import('mermaid')
          window.mermaid = mermaid.default || mermaid
          if (window.mermaid && !window.mermaid.initialized) {
            window.mermaid.initialize({
              startOnLoad: false,
              theme: 'dark',
              securityLevel: 'loose'
            })
            window.mermaid.initialized = true
          }
          LIBS_LOADED.mermaid = true
        } catch (err) {
          console.warn('Mermaid load failed:', err)
        }
      }
    }

    loadKatex()
    loadMermaid()

    return () => { cancelled = true }
  }, [])
}

export function initializeMathAndDiagrams() {
  return {
    katexLoaded: LIBS_LOADED.katex,
    mermaidLoaded: LIBS_LOADED.mermaid
  }
}
