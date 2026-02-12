// lib/api.ts
// Shared fetch helper with cookie credentials for Fikiri Solutions

import { config } from '../config'

const API_BASE_URL = config.apiUrl;

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  error_code?: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public errorCode?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function api<T = any>(
  url: string, 
  init: RequestInit = {}
): Promise<T> {
  const fullUrl = `${API_BASE_URL}${url}`;
  
  const config: RequestInit = {
    credentials: 'include', // Critical for cookie-based auth
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
    ...init,
  };

  // Handle request body
  if (init.body && typeof init.body === 'object' && !(init.body instanceof FormData)) {
    config.body = JSON.stringify(init.body);
  }

  try {
    const response = await fetch(fullUrl, config);
    
    // Handle 401 unauthorized
    if (response.status === 401) {
      throw new ApiError('Unauthorized', 401, 'UNAUTHORIZED');
    }
    
    // Handle other errors
    if (!response.ok) {
      const errorText = await response.text();
      let errorData;
      try {
        errorData = JSON.parse(errorText);
      } catch {
        errorData = { error: errorText };
      }
      
      throw new ApiError(
        errorData.error || errorData.message || 'Request failed',
        response.status,
        errorData.error_code
      );
    }
    
    const data: ApiResponse<T> = await response.json();
    
    if (!data.success) {
      throw new ApiError(
        data.error || data.message || 'Request failed',
        response.status,
        data.error_code
      );
    }
    
    return data.data || data as T;
    
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    
    // Network or other errors - provide user-friendly messages
    let errorMessage = 'Network error';
    if (error instanceof Error) {
      if (error.message.includes('Failed to fetch') || error.message.includes('ERR_CONNECTION_REFUSED')) {
        errorMessage = 'Unable to connect to server. Please check your connection or try again later.';
      } else {
        errorMessage = error.message;
      }
    }
    
    throw new ApiError(
      errorMessage,
      0,
      'NETWORK_ERROR'
    );
  }
}

// Convenience methods
export const apiGet = <T = any>(url: string, init?: RequestInit) =>
  api<T>(url, { ...init, method: 'GET' });

export const apiPost = <T = any>(url: string, body?: any, init?: RequestInit) =>
  api<T>(url, { ...init, method: 'POST', body });

export const apiPut = <T = any>(url: string, body?: any, init?: RequestInit) =>
  api<T>(url, { ...init, method: 'PUT', body });

export const apiPatch = <T = any>(url: string, body?: any, init?: RequestInit) =>
  api<T>(url, { ...init, method: 'PATCH', body });

export const apiDelete = <T = any>(url: string, init?: RequestInit) =>
  api<T>(url, { ...init, method: 'DELETE' });

// Auth-specific API calls
export const authApi = {
  login: (email: string, password: string) =>
    apiPost<{
      user: {
        id: number;
        email: string;
        name: string;
        role: string;
        onboarding_completed: boolean;
        onboarding_step: number;
      };
      access_token: string;
      expires_in: number;
      token_type: string;
    }>('/auth/login', { email, password }),
    
  signup: (userData: {
    email: string;
    password: string;
    name: string;
    business_name?: string;
    business_email?: string;
    industry?: string;
    team_size?: string;
  }) =>
    apiPost<{
      user: {
        id: number;
        email: string;
        name: string;
        role: string;
        onboarding_completed: boolean;
        onboarding_step: number;
      };
      access_token: string;
      expires_in: number;
      token_type: string;
    }>('/auth/signup', userData),
    
  refresh: () =>
    apiPost<{
      access_token: string;
      expires_in: number;
      token_type: string;
    }>('/auth/refresh'),
    
  whoami: () =>
    apiGet<{
      authenticated: boolean;
      user?: {
        id: number;
        email: string;
        name: string;
        role: string;
        onboarding_completed: boolean;
        onboarding_step: number;
      };
      session_exists: boolean;
      token_valid: boolean;
      cookies: {
        fikiri_session: boolean;
        fikiri_refresh_token: boolean;
      };
      headers: {
        authorization: boolean;
        origin?: string;
        user_agent?: string;
      };
    }>('/auth/whoami'),
    
  logout: () =>
    apiPost('/auth/logout'),
};
