import { createClient } from './client'

/**
 * In Next.js, Edge middleware refreshes auth cookies. In a Vite SPA, the browser client
 * keeps sessions fresh; call this once at startup (see `main.tsx`).
 */
export function registerSupabaseSessionRefresh(): () => void {
  if (!import.meta.env.VITE_SUPABASE_URL || !import.meta.env.VITE_SUPABASE_ANON_KEY) {
    return () => {}
  }
  const supabase = createClient()
  void supabase.auth.startAutoRefresh()
  return () => {
    void supabase.auth.stopAutoRefresh()
  }
}
