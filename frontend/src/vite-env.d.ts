/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  /** Set to "true" at build time to allow Socket.IO (also requires realTimeUpdates in config). */
  readonly VITE_ENABLE_WEBSOCKET?: string
  readonly VITE_SUPABASE_URL?: string
  readonly VITE_SUPABASE_ANON_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
