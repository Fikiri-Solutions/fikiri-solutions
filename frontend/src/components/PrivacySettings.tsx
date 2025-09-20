import React, { useState, useEffect } from 'react'
import { Shield, Download, Trash2, Settings, AlertTriangle, CheckCircle, Clock, Database } from 'lucide-react'

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
      
      // Load privacy settings
      const settingsResponse = await fetch(`https://fikirisolutions.onrender.com/api/privacy/settings?user_id=${userId}`)
      const settingsData = await settingsResponse.json()
      
      if (settingsData.success) {
        setSettings(settingsData.data)
      }

      // Load data summary
      const summaryResponse = await fetch(`https://fikirisolutions.onrender.com/api/privacy/data-summary?user_id=${userId}`)
      const summaryData = await summaryResponse.json()
      
      if (summaryData.success) {
        setDataSummary(summaryData.data)
      }

      // Load consents
      const consentsResponse = await fetch(`https://fikirisolutions.onrender.com/api/privacy/consents?user_id=${userId}`)
      const consentsData = await consentsResponse.json()
      
      if (consentsData.success) {
        setConsents(consentsData.data.consents)
      }

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

      const response = await fetch('https://fikirisolutions.onrender.com/api/privacy/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: parseInt(userId),
          [key]: value
        })
      })

      const data = await response.json()
      
      if (data.success) {
        setSettings(data.data.settings)
        setSuccess('Privacy settings updated successfully')
        setTimeout(() => setSuccess(null), 3000)
      } else {
        setError(data.error || 'Failed to update settings')
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

      const response = await fetch('https://fikirisolutions.onrender.com/api/privacy/cleanup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: parseInt(userId)
        })
      })

      const data = await response.json()
      
      if (data.success) {
        setSuccess(`Data cleanup completed. ${data.data.total_deleted} records deleted.`)
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

      const response = await fetch(`https://fikirisolutions.onrender.com/api/privacy/export?user_id=${userId}`)
      const data = await response.json()
      
      if (data.success) {
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

      const response = await fetch('https://fikirisolutions.onrender.com/api/privacy/delete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: parseInt(userId),
          confirmation: deleteConfirmation
        })
      })

      const data = await response.json()
      
      if (data.success) {
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-brand-text dark:text-white">Privacy & Data Management</h1>
          <p className="mt-1 text-sm text-brand-text/70 dark:text-gray-400">
            Control your data privacy settings and manage your information.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Shield className="h-6 w-6 text-brand-primary dark:text-brand-accent" />
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
              <label className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-2">
                Data Retention Period
              </label>
              <div className="flex items-center space-x-4">
                <input
                  type="range"
                  min="30"
                  max="365"
                  value={settings.data_retention_days}
                  onChange={(e) => updateSetting('data_retention_days', parseInt(e.target.value))}
                  className="flex-1 accent-brand-primary"
                  disabled={isLoading}
                />
                <span className="text-sm text-brand-text/70 dark:text-gray-300 min-w-[60px]">
                  {settings.data_retention_days} days
                </span>
              </div>
              <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-1">
                Data older than this period will be automatically deleted
              </p>
            </div>

            {/* Email Scanning */}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-brand-text dark:text-white">Email Scanning</h3>
                <p className="text-xs text-brand-text/60 dark:text-gray-400">Allow AI to scan emails for lead detection</p>
              </div>
              <button
                onClick={() => updateSetting('email_scanning_enabled', !settings.email_scanning_enabled)}
                disabled={isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.email_scanning_enabled ? 'bg-brand-primary' : 'bg-brand-text/20'
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
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-900">Personal Email Exclusion</h3>
                <p className="text-xs text-gray-500">Exclude personal emails from business processing</p>
              </div>
              <button
                onClick={() => updateSetting('personal_email_exclusion', !settings.personal_email_exclusion)}
                disabled={isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.personal_email_exclusion ? 'bg-blue-600' : 'bg-gray-200'
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
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-900">Auto Labeling</h3>
                <p className="text-xs text-gray-500">Automatically apply labels to emails</p>
              </div>
              <button
                onClick={() => updateSetting('auto_labeling_enabled', !settings.auto_labeling_enabled)}
                disabled={isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.auto_labeling_enabled ? 'bg-blue-600' : 'bg-gray-200'
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
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-900">Lead Detection</h3>
                <p className="text-xs text-gray-500">Automatically detect and create leads from emails</p>
              </div>
              <button
                onClick={() => updateSetting('lead_detection_enabled', !settings.lead_detection_enabled)}
                disabled={isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.lead_detection_enabled ? 'bg-blue-600' : 'bg-gray-200'
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
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-900">Analytics Tracking</h3>
                <p className="text-xs text-gray-500">Allow usage analytics for service improvement</p>
              </div>
              <button
                onClick={() => updateSetting('analytics_tracking_enabled', !settings.analytics_tracking_enabled)}
                disabled={isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.analytics_tracking_enabled ? 'bg-blue-600' : 'bg-gray-200'
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
          <div className="flex items-center justify-between p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <div>
              <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">Cleanup Expired Data</h3>
              <p className="text-xs text-yellow-700 dark:text-yellow-300">
                Delete data older than your retention period
              </p>
            </div>
            <button
              onClick={cleanupExpiredData}
              disabled={isLoading}
              className="px-4 py-2 text-brand-text bg-brand-background/50 hover:bg-brand-background/80 border border-brand-text/20 rounded-lg font-medium transition-all duration-200 flex items-center space-x-2"
            >
              <Clock className="h-4 w-4" />
              <span>Cleanup Now</span>
            </button>
          </div>

          {/* Export Data */}
          <div className="flex items-center justify-between p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div>
              <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">Export Your Data</h3>
              <p className="text-xs text-blue-700 dark:text-blue-300">
                Download all your data in JSON format
              </p>
            </div>
            <button
              onClick={exportUserData}
              disabled={isLoading}
              className="bg-brand-primary hover:bg-brand-secondary text-white px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center space-x-2"
            >
              <Download className="h-4 w-4" />
              <span>Export Data</span>
            </button>
          </div>

          {/* Delete All Data */}
          <div className="flex items-center justify-between p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div>
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Delete All Data</h3>
              <p className="text-xs text-red-700 dark:text-red-300">
                Permanently delete all your data and account
              </p>
            </div>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              disabled={isLoading}
              className="bg-brand-error hover:bg-brand-error/80 text-white px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center space-x-2"
            >
              <Trash2 className="h-4 w-4" />
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
              <div key={consent.id} className="flex items-center justify-between p-3 bg-brand-background/50 dark:bg-gray-700 rounded-lg">
                <div>
                  <h3 className="text-sm font-medium text-brand-text dark:text-white capitalize">
                    {consent.consent_type.replace('_', ' ')}
                  </h3>
                  <p className="text-xs text-brand-text/60 dark:text-gray-400">
                    {consent.granted ? 'Granted' : 'Denied'} on {new Date(consent.granted_at).toLocaleDateString()}
                  </p>
                </div>
                <div className={`px-2 py-1 rounded-full text-xs font-medium ${
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

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-brand-background dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4 border border-brand-text/10">
            <div className="flex items-center space-x-3 mb-4">
              <AlertTriangle className="h-6 w-6 text-brand-error" />
              <h3 className="text-lg font-semibold text-brand-text dark:text-white">Delete All Data</h3>
            </div>
            
            <p className="text-sm text-brand-text/70 dark:text-gray-300 mb-4">
              This action cannot be undone. All your data, including leads, activities, and account information, will be permanently deleted.
            </p>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-2">
                Type "DELETE_ALL_MY_DATA" to confirm:
              </label>
              <input
                type="text"
                value={deleteConfirmation}
                onChange={(e) => setDeleteConfirmation(e.target.value)}
                className="bg-white text-brand-text border border-brand-text/20 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
                placeholder="DELETE_ALL_MY_DATA"
              />
            </div>
            
            <div className="flex space-x-3">
              <button
                onClick={() => {
                  setShowDeleteConfirm(false)
                  setDeleteConfirmation('')
                }}
                className="px-4 py-2 text-brand-text bg-brand-background/50 hover:bg-brand-background/80 border border-brand-text/20 rounded-lg font-medium transition-all duration-200 flex-1"
              >
                Cancel
              </button>
              <button
                onClick={deleteUserData}
                disabled={deleteConfirmation !== 'DELETE_ALL_MY_DATA' || isLoading}
                className="bg-brand-error hover:bg-brand-error/80 text-white px-4 py-2 rounded-lg font-medium transition-all duration-200 flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
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
