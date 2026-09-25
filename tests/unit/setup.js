// Test setup file
import '@testing-library/jest-dom'

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

// Mock window.speechSynthesis
Object.defineProperty(window, 'speechSynthesis', {
  writable: true,
  value: {
    speak: () => {},
    cancel: () => {},
    pause: () => {},
    resume: () => {},
    getVoices: () => []
  }
})

// Mock navigator.mediaDevices
Object.defineProperty(navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: () => Promise.resolve({
      getTracks: () => [{ stop: () => {} }]
    }),
    getDisplayMedia: () => Promise.resolve({
      getTracks: () => [{ stop: () => {} }]
    })
  }
})

// Mock clipboard
Object.defineProperty(navigator, 'clipboard', {
  writable: true,
  value: {
    writeText: () => Promise.resolve()
  }
})

// Mock crypto.randomUUID
Object.defineProperty(crypto, 'randomUUID', {
  writable: true,
  value: () => 'test-uuid-' + Math.random().toString(36).substr(2, 9)
})

// Mock DataTransfer for file uploads
class MockDataTransfer {
  items = []
  addItem(file) { this.items.push(file) }
  get files() { return this.items }
}
window.DataTransfer = MockDataTransfer
