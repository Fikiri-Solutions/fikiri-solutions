import React from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { EmailInbox } from './EmailInbox'
import { EmailCommandCenter } from './EmailCommandCenter'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '../services/apiClient'
import { organizeAttentionCount, primaryCategoryForQueue } from '../constants/inboxSimpleFirst'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `min-h-[44px] shrink-0 border-b-2 px-3 py-2 text-sm font-medium transition-colors touch-manipulation sm:px-4 ${
    isActive
      ? 'border-brand-primary text-brand-primary dark:border-sky-400 dark:text-sky-400'
      : 'border-transparent text-brand-text/60 hover:text-brand-text dark:text-gray-400 dark:hover:text-gray-200'
  }`

/**
 * Inbox hub: Read (Gmail) + Organize (sorted piles). Single sidebar nav item (/inbox).
 */
export const InboxPage: React.FC = () => {
  const { user } = useAuth()
  const { data: triageSummary } = useQuery({
    queryKey: ['email-triage-summary', user?.id],
    queryFn: () =>
      apiClient.getEmailTriage({
        category: primaryCategoryForQueue('opportunities'),
        limit: 1,
      }),
    enabled: !!user,
    staleTime: 60_000,
  })
  const organizeBadge = organizeAttentionCount(triageSummary?.category_counts)

  return (
    <div className="flex min-h-0 w-full flex-col">
      <nav
        className="flex shrink-0 gap-1 overflow-x-auto border-b border-brand-text/10 bg-white px-2 dark:border-gray-700 dark:bg-gray-900 sm:px-4"
        aria-label="Inbox views"
      >
        <NavLink to="/inbox" end className={tabClass}>
          Read
        </NavLink>
        <NavLink to="/inbox/command-center" className={tabClass}>
          Organize
          {organizeBadge > 0 ? (
            <span className="ml-1.5 inline-flex min-w-[1.25rem] items-center justify-center rounded-full bg-brand-primary/15 px-1.5 py-0.5 text-xs font-semibold tabular-nums text-brand-primary dark:bg-sky-500/20 dark:text-sky-300">
              {organizeBadge > 99 ? '99+' : organizeBadge}
            </span>
          ) : null}
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
