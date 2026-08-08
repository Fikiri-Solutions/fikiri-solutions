/**
 * Minimal Suspense fallback for route-level code splitting.
 * Avoids heavy spinners / motion so public cold loads stay light.
 */
export function RouteLoadingFallback() {
  return (
    <div
      className="min-h-screen flex items-center justify-center bg-white text-gray-600 dark:bg-gray-950 dark:text-gray-400"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <p className="text-sm font-medium tracking-wide">Loading…</p>
    </div>
  )
}
