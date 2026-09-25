import ReactDOM from 'react-dom/client'
import App from './app.jsx'
import { initializeMathAndDiagrams } from './utils/mathAndDiagrams'

initializeMathAndDiagrams()

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((err) => {
      console.warn('Service worker registration failed:', err)
    })
  })
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <App />,
)
