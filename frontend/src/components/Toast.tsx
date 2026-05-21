import React, { createContext, useContext, useCallback, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import toast, { Toaster } from 'react-hot-toast'
import { CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastUndoAction {
  label: string
  onClick: () => void
}

export interface Toast {
  type: ToastType
  title: string
  message?: string
  duration?: number
  /** Optional undo control (e.g. Mark done in Organize) */
  undo?: ToastUndoAction
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
    width: '100%',
    maxWidth: 'min(420px, calc(100vw - 2rem))',
    minWidth: 0,
    marginLeft: 'auto',
    marginRight: 'auto',
    boxSizing: 'border-box' as const,
    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.2)',
    border: '1px solid rgba(0, 0, 0, 0.08)',
  }

  switch (type) {
    case 'success':
      return {
        ...baseStyles,
        background: '#059669',
        color: '#ffffff',
      }
    case 'error':
      return {
        ...baseStyles,
        background: '#dc2626',
        color: '#ffffff',
      }
    case 'warning':
      return {
        ...baseStyles,
        background: '#ea580c',
        color: '#ffffff',
      }
    case 'info':
      return {
        ...baseStyles,
        background: '#2563eb',
        color: '#ffffff',
      }
  }
}

const getToastPosition = (_pathname: string): { position: 'top-right' | 'top-left' | 'top-center', containerStyle: React.CSSProperties } => {
  // Narrow fixed column so stacked toasts stay vertically centered (not full-viewport strips).
  const toastColumnWidth = 'min(420px, calc(100vw - 2rem))'
  return {
    position: 'top-center',
    containerStyle: {
      position: 'fixed',
      top: '90px',
      left: '50%',
      right: 'auto',
      bottom: 'auto',
      transform: 'translateX(-50%)',
      width: toastColumnWidth,
      maxWidth: '100%',
      boxSizing: 'border-box',
      paddingLeft: '1rem',
      paddingRight: '1rem',
      pointerEvents: 'auto',
      zIndex: 10000,
    },
  }
}

export const ToastProvider: React.FC<ToastProviderProps> = ({ children }) => {
  const location = useLocation()
  const lastToastRef = useRef<{ key: string; timestamp: number } | null>(null)
  const DEBOUNCE_MS = 500

  const { position, containerStyle } = getToastPosition(location.pathname)

  const addToast = useCallback((toastData: Toast) => {
    const { type, title, message, duration = toastData.undo ? 8000 : 4000, undo } = toastData

    const toastKey = `${type}-${title}-${message || ''}-${undo?.label || ''}`
    const now = Date.now()

    if (
      lastToastRef.current?.key === toastKey &&
      now - lastToastRef.current.timestamp < DEBOUNCE_MS
    ) {
      return
    }

    lastToastRef.current = { key: toastKey, timestamp: now }

    const customToast = (
      <div
        style={{ ...getToastStyles(type), pointerEvents: 'auto' }}
        className="flex items-start gap-3"
      >
        {getToastIcon(type)}
        <div className="flex-1 min-w-0">
          <div className="mb-1 text-base font-semibold">{title}</div>
          {message && <div className="text-sm leading-relaxed opacity-90">{message}</div>}
          {undo ? (
            <button
              type="button"
              className="mt-2 rounded-md bg-white/20 px-3 py-1.5 text-sm font-semibold hover:bg-white/30"
              onClick={() => {
                undo.onClick()
                toast.dismiss()
              }}
            >
              {undo.label}
            </button>
          ) : null}
        </div>
      </div>
    )

    toast.dismiss()
    if (undo) {
      toast.custom(customToast, {
        duration,
        position,
      })
    } else {
      toast(customToast, {
        duration,
        position,
      })
    }
  }, [position])

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <Toaster
        position={position}
        gutter={14}
        containerStyle={containerStyle}
        toastOptions={{
          style: {
            background: 'transparent',
            boxShadow: 'none',
            padding: 0,
            margin: 0,
            maxWidth: 'min(420px, calc(100vw - 2rem))',
          },
        }}
      />
    </ToastContext.Provider>
  )
}
