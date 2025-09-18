/**
 * Cache Invalidation Utilities
 * Comprehensive cache invalidation strategy for production deployments
 */

import { config } from '../config'

/**
 * Cache invalidation strategies
 */
export class CacheInvalidationManager {
  private static instance: CacheInvalidationManager
  private cacheVersion: string
  private buildTimestamp: string

  constructor() {
    this.cacheVersion = config.cacheVersion
    this.buildTimestamp = config.buildTimestamp
  }

  public static getInstance(): CacheInvalidationManager {
    if (!CacheInvalidationManager.instance) {
      CacheInvalidationManager.instance = new CacheInvalidationManager()
    }
    return CacheInvalidationManager.instance
  }

  /**
   * Force cache invalidation by adding version parameters to requests
   */
  public addCacheBuster(url: string): string {
    const separator = url.includes('?') ? '&' : '?'
    return `${url}${separator}_v=${this.cacheVersion}&_t=${Date.now()}`
  }

  /**
   * Clear all browser caches
   */
  public clearBrowserCache(): void {
    try {
      // Clear localStorage
      localStorage.clear()
      
      // Clear sessionStorage
      sessionStorage.clear()
      
      // Clear IndexedDB (if available)
      if ('indexedDB' in window) {
        indexedDB.databases?.().then(databases => {
          databases.forEach(db => {
            if (db.name) {
              indexedDB.deleteDatabase(db.name)
            }
          })
        })
      }
      
      // Clear service worker cache (if available)
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistrations().then(registrations => {
          registrations.forEach(registration => {
            registration.unregister()
          })
        })
      }
    } catch (error) {
      // Cache clearing failed - log silently
    }
  }

  /**
   * Force reload with cache invalidation
   */
  public forceReload(): void {
    // Clear caches first
    this.clearBrowserCache()
    
    // Force reload with cache bypass
    window.location.reload()
  }

  /**
   * Check if cache needs invalidation based on version
   */
  public needsCacheInvalidation(): boolean {
    const storedVersion = localStorage.getItem('app_version')
    return storedVersion !== this.cacheVersion
  }

  /**
   * Update stored version and clear caches if needed
   */
  public invalidateIfNeeded(): void {
    if (this.needsCacheInvalidation()) {
      this.clearBrowserCache()
      localStorage.setItem('app_version', this.cacheVersion)
      localStorage.setItem('build_timestamp', this.buildTimestamp)
    }
  }

  /**
   * Get cache invalidation headers for API requests
   */
  public getCacheHeaders(): Record<string, string> {
    return {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
      'X-Cache-Version': this.cacheVersion,
      'X-Build-Timestamp': this.buildTimestamp
    }
  }
}

/**
 * Initialize cache invalidation on app start
 */
export const initializeCacheInvalidation = (): void => {
  const cacheManager = CacheInvalidationManager.getInstance()
  cacheManager.invalidateIfNeeded()
}

/**
 * Hook for React components to use cache invalidation
 */
export const useCacheInvalidation = () => {
  const cacheManager = CacheInvalidationManager.getInstance()
  
  return {
    addCacheBuster: cacheManager.addCacheBuster.bind(cacheManager),
    clearBrowserCache: cacheManager.clearBrowserCache.bind(cacheManager),
    forceReload: cacheManager.forceReload.bind(cacheManager),
    needsCacheInvalidation: cacheManager.needsCacheInvalidation.bind(cacheManager),
    getCacheHeaders: cacheManager.getCacheHeaders.bind(cacheManager)
  }
}
