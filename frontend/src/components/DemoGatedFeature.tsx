import React from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle } from 'lucide-react'
import {
  DEMO_UNAVAILABLE_COPY,
  isRouteGatedForDemo,
  type DemoGatedRoute,
} from '../lib/demoSafety'

interface DemoGatedFeatureProps {
  route: DemoGatedRoute
  children: React.ReactNode
  /** When true, show preview banner but still render children (e.g. Services). */
  previewOnly?: boolean
}

export const DemoGatedFeature: React.FC<DemoGatedFeatureProps> = ({
  route,
  children,
  previewOnly = false,
}) => {
  const gated = isRouteGatedForDemo(route)
  const copy = DEMO_UNAVAILABLE_COPY[route]

  if (gated && !previewOnly) {
    return (
      <div className="mx-auto max-w-lg space-y-4 px-4 py-16 text-center">
        <AlertCircle className="mx-auto h-12 w-12 text-amber-600 dark:text-amber-400" aria-hidden />
        <h1 className="text-xl font-semibold text-brand-text dark:text-white">{copy.title}</h1>
        <p className="text-sm text-brand-text/70 dark:text-gray-400">{copy.body}</p>
        <div className="flex flex-wrap justify-center gap-3 pt-2">
          <Link
            to="/crm"
            className="inline-flex min-h-[44px] items-center rounded-lg bg-brand-primary px-4 py-2 text-sm font-medium text-white hover:bg-brand-secondary"
          >
            Open CRM
          </Link>
          <Link
            to="/dashboard"
            className="inline-flex min-h-[44px] items-center rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-brand-text hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            Dashboard
          </Link>
        </div>
      </div>
    )
  }

  return (
    <>
      {gated && previewOnly && (
        <div
          className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100"
          role="status"
        >
          <strong>Preview only:</strong> {copy.body}
        </div>
      )}
      {children}
    </>
  )
}
