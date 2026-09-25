import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['tests/integration/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    snapshotFormat: {
      escapeString: false,
      printBasicPrototype: false
    },
    coverage: {
      reporter: ['text', 'json'],
      include: ['src/**/*.{js,jsx,ts,tsx}']
    }
  }
})
