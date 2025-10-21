// lib/withRefresh.ts
// Token refresh utility for handling 401 errors

import { authApi } from './api';
import { useAuth } from '../store/auth';

export class AuthError extends Error {
  constructor(message: string, public code: string) {
    super(message);
    this.name = 'AuthError';
  }
}

/**
 * Wrapper for API calls that automatically handles token refresh on 401
 * @param fn Function that makes an API call
 * @returns Promise with the API response
 */
export async function withRefresh<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error: any) {
    // Check if it's a 401 unauthorized error
    if (error.status === 401 || error.message === 'Unauthorized') {
      try {
        // Attempt to refresh the token
        const refreshResponse = await authApi.refresh();
        
        // Update the token in the store
        const { setToken } = useAuth.getState();
        setToken(refreshResponse.access_token);
        
        // Dispatch custom event for other components to listen
        window.dispatchEvent(new CustomEvent('auth:token-refreshed', { 
          detail: refreshResponse.access_token 
        }));
        
        // Retry the original request
        return await fn();
        
      } catch (refreshError: any) {
        // Refresh failed, user needs to re-authenticate
        const { logout } = useAuth.getState();
        logout();
        
        // Dispatch logout event
        window.dispatchEvent(new CustomEvent('auth:logout-required'));
        
        throw new AuthError('Session expired. Please log in again.', 'REAUTH_REQUIRED');
      }
    }
    
    // Re-throw non-401 errors
    throw error;
  }
}

/**
 * Hook for components that need to handle auth state changes
 */
export function useAuthEvents() {
  const { setToken, logout } = useAuth();
  
  React.useEffect(() => {
    const handleTokenRefresh = (event: CustomEvent) => {
      setToken(event.detail);
    };
    
    const handleLogoutRequired = () => {
      logout();
      // Redirect to login page
      window.location.href = '/login';
    };
    
    window.addEventListener('auth:token-refreshed', handleTokenRefresh as EventListener);
    window.addEventListener('auth:logout-required', handleLogoutRequired);
    
    return () => {
      window.removeEventListener('auth:token-refreshed', handleTokenRefresh as EventListener);
      window.removeEventListener('auth:logout-required', handleLogoutRequired);
    };
  }, [setToken, logout]);
}

/**
 * Higher-order function to wrap API calls with refresh logic
 */
export function createApiWithRefresh<T extends any[], R>(
  apiFunction: (...args: T) => Promise<R>
) {
  return (...args: T): Promise<R> => {
    return withRefresh(() => apiFunction(...args));
  };
}

// Import React for the hook
import React from 'react';
