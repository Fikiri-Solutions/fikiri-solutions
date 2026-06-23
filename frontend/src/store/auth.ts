// store/auth.ts
// Authentication state management with Zustand

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  onboarding_completed: boolean;
  onboarding_step: number;
}

export interface AuthState {
  // State
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setRefreshToken: (token: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  login: (user: User, token: string, refreshToken?: string | null) => void;
  logout: () => void;
  clearError: () => void;
}

const clearLegacyAuthStorage = () => {
  if (typeof window === 'undefined') {
    return;
  }

  localStorage.removeItem('fikiri-token');
  localStorage.removeItem('fikiri-user');
  localStorage.removeItem('fikiri-user-id');
  localStorage.removeItem('fikiri-remember-password');
};

// Create auth store with persistence for user data only
export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      // Initial state
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      
      // Actions
      setUser: (user) => set({ 
        user, 
        isAuthenticated: !!user 
      }),
      
      setToken: (accessToken) => set({ accessToken }),
      setRefreshToken: (refreshToken) => set({ refreshToken }),
      
      setLoading: (isLoading) => set({ isLoading }),
      
      setError: (error) => set({ error }),
      
      login: (user, accessToken, refreshToken = null) => set({
        user,
        accessToken,
        refreshToken,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      }),
      
      logout: () => {
        clearLegacyAuthStorage();
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      },
      
      clearError: () => set({ error: null }),
    }),
    {
      name: 'fikiri-auth',
      // Only persist user data, not tokens (security)
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// Selectors for common use cases
export const useUser = () => useAuth((state) => state.user);
export const useIsAuthenticated = () => useAuth((state) => state.isAuthenticated);
export const useAccessToken = () => useAuth((state) => state.accessToken);
export const useRefreshToken = () => useAuth((state) => state.refreshToken);
export const useAuthLoading = () => useAuth((state) => state.isLoading);
export const useAuthError = () => useAuth((state) => state.error);

// Auth actions
export const useAuthActions = () => useAuth((state) => ({
  setUser: state.setUser,
  setToken: state.setToken,
  setRefreshToken: state.setRefreshToken,
  setLoading: state.setLoading,
  setError: state.setError,
  login: state.login,
  logout: state.logout,
  clearError: state.clearError,
}));
