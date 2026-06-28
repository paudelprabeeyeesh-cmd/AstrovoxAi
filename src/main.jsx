import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './app.jsx'

// Mounts the React application to the DOM
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)