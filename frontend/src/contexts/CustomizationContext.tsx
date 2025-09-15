import React, { createContext, useContext, useEffect, useState } from 'react'

export interface UserCustomization {
  accentColor: string
  logoUrl?: string
  companyName?: string
}

interface CustomizationContextType {
  customization: UserCustomization
  updateCustomization: (updates: Partial<UserCustomization>) => void
  resetCustomization: () => void
}

const CustomizationContext = createContext<CustomizationContextType | undefined>(undefined)

export const useCustomization = () => {
  const context = useContext(CustomizationContext)
  if (!context) {
    throw new Error('useCustomization must be used within a CustomizationProvider')
  }
  return context
}

interface CustomizationProviderProps {
  children: React.ReactNode
}

const defaultCustomization: UserCustomization = {
  accentColor: '#3B82F6', // Default Fikiri blue
  logoUrl: undefined,
  companyName: 'Fikiri Solutions',
}

export const CustomizationProvider: React.FC<CustomizationProviderProps> = ({ children }) => {
  const [customization, setCustomization] = useState<UserCustomization>(defaultCustomization)

  // Load customization from localStorage on mount
  useEffect(() => {
    const savedCustomization = localStorage.getItem('fikiri-customization')
    if (savedCustomization) {
      try {
        const parsed = JSON.parse(savedCustomization)
        setCustomization({ ...defaultCustomization, ...parsed })
      } catch (error) {
        console.warn('Failed to parse saved customization:', error)
      }
    }
  }, [])

  // Save customization to localStorage
  useEffect(() => {
    localStorage.setItem('fikiri-customization', JSON.stringify(customization))
    
    // Update CSS custom properties
    document.documentElement.style.setProperty('--fikiri-primary', customization.accentColor)
    
    // Update page title if company name changed
    if (customization.companyName && customization.companyName !== 'Fikiri Solutions') {
      document.title = `${customization.companyName} - Dashboard`
    }
  }, [customization])

  const updateCustomization = (updates: Partial<UserCustomization>) => {
    setCustomization(prev => ({ ...prev, ...updates }))
  }

  const resetCustomization = () => {
    setCustomization(defaultCustomization)
  }

  return (
    <CustomizationContext.Provider value={{ customization, updateCustomization, resetCustomization }}>
      {children}
    </CustomizationContext.Provider>
  )
}
