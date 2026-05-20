import React from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { EmailInbox } from './EmailInbox'
import { EmailCommandCenter } from './EmailCommandCenter'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `min-h-[44px] shrink-0 border-b-2 px-3 py-2 text-sm font-medium transition-colors touch-manipulation sm:px-4 ${
    isActive
      ? 'border-brand-primary text-brand-primary dark:border-sky-400 dark:text-sky-400'
      : 'border-transparent text-brand-text/60 hover:text-brand-text dark:text-gray-400 dark:hover:text-gray-200'
  }`

/**
 * Inbox hub: live Gmail (unchanged) + Command Center (synced triage).
 * Single sidebar nav item (/inbox).
 */
export const InboxPage: React.FC = () => {
  return (
    <div className="flex min-h-0 w-full flex-col">
      <nav
        className="flex shrink-0 gap-1 overflow-x-auto border-b border-brand-text/10 bg-white px-2 dark:border-gray-700 dark:bg-gray-900 sm:px-4"
        aria-label="Inbox views"
      >
        <NavLink to="/inbox" end className={tabClass}>
          Live mail
        </NavLink>
        <NavLink to="/inbox/command-center" className={tabClass}>
          Command Center
        </NavLink>
      </nav>
      <div className="min-h-0 flex-1">
        <Routes>
          <Route index element={<EmailInbox />} />
          <Route path="command-center" element={<EmailCommandCenter />} />
        </Routes>
      </div>
    </div>
  )
}
