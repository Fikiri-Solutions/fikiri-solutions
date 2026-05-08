import React, { useState, useEffect } from 'react'
import { Shield, Download, Trash2, Settings, AlertTriangle, CheckCircle, Clock, Database } from 'lucide-react'
import { LegalFooterLinks } from './LegalFooterLinks'
import { apiClient } from '../services/apiClient'

interface PrivacySettings {
  data_retention_days: number
  email_scanning_enabled: boolean
  personal_email_exclusion: boolean
  auto_labeling_enabled: boolean
  lead_detection_enabled: boolean
  analytics_tracking_enabled: boolean
  updated_at: string
}

interface DataSummary {
  leads_count: number
  activities_count: number
  sync_records_count: number
  privacy_settings: PrivacySettings
  consents: {
    gmail_access: boolean
    data_processing: boolean
    analytics: boolean
  }
}

interface PrivacyConsent {
  id: number
  consent_type: string
  granted: boolean
  consent_text: string
  granted_at: string
  revoked_at?: string
}

export const PrivacySettings: React.FC = () => {
  const [settings, setSettings] = useState<PrivacySettings | null>(null)
  const [dataSummary, setDataSummary] = useState<DataSummary | null>(null)
  const [consents, setConsents] = useState<PrivacyConsent[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteConfirmation, setDeleteConfirmation] = useState('')

  const userId = localStorage.getItem('fikiri-user-id')

  useEffect(() => {
    if (userId) {
      loadPrivacyData()
    }
  }, [userId])

  const loadPrivacyData = async () => {
    if (!userId) return

    try {
      setIsLoading(true)
      
      const [settingsData, summaryData, consentsData] = await Promise.all([
        apiClient.request<{ success?: boolean; data?: any }>('GET', '/privacy/settings', { params: { user_id: userId } }),
        apiClient.request<{ success?: boolean; data?: any }>('GET', '/privacy/data-summary', { params: { user_id: userId } }),
        apiClient.request<{ success?: boolean; data?: { consents?: any } }>('GET', '/privacy/consents', { params: { user_id: userId } })
      ])

      if (settingsData?.success && settingsData.data) setSettings(settingsData.data)
      if (summaryData?.success && summaryData.data) setDataSummary(summaryData.data)
      if (consentsData?.success && consentsData.data?.consents) setConsents(consentsData.data.consents)

    } catch (error) {
      setError('Failed to load privacy data')
    } finally {
      setIsLoading(false)
    }
  }

  const updateSetting = async (key: keyof PrivacySettings, value: any) => {
    if (!userId || !settings) return

    try {
      setIsLoading(true)
      setError(null)

      const data = await apiClient.request<{ success?: boolean; data?: { settings?: any } }>(
        'PUT',
        '/privacy/settings',
        { data: { user_id: parseInt(userId), [key]: value } }
      )

      if (data?.success && data.data?.settings) {
        setSettings(data.data.settings)
        setSuccess('Privacy settings updated successfully')
        setTimeout(() => setSuccess(null), 3000)
      } else {
        setError((data as { error?: string }).error || 'Failed to update settings')
      }
    } catch (error) {
      setError('Failed to update privacy settings')
    } finally {
      setIsLoading(false)
    }
  }

  const cleanupExpiredData = async () => {
    if (!userId) return

    try {
      setIsLoading(true)
      setError(null)

      const data = await apiClient.request<{ success?: boolean; data?: { total_deleted?: number }; error?: string }>(
        'POST',
        '/privacy/cleanup',
        { data: { user_id: parseInt(userId) } }
      )

      if (data?.success) {
        setSuccess(`Data cleanup completed. ${(data.data?.total_deleted) ?? 0} records deleted.`)
        setTimeout(() => setSuccess(null), 5000)
        loadPrivacyData() // Reload data summary
      } else {
        setError(data.error || 'Failed to cleanup data')
      }
    } catch (error) {
      setError('Failed to cleanup expired data')
    } finally {
      setIsLoading(false)
    }
  }

  const exportUserData = async () => {
    if (!userId) return

    try {
      setIsLoading(true)
      setError(null)

      const data = await apiClient.request<{ success?: boolean; data?: any; error?: string }>(
        'GET',
        '/privacy/export',
        { params: { user_id: userId } }
      )

      if (data?.success && data.data) {
        // Download the data as JSON file
        const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `fikiri-data-export-${new Date().toISOString().split('T')[0]}.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        
        setSuccess('Data exported successfully')
        setTimeout(() => setSuccess(null), 3000)
      } else {
        setError(data.error || 'Failed to export data')
      }
    } catch (error) {
      setError('Failed to export user data')
    } finally {
      setIsLoading(false)
    }
  }

  const deleteUserData = async () => {
    if (!userId || deleteConfirmation !== 'DELETE_ALL_MY_DATA') return

    try {
      setIsLoading(true)
      setError(null)

      const data = await apiClient.request<{ success?: boolean; error?: string }>(
        'POST',
        '/privacy/delete',
        { data: { user_id: parseInt(userId), confirmation: deleteConfirmation } }
      )
      
      if (data?.success) {
        setSuccess('All your data has been deleted successfully')
        setTimeout(() => {
          localStorage.clear()
          window.location.href = '/login'
        }, 3000)
      } else {
        setError(data.error || 'Failed to delete data')
      }
    } catch (error) {
      setError('Failed to delete user data')
    } finally {
      setIsLoading(false)
      setShowDeleteConfirm(false)
      setDeleteConfirmation('')
    }
  }

  if (isLoading && !settings) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-bold text-brand-text dark:text-white">Privacy & Data Management</h1>
          <p className="mt-1 text-sm text-brand-text/70 dark:text-gray-400">
            Control your data privacy settings and manage your information.
          </p>
          <LegalFooterLinks className="mt-3 text-sm text-brand-text/70 dark:text-gray-400" />
        </div>
        <div className="flex shrink-0 items-center gap-2 self-start sm:self-center">
          <Shield className="h-6 w-6 shrink-0 text-brand-primary dark:text-brand-accent" aria-hidden />
          <span className="text-sm font-medium text-brand-primary dark:text-brand-accent">GDPR Compliant</span>
        </div>
      </div>

      {/* Success/Error Messages */}
      {success && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex items-start">
            <CheckCircle className="h-5 w-5 text-green-400 mt-0.5 mr-3" />
            <div>
              <h3 className="text-sm font-medium text-green-800 dark:text-green-200">Success</h3>
              <p className="mt-1 text-sm text-green-700 dark:text-green-300">{success}</p>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-start">
            <AlertTriangle className="h-5 w-5 text-red-400 mt-0.5 mr-3" />
            <div>
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Error</h3>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Data Summary */}
      {dataSummary && (
        <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
          <div className="flex items-center space-x-3 mb-4">
            <Database className="h-5 w-5 text-brand-primary dark:text-brand-accent" />
            <h2 className="text-lg font-semibold text-brand-text dark:text-white">Your Data Summary</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-brand-accent/20 dark:bg-brand-accent/20 rounded-lg p-4">
              <div className="text-2xl font-bold text-brand-primary dark:text-brand-accent">{dataSummary.leads_count}</div>
              <div className="text-sm text-brand-text/70 dark:text-gray-300">Leads</div>
            </div>
            <div className="bg-brand-secondary/20 dark:bg-brand-secondary/20 rounded-lg p-4">
              <div className="text-2xl font-bold text-brand-secondary dark:text-brand-secondary">{dataSummary.activities_count}</div>
              <div className="text-sm text-brand-text/70 dark:text-gray-300">Activities</div>
            </div>
            <div className="bg-brand-warning/20 dark:bg-brand-warning/20 rounded-lg p-4">
              <div className="text-2xl font-bold text-brand-warning dark:text-brand-warning">{dataSummary.sync_records_count}</div>
              <div className="text-sm text-brand-text/70 dark:text-gray-300">Sync Records</div>
            </div>
          </div>
        </div>
      )}

      {/* Privacy Settings */}
      {settings && (
        <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
          <div className="flex items-center space-x-3 mb-6">
            <Settings className="h-5 w-5 text-brand-primary dark:text-brand-accent" />
            <h2 className="text-lg font-semibold text-brand-text dark:text-white">Privacy Settings</h2>
          </div>

          <div className="space-y-6">
            {/* Data Retention */}
            <div>
              <label htmlFor="privacy-data-retention-days" className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-2">
                Data Retention Period
              </label>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
                <input
                  id="privacy-data-retention-days"
                  type="range"
                  min="30"
                  max="365"
                  value={settings.data_retention_days}
                  onChange={(e) => updateSetting('data_retention_days', parseInt(e.target.value))}
                  className="min-h-[44px] w-full flex-1 accent-brand-primary sm:min-h-0"
                  disabled={isLoading}
                />
                <span className="shrink-0 text-sm text-brand-text/70 dark:text-gray-300 sm:min-w-[60px] sm:text-right">
                  {settings.data_retention_days} days
                </span>
              </div>
              <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-1">
                Data older than this period will be automatically deleted
              </p>
            </div>

            {/* Email Scanning */}
            <div className="flex flex-col gap-3 rounded-lg border border-transparent py-1 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-medium text-brand-text dark:text-white">Email Scanning</h3>
                <p className="text-xs text-brand-text/60 dark:text-gray-400">Allow AI to scan emails for lead detection</p>
              </div>
              <button
                type="button"
                onClick={() => updateSetting('email_scanning_enabled', !settings.email_scanning_enabled)}
                disabled={isLoading}
                aria-pressed={settings.email_scanning_enabled}
                className={`relative inline-flex h-8 w-11 shrink-0 items-center self-end rounded-full transition-colors sm:h-6 sm:self-center ${
                  settings.email_scanning_enabled ? 'bg-brand-primary' : 'bg-brand-text/20 dark:bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.email_scanning_enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Personal Email Exclusion */}
            <div className="flex flex-col gap-3 rounded-lg border border-transparent py-1 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-medium text-brand-text dark:text-white">Personal Email Exclusion</h3>
                <p className="text-xs text-brand-text/60 dark:text-gray-400">Exclude personal emails from business processing</p>
              </div>
              <button
                type="button"
                onClick={() => updateSetting('personal_email_exclusion', !settings.personal_email_exclusion)}
                disabled={isLoading}
                aria-pressed={settings.personal_email_exclusion}
                className={`relative inline-flex h-8 w-11 shrink-0 items-center self-end rounded-full transition-colors sm:h-6 sm:self-center ${
                  settings.personal_email_exclusion ? 'bg-brand-primary dark:bg-brand-secondary' : 'bg-brand-text/20 dark:bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.personal_email_exclusion ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Auto Labeling */}
            <div className="flex flex-col gap-3 rounded-lg border border-transparent py-1 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-medium text-brand-text dark:text-white">Auto Labeling</h3>
                <p className="text-xs text-brand-text/60 dark:text-gray-400">Automatically apply labels to emails</p>
              </div>
              <button
                type="button"
                onClick={() => updateSetting('auto_labeling_enabled', !settings.auto_labeling_enabled)}
                disabled={isLoading}
                aria-pressed={settings.auto_labeling_enabled}
                className={`relative inline-flex h-8 w-11 shrink-0 items-center self-end rounded-full transition-colors sm:h-6 sm:self-center ${
                  settings.auto_labeling_enabled ? 'bg-brand-primary dark:bg-brand-secondary' : 'bg-brand-text/20 dark:bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.auto_labeling_enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Lead Detection */}
            <div className="flex flex-col gap-3 rounded-lg border border-transparent py-1 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-medium text-brand-text dark:text-white">Lead Detection</h3>
                <p className="text-xs text-brand-text/60 dark:text-gray-400">Automatically detect and create leads from emails</p>
              </div>
              <button
                type="button"
                onClick={() => updateSetting('lead_detection_enabled', !settings.lead_detection_enabled)}
                disabled={isLoading}
                aria-pressed={settings.lead_detection_enabled}
                className={`relative inline-flex h-8 w-11 shrink-0 items-center self-end rounded-full transition-colors sm:h-6 sm:self-center ${
                  settings.lead_detection_enabled ? 'bg-brand-primary dark:bg-brand-secondary' : 'bg-brand-text/20 dark:bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.lead_detection_enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Analytics Tracking */}
            <div className="flex flex-col gap-3 rounded-lg border border-transparent py-1 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-medium text-brand-text dark:text-white">Analytics Tracking</h3>
                <p className="text-xs text-brand-text/60 dark:text-gray-400">Allow usage analytics for service improvement</p>
              </div>
              <button
                type="button"
                onClick={() => updateSetting('analytics_tracking_enabled', !settings.analytics_tracking_enabled)}
                disabled={isLoading}
                aria-pressed={settings.analytics_tracking_enabled}
                className={`relative inline-flex h-8 w-11 shrink-0 items-center self-end rounded-full transition-colors sm:h-6 sm:self-center ${
                  settings.analytics_tracking_enabled ? 'bg-brand-primary dark:bg-brand-secondary' : 'bg-brand-text/20 dark:bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.analytics_tracking_enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Data Management Actions */}
      <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
        <div className="flex items-center space-x-3 mb-6">
          <Database className="h-5 w-5 text-brand-primary dark:text-brand-accent" />
          <h2 className="text-lg font-semibold text-brand-text dark:text-white">Data Management</h2>
        </div>

        <div className="space-y-4">
          {/* Cleanup Expired Data */}
          <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <div className="min-w-0">
              <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">Cleanup Expired Data</h3>
              <p className="text-xs text-yellow-700 dark:text-yellow-300">
                Delete data older than your retention period
              </p>
            </div>
            <button
              type="button"
              onClick={cleanupExpiredData}
              disabled={isLoading}
              className="inline-flex min-h-[44px] w-full shrink-0 items-center justify-center gap-2 rounded-lg border border-brand-text/20 bg-brand-background/50 px-4 py-2 font-medium text-brand-text transition-all duration-200 hover:bg-brand-background/80 sm:w-auto"
            >
              <Clock className="h-4 w-4 shrink-0" />
              <span>Cleanup Now</span>
            </button>
          </div>

          {/* Export Data */}
          <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="min-w-0">
              <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">Export Your Data</h3>
              <p className="text-xs text-blue-700 dark:text-blue-300">
                Download all your data in JSON format
              </p>
            </div>
            <button
              type="button"
              onClick={exportUserData}
              disabled={isLoading}
              className="inline-flex min-h-[44px] w-full shrink-0 items-center justify-center gap-2 rounded-lg bg-brand-primary px-4 py-2 font-medium text-white transition-all duration-200 hover:bg-brand-secondary sm:w-auto"
            >
              <Download className="h-4 w-4 shrink-0" />
              <span>Export Data</span>
            </button>
          </div>

          {/* Delete All Data */}
          <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="min-w-0">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Delete All Data</h3>
              <p className="text-xs text-red-700 dark:text-red-300">
                Permanently delete all your data and account
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={isLoading}
              className="inline-flex min-h-[44px] w-full shrink-0 items-center justify-center gap-2 rounded-lg bg-brand-error px-4 py-2 font-medium text-white transition-all duration-200 hover:bg-brand-error/80 sm:w-auto"
            >
              <Trash2 className="h-4 w-4 shrink-0" />
              <span>Delete All</span>
            </button>
          </div>
        </div>
      </div>

      {/* Consent History */}
      {consents.length > 0 && (
        <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
          <div className="flex items-center space-x-3 mb-6">
            <Shield className="h-5 w-5 text-brand-primary dark:text-brand-accent" />
            <h2 className="text-lg font-semibold text-brand-text dark:text-white">Consent History</h2>
          </div>

          <div className="space-y-3">
            {consents.map((consent) => (
              <div key={consent.id} className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 bg-brand-background/50 dark:bg-gray-700 rounded-lg">
                <div className="min-w-0">
                  <h3 className="text-sm font-medium text-brand-text dark:text-white capitalize">
                    {consent.consent_type.replace('_', ' ')}
                  </h3>
                  <p className="text-xs text-brand-text/60 dark:text-gray-400">
                    {consent.granted ? 'Granted' : 'Denied'} on {new Date(consent.granted_at).toLocaleDateString()}
                  </p>
                </div>
                <div className={`shrink-0 self-start px-2 py-1 rounded-full text-xs font-medium sm:self-center ${
                  consent.granted 
                    ? 'bg-brand-accent/20 text-brand-primary dark:bg-brand-accent/20 dark:text-brand-accent' 
                    : 'bg-brand-error/20 text-brand-error dark:bg-brand-error/20 dark:text-brand-error'
                }`}>
                  {consent.granted ? 'Granted' : 'Denied'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="border-t border-brand-text/10 pt-6">
        <LegalFooterLinks className="text-sm text-center text-brand-text/60 dark:text-gray-500" />
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="privacy-delete-title"
        >
          <div className="max-h-[min(90dvh,100%)] w-full max-w-md overflow-y-auto rounded-t-2xl border border-brand-text/10 bg-brand-background p-4 safe-area-pb sm:my-auto sm:rounded-lg sm:p-6 dark:bg-gray-800">
            <div className="mb-4 flex items-center gap-3">
              <AlertTriangle className="h-6 w-6 shrink-0 text-brand-error" aria-hidden />
              <h3 id="privacy-delete-title" className="text-lg font-semibold text-brand-text dark:text-white">
                Delete All Data
              </h3>
            </div>

            <p className="mb-4 text-sm text-brand-text/70 dark:text-gray-300">
              This action cannot be undone. All your data, including leads, activities, and account information, will be permanently deleted.
            </p>

            <div className="mb-4">
              <label htmlFor="privacy-delete-confirm-input" className="mb-2 block text-sm font-medium text-brand-text dark:text-gray-300">
                Type &quot;DELETE_ALL_MY_DATA&quot; to confirm:
              </label>
              <input
                id="privacy-delete-confirm-input"
                type="text"
                value={deleteConfirmation}
                onChange={(e) => setDeleteConfirmation(e.target.value)}
                autoComplete="off"
                className="w-full rounded-lg border border-brand-text/20 bg-white px-4 py-2 text-brand-text focus:border-brand-accent focus:ring-brand-accent dark:bg-gray-900 dark:text-white"
                placeholder="DELETE_ALL_MY_DATA"
              />
            </div>

            <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowDeleteConfirm(false)
                  setDeleteConfirmation('')
                }}
                className="min-h-[44px] flex-1 rounded-lg border border-brand-text/20 bg-brand-background/50 px-4 py-2 font-medium text-brand-text transition-all duration-200 hover:bg-brand-background/80"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={deleteUserData}
                disabled={deleteConfirmation !== 'DELETE_ALL_MY_DATA' || isLoading}
                className="min-h-[44px] flex-1 rounded-lg bg-brand-error px-4 py-2 font-medium text-white transition-all duration-200 hover:bg-brand-error/80 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isLoading ? 'Deleting...' : 'Delete All Data'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
