import React, { createContext, useContext, useCallback } from 'react'
import toast, { Toaster } from 'react-hot-toast'

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

export const ToastProvider: React.FC<ToastProviderProps> = ({ children }) => {
  const addToast = useCallback((toastData: Toast) => {
    const { type, title, message, duration = 4000 } = toastData
    
    const toastOptions = {
      duration,
      position: 'top-right' as const,
      style: {
        background: 'var(--bg-primary)',
        color: 'var(--text-primary)',
        border: '1px solid var(--border-primary)',
        borderRadius: '12px',
        boxShadow: 'var(--shadow-lg)',
        padding: '16px',
        fontSize: '14px',
        maxWidth: '400px',
      },
    }

    switch (type) {
      case 'success':
        toast.success(`${title}${message ? `\n${message}` : ''}`, toastOptions)
        break
      case 'error':
        toast.error(`${title}${message ? `\n${message}` : ''}`, toastOptions)
        break
      case 'warning':
        toast(`${title}${message ? `\n${message}` : ''}`, {
          ...toastOptions,
          icon: '⚠️',
        })
        break
      case 'info':
        toast(`${title}${message ? `\n${message}` : ''}`, {
          ...toastOptions,
          icon: 'ℹ️',
        })
        break
    }
  }, [])

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <Toaster 
        toastOptions={{
          className: 'mobile-optimized-toast',
        }}
      />
    </ToastContext.Provider>
  )
}

