import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import { initializeCacheInvalidation } from './utils/cacheInvalidation'

// Initialize cache invalidation before app starts
initializeCacheInvalidation()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

