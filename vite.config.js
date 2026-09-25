import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import monacoEditorPlugin from '@monaco-editor/plugin'

export default defineConfig({
  plugins: [
    react(),
    monacoEditorPlugin({
      viteConfig: {
        build: {
          rollupOptions: {
            output: {
              manualChunks: {
                'monaco-editor': ['monaco-editor']
              }
            }
          }
        }
      }
    })
  ],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          'monaco-editor': ['monaco-editor']
        }
      }
    }
  },
  optimizeDeps: {
    include: ['monaco-editor']
  }
})
