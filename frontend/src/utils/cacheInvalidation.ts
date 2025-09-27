/**
 * Cache Invalidation Utilities
 * Comprehensive cache invalidation strategy for production deployments
 * 
 * This utility ensures that users always get the latest version of the app
 * by implementing multiple cache invalidation strategies:
 * 
 * 1. Version-based cache invalidation
 * 2. Timestamp-based cache busting
 * 3. Browser cache clearing
 * 4. Service Worker cache invalidation
 * 5. API request cache headers
 */

import { config } from '../config'

const CURRENT_APP_VERSION = config.version
const CURRENT_BUILD_TIMESTAMP = config.buildTimestamp
const CURRENT_CACHE_VERSION = config.cacheVersion

/**
 * Comprehensive Cache Invalidation Manager
 * Handles all aspects of cache invalidation for production deployments
 */
export class CacheInvalidationManager {
  private static instance: CacheInvalidationManager
  private constructor() {}

  public static getInstance(): CacheInvalidationManager {
    if (!CacheInvalidationManager.instance) {
      CacheInvalidationManager.instance = new CacheInvalidationManager()
    }
    return CacheInvalidationManager.instance
  }

  /**
   * Initialize cache invalidation on app start
   * Checks version and clears caches if needed
   */
  public initialize(): void {
    const storedCacheVersion = localStorage.getItem('appCacheVersion')
    const storedBuildTimestamp = localStorage.getItem('appBuildTimestamp')

    if (storedCacheVersion !== CURRENT_CACHE_VERSION || storedBuildTimestamp !== CURRENT_BUILD_TIMESTAMP) {
      console.log('🚨 Cache mismatch detected! Clearing all client-side caches.')
      // Delay cache clearing to allow React app to render first
      setTimeout(() => {
        this.clearAllCaches()
        localStorage.setItem('appCacheVersion', CURRENT_CACHE_VERSION)
        localStorage.setItem('appBuildTimestamp', CURRENT_BUILD_TIMESTAMP)
        console.log(`✅ New cache version stored: ${CURRENT_CACHE_VERSION} (${CURRENT_BUILD_TIMESTAMP})`)
      }, 1000) // Wait 1 second for React to render
    } else {
      console.log('✅ Client-side cache is up to date.')
    }
  }

  /**
   * Clear all possible client-side caches
   */
  private clearAllCaches(): void {
    // Preserve theme preference before clearing
    const themePreference = localStorage.getItem('fikiri-theme')
    
    // Clear localStorage
    localStorage.clear()
    console.log('  - localStorage cleared.')

    // Restore theme preference
    if (themePreference) {
      localStorage.setItem('fikiri-theme', themePreference)
      console.log('  - Theme preference restored.')
    }

    // Clear sessionStorage
    sessionStorage.clear()
    console.log('  - sessionStorage cleared.')

    // Clear IndexedDB (if used)
    if (window.indexedDB) {
      indexedDB.databases().then(dbs => {
        dbs.forEach(db => {
          if (db.name) {
            indexedDB.deleteDatabase(db.name)
            console.log(`  - IndexedDB database '${db.name}' deleted.`)
          }
        })
      }).catch(error => console.error('Error clearing IndexedDB:', error))
    }

    // Clear Service Worker caches
    if ('caches' in window) {
      caches.keys().then(cacheNames => {
        cacheNames.forEach(cacheName => {
          caches.delete(cacheName)
          console.log(`  - Service Worker cache '${cacheName}' deleted.`)
        })
      }).catch(error => console.error('Error clearing Service Worker caches:', error))
    }

    // Don't reload immediately - let the app render first
    console.log('  - Cache cleared. App will continue loading.')
  }

  /**
   * Get cache invalidation headers for API requests
   */
  public getCacheHeaders(): Record<string, string> {
    return {
      'X-Deployment-Timestamp': CURRENT_BUILD_TIMESTAMP,
      'X-Cache-Version': CURRENT_CACHE_VERSION,
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
    }
  }

  /**
   * Add cache buster parameters to URLs
   */
  public addCacheBuster(url: string): string {
    const separator = url.includes('?') ? '&' : '?'
    return `${url}${separator}v=${CURRENT_CACHE_VERSION}&t=${Date.now()}`
  }

  /**
   * Force reload with cache bypass
   */
  public forceReload(): void {
    window.location.reload()
  }
}

/**
 * Initialize cache invalidation on app start
 * This should be called before the app renders
 */
export const initializeCacheInvalidation = (): void => {
  const cacheManager = CacheInvalidationManager.getInstance()
  cacheManager.initialize()
}

/**
 * Hook for React components to use cache invalidation
 */
export const useCacheInvalidation = () => {
  const cacheManager = CacheInvalidationManager.getInstance()
  
  return {
    addCacheBuster: cacheManager.addCacheBuster.bind(cacheManager),
    forceReload: cacheManager.forceReload.bind(cacheManager),
    getCacheHeaders: cacheManager.getCacheHeaders.bind(cacheManager)
  }
}
