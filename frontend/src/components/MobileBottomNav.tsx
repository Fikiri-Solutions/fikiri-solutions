import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Mail, Users, Brain, Settings, Home } from 'lucide-react'

interface MobileBottomNavProps {
  className?: string
}

export const MobileBottomNav: React.FC<MobileBottomNavProps> = ({ className = '' }) => {
  const location = useLocation()

  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'Services', href: '/services', icon: Settings },
    { name: 'CRM', href: '/crm', icon: Users },
    { name: 'AI Assistant', href: '/ai', icon: Brain },
  ]

  return (
    <div className={`lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-4 py-2 ${className}`}>
      <div className="flex justify-around">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`flex flex-col items-center py-2 px-3 rounded-lg transition-colors duration-200 ${
                isActive
                  ? 'text-blue-600 bg-blue-50'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <item.icon className={`h-5 w-5 ${isActive ? 'text-blue-600' : 'text-gray-500'}`} />
              <span className={`text-xs mt-1 font-medium ${isActive ? 'text-blue-600' : 'text-gray-500'}`}>
                {item.name}
              </span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
