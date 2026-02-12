import React, { createContext, useContext, useCallback, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import toast, { Toaster } from 'react-hot-toast'
import { CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  type: ToastType
  title: string
  message?: string
  duration?: number
}

interface ToastContextType {
  addToast: (toast: Toast) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

interface ToastProviderProps {
  children: React.ReactNode
}

const getToastIcon = (type: ToastType) => {
  const iconClass = "w-5 h-5 flex-shrink-0"
  switch (type) {
    case 'success':
      return <CheckCircle className={`${iconClass} text-green-500`} />
    case 'error':
      return <XCircle className={`${iconClass} text-red-500`} />
    case 'warning':
      return <AlertCircle className={`${iconClass} text-orange-500`} />
    case 'info':
      return <Info className={`${iconClass} text-blue-500`} />
  }
}

const getToastStyles = (type: ToastType) => {
  const baseStyles = {
    borderRadius: '12px',
    padding: '16px',
    fontSize: '14px',
    maxWidth: '420px',
    minWidth: '320px',
    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.2)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
  }

  switch (type) {
    case 'success':
      return {
        ...baseStyles,
        background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.1) 100%)',
        color: '#f0fdf4',
      }
    case 'error':
      return {
        ...baseStyles,
        background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.1) 100%)',
        color: '#fef2f2',
      }
    case 'warning':
      return {
        ...baseStyles,
        background: 'linear-gradient(135deg, rgba(249, 115, 22, 0.15) 0%, rgba(234, 88, 12, 0.1) 100%)',
        color: '#fff7ed',
      }
    case 'info':
      return {
        ...baseStyles,
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(37, 99, 235, 0.1) 100%)',
        color: '#eff6ff',
      }
  }
}

const getToastPosition = (pathname: string): { position: 'top-right' | 'top-left' | 'top-center', containerStyle: React.CSSProperties } => {
  // Pages with forms/centered content - use top-right to avoid overlap
  if (pathname === '/login' || pathname === '/signup' || pathname.startsWith('/onboarding')) {
    return {
      position: 'top-right',
      containerStyle: {
        top: '80px',
        right: '24px',
        left: 'auto',
      }
    }
  }
  
  // Dashboard and app pages - top-right, below header
  if (pathname.startsWith('/dashboard') || pathname.startsWith('/inbox') || 
      pathname.startsWith('/crm') || pathname.startsWith('/services') ||
      pathname.startsWith('/integrations') || pathname.startsWith('/automations') ||
      pathname.startsWith('/ai')) {
    return {
      position: 'top-right',
      containerStyle: {
        top: '80px',
        right: '24px',
        left: 'auto',
      }
    }
  }
  
  // Landing and pricing pages - top-right, avoid hero section
  if (pathname === '/' || pathname === '/pricing' || pathname.startsWith('/industries')) {
    return {
      position: 'top-right',
      containerStyle: {
        top: '100px',
        right: '24px',
        left: 'auto',
      }
    }
  }
  
  // Default: top-right for all other pages
  return {
    position: 'top-right',
    containerStyle: {
      top: '80px',
      right: '24px',
      left: 'auto',
    }
  }
}

export const ToastProvider: React.FC<ToastProviderProps> = ({ children }) => {
  const location = useLocation()
  const lastToastRef = useRef<{ key: string; timestamp: number } | null>(null)
  const DEBOUNCE_MS = 500

  const { position, containerStyle } = getToastPosition(location.pathname)

  const addToast = useCallback((toastData: Toast) => {
    const { type, title, message, duration = 4000 } = toastData
    
    const toastKey = `${type}-${title}-${message || ''}`
    const now = Date.now()
    
    if (lastToastRef.current?.key === toastKey && 
        now - lastToastRef.current.timestamp < DEBOUNCE_MS) {
      return
    }
    
    lastToastRef.current = { key: toastKey, timestamp: now }
    
    const customToast = (
      <div style={getToastStyles(type)} className="flex items-start gap-3">
        {getToastIcon(type)}
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-base mb-1">{title}</div>
          {message && <div className="text-sm opacity-90 leading-relaxed">{message}</div>}
        </div>
      </div>
    )

    toast(customToast, {
      duration,
      position,
      style: {
        background: 'transparent',
        boxShadow: 'none',
        padding: 0,
      },
    })
  }, [position])

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <Toaster 
        position={position}
        containerStyle={containerStyle}
        toastOptions={{
          className: '',
          style: {
            background: 'transparent',
            boxShadow: 'none',
            padding: 0,
          },
        }}
      />
    </ToastContext.Provider>
  )
}

