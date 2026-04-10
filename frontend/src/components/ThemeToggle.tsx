import React from 'react'
import { Sun, Moon, Monitor } from 'lucide-react'
import { useTheme } from '../contexts/ThemeContext'

export const ThemeToggle: React.FC = () => {
  const { theme, setTheme, resolvedTheme } = useTheme()

  const themes = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'System', icon: Monitor },
  ] as const

  return (
    <div className="flex shrink-0 items-center space-x-0.5 bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5 sm:space-x-1 sm:p-1">
      {themes.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          type="button"
          onClick={() => setTheme(value)}
          className={`flex min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 items-center justify-center space-x-1 rounded-md px-2 py-2 sm:px-3 sm:py-1.5 text-sm font-medium transition-all duration-200 ${
            theme === value
              ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
          }`}
          title={`${label} theme`}
          aria-label={`Use ${label} theme`}
          aria-pressed={theme === value}
        >
          <Icon className="h-4 w-4 shrink-0" />
          <span className="hidden sm:inline">{label}</span>
        </button>
      ))}
    </div>
  )
}
