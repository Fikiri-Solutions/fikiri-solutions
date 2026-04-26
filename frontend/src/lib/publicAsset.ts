/**
 * Resolves a URL for files in Vite’s `public/` directory. Use for every
 * `img`/`src`/`source srcSet` that points at static public assets so builds
 * work when the app is deployed under a non-root `base` path.
 */
export function publicAsset(path: string): string {
  const relative = path.replace(/^\/+/, '')
  return `${import.meta.env.BASE_URL}${relative}`
}
