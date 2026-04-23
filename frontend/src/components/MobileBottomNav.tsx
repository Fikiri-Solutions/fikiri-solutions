import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import { getMobileBottomNavItems, isDashboardNavItemActive } from '../navigation/dashboardNav'

interface MobileBottomNavProps {
  className?: string
}

export const MobileBottomNav: React.FC<MobileBottomNavProps> = ({ className = '' }) => {
  const location = useLocation()
  const { user } = useAuth()
  const navigation = getMobileBottomNavItems(user)

  return (
    <motion.div 
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`lg:hidden fixed bottom-0 left-0 right-0 z-30 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 px-2 py-1 safe-area-pb ${className}`}
    >
      {/* Six primary destinations: equal flex columns; icon-only on very narrow widths to keep taps ≥44px */}
      <div className="flex justify-between gap-0.5">
        {navigation.map((item, index) => {
          const isActive = isDashboardNavItemActive(location.pathname, item.href)
          return (
            <motion.div
              key={item.href}
              className="min-w-0 flex-1 flex justify-center"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <Link
                to={item.href}
                aria-label={item.name}
                title={item.name}
                className={`flex flex-col items-center justify-center min-h-[48px] w-full max-w-[5.5rem] py-1.5 px-1 rounded-lg transition-all duration-200 active:opacity-80 ${
                  isActive
                    ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
              >
                <motion.div
                  animate={{ scale: isActive ? 1.08 : 1 }}
                  transition={{ duration: 0.2 }}
                >
                  <item.icon className={`h-6 w-6 shrink-0 ${isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'}`} />
                </motion.div>
                <span
                  className={`text-[0.65rem] leading-tight mt-0.5 font-medium text-center truncate w-full max-[380px]:hidden ${isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'}`}
                >
                  {item.name}
                </span>
              </Link>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}
