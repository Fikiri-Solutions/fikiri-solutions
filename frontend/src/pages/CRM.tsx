import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { Users, Mail, Phone, Building, Calendar, Star, Filter, Search, Plus, Activity, Download, Upload, GitBranch } from 'lucide-react'
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd'
import { apiClient, LeadData } from '../services/apiClient'
import { EmptyState } from '../components/EmptyState'
import { ErrorMessage, getUserFriendlyError } from '../components/ErrorMessage'
import { FeatureStatus, getFeatureStatus } from '../components/FeatureStatus'
import { useToast } from '../components/Toast'
import { LeadTraceModal } from '../components/LeadTraceModal'
import { TableScroll } from '../components/TableScroll'

/** Must match canonical stages in `crm/service.py` (`lead_stages`). */
const pipelineStages = [
  { id: 'new', title: 'New', accent: 'border-blue-200 bg-blue-50 dark:bg-blue-900/30', helper: 'Manual, forms, automations' },
  { id: 'contacted', title: 'Contacted', accent: 'border-amber-200 bg-amber-50 dark:bg-amber-900/30', helper: 'Outreach started' },
  { id: 'replied', title: 'Replied', accent: 'border-cyan-200 bg-cyan-50 dark:bg-cyan-900/25', helper: 'Two-way conversation' },
  { id: 'qualified', title: 'Qualified', accent: 'border-emerald-200 bg-emerald-50 dark:bg-emerald-900/20', helper: 'Fit confirmed' },
  { id: 'closed', title: 'Closed', accent: 'border-purple-200 bg-purple-50 dark:bg-purple-900/30', helper: 'Won or closed' }
] as const

function pipelineColumnForStage(stage: string | undefined): string {
  const s = (stage || 'new').toLowerCase()
  if (s === 'booked' || s === 'converted') return 'closed'
  const allowed = new Set(pipelineStages.map(p => p.id))
  if (allowed.has(s as (typeof pipelineStages)[number]['id'])) return s
  return 'new'
}

const PIPELINE_STAGE_PAGE_SIZE = 8
const TABLE_PAGE_SIZE = 50

const pipelineEmptyCopy: Record<(typeof pipelineStages)[number]['id'], string> = {
  new: 'No new leads yet. New opportunities will appear here.',
  contacted: 'No contacted leads yet. Drag leads here once outreach starts.',
  replied: 'No replies yet. Move leads here when a conversation starts.',
  qualified: 'No qualified leads yet. Move strong-fit leads here after review.',
  closed: 'No closed leads yet. Move won or closed opportunities here.',
}

function initialVisibleByStage(): Record<string, number> {
  return Object.fromEntries(
    pipelineStages.map((stage) => [stage.id, PIPELINE_STAGE_PAGE_SIZE])
  )
}

type ScoreTier = { label: string; className: string }

function scoreTierForLead(lead: LeadData): ScoreTier {
  const score = lead.score
  if (score == null || Number.isNaN(Number(score))) {
    return {
      label: 'Needs Review',
      className: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
    }
  }
  if (score === 0 && !lead.scoreBreakdown) {
    return {
      label: 'Needs Review',
      className: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
    }
  }
  if (score >= 75) {
    return {
      label: 'Hot',
      className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    }
  }
  if (score >= 50) {
    return {
      label: 'Warm',
      className: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    }
  }
  return {
    label: 'Low Fit',
    className: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
  }
}

type CsvPreviewRow = {
  row: number
  email: string
  name?: string
  status: 'ok' | 'duplicate' | 'invalid' | string
  reason?: string
}

type CsvPreviewState = {
  fileName: string
  totalRows: number
  validRows: number
  duplicateRows: number
  invalidRows: number
  rows: CsvPreviewRow[]
}

function buildCsvPreviewState(
  file: File,
  preview: { rows?: CsvPreviewRow[]; summary?: { ok?: number; duplicate?: number; invalid?: number; total?: number } }
): CsvPreviewState {
  const rows = preview.rows || []
  const okRows = preview.summary?.ok ?? rows.filter((row) => row.status === 'ok').length
  const duplicateRows = preview.summary?.duplicate ?? rows.filter((row) => row.status === 'duplicate').length
  const invalidRows = preview.summary?.invalid ?? rows.filter((row) => row.status === 'invalid').length
  const totalRows = preview.summary?.total ?? rows.length

  return {
    fileName: file.name,
    totalRows,
    validRows: okRows + duplicateRows,
    duplicateRows,
    invalidRows,
    rows,
  }
}

/** O(n) single pass; maps legacy stages (e.g. booked) into canonical columns. */
function groupLeadsByStage(items: LeadData[]) {
  const grouped: Record<string, LeadData[]> = {}
  pipelineStages.forEach(stage => {
    grouped[stage.id] = []
  })
  items.forEach(lead => {
    const col = pipelineColumnForStage(lead.stage)
    if (grouped[col]) grouped[col].push(lead)
  })
  return grouped
}

export const CRM: React.FC = () => {
  const [leads, setLeads] = useState<LeadData[]>([])
  const [pipeline, setPipeline] = useState<Record<string, LeadData[]>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<{ type: 'error' | 'warning' | 'info' | 'success'; title: string; message: string } | null>(null)
  const [showAddLeadModal, setShowAddLeadModal] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStage, setFilterStage] = useState('all')
  const [newLead, setNewLead] = useState({
    id: '',
    name: '',
    email: '',
    phone: '',
    company: '',
    stage: 'new',
    score: 0,
    lastContact: new Date().toISOString(),
    source: 'web'
  })
  const [isExporting, setIsExporting] = useState(false)
  const [traceLead, setTraceLead] = useState<LeadData | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [importResult, setImportResult] = useState<{
    imported: number
    created: number
    updated: number
    skipped: number
    skipped_details: Array<{ row: number; reason: string; email?: string }>
  } | null>(null)
  const [isPreviewingImport, setIsPreviewingImport] = useState(false)
  const [pendingImportFile, setPendingImportFile] = useState<File | null>(null)
  const [csvPreview, setCsvPreview] = useState<CsvPreviewState | null>(null)
  const [tableLeads, setTableLeads] = useState<LeadData[]>([])
  const [tableLoading, setTableLoading] = useState(false)
  const [tablePagination, setTablePagination] = useState({
    total_count: 0,
    returned_count: 0,
    limit: TABLE_PAGE_SIZE,
    offset: 0,
    has_more: false,
  })
  const [tableOffset, setTableOffset] = useState(0)
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [visibleByStage, setVisibleByStage] = useState<Record<string, number>>(initialVisibleByStage)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { addToast } = useToast()

  const fetchTableLeads = useCallback(async (offset: number, q: string, stage: string) => {
    setTableLoading(true)
    try {
      const result = await apiClient.getLeadsPage({
        limit: TABLE_PAGE_SIZE,
        offset,
        q: q.trim() || undefined,
        stage: stage !== 'all' ? stage : undefined,
      })
      setTableLeads(result.leads)
      setTablePagination(result.pagination)
    } catch (err) {
      setError(getUserFriendlyError(err))
    } finally {
      setTableLoading(false)
    }
  }, [])

  const refreshCrmData = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const leadsData = await apiClient.getLeads()
      setLeads(leadsData)
      setPipeline(groupLeadsByStage(leadsData))
    } catch (err) {
      setError(getUserFriendlyError(err))
    } finally {
      setIsLoading(false)
    }

    await fetchTableLeads(tableOffset, debouncedSearch, filterStage)
  }, [fetchTableLeads, tableOffset, debouncedSearch, filterStage])

  const handleAddLead = async () => {
    if (!newLead.name || !newLead.email) {
      setError({
        type: 'warning',
        title: 'Missing Information',
        message: 'Name and email are required fields.'
      })
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      await apiClient.addLead(newLead)
      setNewLead({ 
        id: '', 
        name: '', 
        email: '', 
        phone: '', 
        company: '', 
        stage: 'new', 
        score: 0, 
        lastContact: new Date().toISOString(), 
        source: 'web' 
      })
      setShowAddLeadModal(false)
      addToast({ type: 'success', title: 'Lead Added', message: 'The new lead has been added to your CRM.' })
      setError(null)
      refreshCrmData()
    } catch (error) {
      // Failed to add lead
      setError(getUserFriendlyError(error))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    const loadPipeline = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const leadsData = await apiClient.getLeads()
        if (cancelled) return
        setLeads(leadsData)
        setPipeline(groupLeadsByStage(leadsData))
      } catch (err) {
        if (!cancelled) setError(getUserFriendlyError(err))
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }
    void loadPipeline()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(searchTerm), 300)
    return () => window.clearTimeout(timer)
  }, [searchTerm])

  useEffect(() => {
    setTableOffset(0)
    setVisibleByStage(initialVisibleByStage())
  }, [debouncedSearch, filterStage])

  useEffect(() => {
    void fetchTableLeads(tableOffset, debouncedSearch, filterStage)
  }, [tableOffset, debouncedSearch, filterStage, fetchTableLeads])

  const handleExportCsv = async () => {
    setIsExporting(true)
    setError(null)
    try {
      await apiClient.exportLeadsCsv()
      addToast({ type: 'success', title: 'Export complete', message: 'leads.csv downloaded.' })
    } catch (err) {
      setError(getUserFriendlyError(err))
    } finally {
      setIsExporting(false)
    }
  }

  const handleDownloadTemplate = () => {
    const template = 'email,name,phone,source\njohn@example.com,John Doe,1234567890,website\njane@example.com,Jane Smith,9876543210,facebook'
    const blob = new Blob([template], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'leads-template.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    addToast({ type: 'success', title: 'Template downloaded', message: 'Fill in your leads and import the CSV.' })
  }

  const handleImportCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setIsPreviewingImport(true)
    setError(null)
    setImportResult(null)
    setPendingImportFile(null)
    setCsvPreview(null)
    try {
      const preview = await apiClient.previewLeadsCsv(file)
      setPendingImportFile(file)
      setCsvPreview(buildCsvPreviewState(file, preview))
    } catch (err) {
      setError(getUserFriendlyError(err))
    } finally {
      setIsPreviewingImport(false)
    }
  }

  const handleCancelImportCsv = () => {
    setPendingImportFile(null)
    setCsvPreview(null)
    setError(null)
  }

  const handleConfirmImportCsv = async () => {
    if (!pendingImportFile || !csvPreview) return

    if (csvPreview.invalidRows > 0) {
      setError({
        type: 'warning',
        title: 'Fix CSV errors first',
        message: 'This CSV has invalid rows. Correct the listed errors and upload it again before importing.',
      })
      return
    }

    setIsImporting(true)
    setError(null)
    setImportResult(null)
    try {
      const result = await apiClient.importLeadsCsv(pendingImportFile)
      setImportResult({
        imported: result.imported,
        created: result.created,
        updated: result.updated,
        skipped: result.skipped,
        skipped_details: result.skipped_details || []
      })
      setPendingImportFile(null)
      setCsvPreview(null)
      addToast({
        type: 'success',
        title: 'Import complete',
        message: `${result.imported} leads imported${result.skipped ? `, ${result.skipped} skipped` : ''}.`
      })
      refreshCrmData()
    } catch (err) {
      setError(getUserFriendlyError(err))
    } finally {
      setIsImporting(false)
    }
  }

  const handleDragEnd = async (result: DropResult) => {
    if (!result.destination) return

    const sourceStage = result.source.droppableId
    const destStage = result.destination.droppableId
    if (!result.draggableId || (sourceStage === destStage && result.source.index === result.destination.index)) {
      return
    }

    const previous = JSON.parse(JSON.stringify(pipeline))
    setPipeline(prev => {
      if (!result.destination) return prev
      const updated = { ...prev }
      const sourceItems = Array.from(updated[sourceStage] || [])
      const destItems = sourceStage === destStage ? sourceItems : Array.from(updated[destStage] || [])
      const [moved] = sourceItems.splice(result.source.index, 1)
      if (!moved) return prev
      moved.stage = destStage
      destItems.splice(result.destination.index, 0, moved)

      updated[sourceStage] = sourceStage === destStage ? destItems : sourceItems
      updated[destStage] = destItems
      return updated
    })

    try {
      await apiClient.updateLeadStage(result.draggableId, destStage)
      addToast({ type: 'success', title: 'Lead Updated', message: 'Lead stage updated successfully' })
      refreshCrmData()
    } catch (err) {
      setPipeline(previous)
      addToast({ type: 'error', title: 'Update Failed', message: 'Failed to update lead. Please try again.' })
    }
  }

  const loadMorePipelineStage = (stageId: string) => {
    setVisibleByStage((prev) => ({
      ...prev,
      [stageId]: (prev[stageId] ?? PIPELINE_STAGE_PAGE_SIZE) + PIPELINE_STAGE_PAGE_SIZE,
    }))
  }

  const tableRangeStart =
    tablePagination.total_count === 0 ? 0 : tableOffset + 1
  const tableRangeEnd =
    tablePagination.total_count === 0
      ? 0
      : Math.min(tableOffset + tableLeads.length, tablePagination.total_count)

  // Optimized: memoize stats calculations
  const leadStats = useMemo(() => ({
    total: leads.length,
    qualified: leads.filter(lead => lead.stage === 'qualified').length,
    contacted: leads.filter(lead => lead.stage === 'contacted').length,
  }), [leads])

  const getStageColor = (stage: string) => {
    switch (stage) {
      case 'new':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
      case 'qualified':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
      case 'contacted':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
      case 'replied':
        return 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300'
      case 'closed':
      case 'booked':
      case 'converted':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    }
  }

  /** Backend stores lead score as 0–100 (`LeadScoringService`). */
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400'
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const scoreBreakdownSummary = (lead: LeadData): string | null => {
    const b = lead.scoreBreakdown
    if (!b) return null
    const keys = ['identity', 'intent', 'icp_match', 'engagement', 'lifecycle_modifier']
    const parts = keys
      .filter((k) => typeof b[k] === 'number')
      .map((k) => `${k.replace('_', ' ')} ${b[k]}`)
    if (parts.length === 0) return null
    const suffix = lead.scoringVersion ? ` · ${lead.scoringVersion}` : ''
    return `${parts.join(' · ')}${suffix}`
  }

  return (
    <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-brand-text dark:text-white">CRM - Lead Management</h1>
              <FeatureStatus status={getFeatureStatus('crm')} />
            </div>
            <p className="mt-1 text-sm text-brand-text/70 dark:text-gray-400">
              Track and manage your customer leads and relationships.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleExportCsv}
              disabled={isExporting || leads.length === 0}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium border border-brand-text/20 dark:border-gray-600 text-brand-text dark:text-gray-200 hover:bg-brand-background/50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className="h-4 w-4" />
              <span>{isExporting ? 'Exporting…' : 'Export CSV'}</span>
            </button>
            <input
              ref={fileInputRef}
              id="crm-import-csv-file"
              name="crm_import_csv"
              type="file"
              accept=".csv"
              className="hidden"
              aria-label="Import leads CSV file"
              onChange={handleImportCsv}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isImporting || isPreviewingImport}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium border border-brand-text/20 dark:border-gray-600 text-brand-text dark:text-gray-200 hover:bg-brand-background/50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Upload className="h-4 w-4" />
              <span>{isPreviewingImport ? 'Previewing…' : isImporting ? 'Importing…' : 'Import CSV'}</span>
            </button>
            <button
              onClick={handleDownloadTemplate}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-brand-primary dark:text-brand-accent hover:underline"
            >
              <Download className="h-4 w-4" />
              <span>Download template</span>
            </button>
            <button 
              onClick={() => setShowAddLeadModal(true)}
              className="bg-brand-primary hover:bg-brand-secondary text-white px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center space-x-2"
            >
              <Plus className="h-4 w-4" />
              <span>Add Lead</span>
            </button>
          </div>
        </div>

        {csvPreview !== null && (
          <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 p-4 text-sm">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="font-medium text-blue-900 dark:text-blue-100">CSV preview ready: {csvPreview.fileName}</p>
                <p className="mt-1 text-blue-800 dark:text-blue-200">
                  Review the summary below, then confirm when you are ready to import. Duplicate rows are importable and will follow the server import policy.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleConfirmImportCsv}
                  disabled={isImporting || csvPreview.invalidRows > 0}
                  className="rounded-lg bg-brand-primary px-4 py-2 font-medium text-white transition-colors hover:bg-brand-secondary disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isImporting ? 'Importing…' : 'Confirm import'}
                </button>
                <button
                  type="button"
                  onClick={handleCancelImportCsv}
                  disabled={isImporting}
                  className="rounded-lg border border-brand-text/20 px-4 py-2 font-medium text-brand-text transition-colors hover:bg-white/60 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <div className="rounded-md bg-white/70 p-3 dark:bg-gray-900/40">
                <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Total rows</p>
                <p className="mt-1 text-lg font-semibold text-blue-950 dark:text-blue-50">{csvPreview.totalRows}</p>
              </div>
              <div className="rounded-md bg-white/70 p-3 dark:bg-gray-900/40">
                <p className="text-xs uppercase tracking-wide text-green-700 dark:text-green-300">Valid rows</p>
                <p className="mt-1 text-lg font-semibold text-green-800 dark:text-green-100">{csvPreview.validRows}</p>
              </div>
              <div className="rounded-md bg-white/70 p-3 dark:bg-gray-900/40">
                <p className="text-xs uppercase tracking-wide text-amber-700 dark:text-amber-300">Duplicate rows</p>
                <p className="mt-1 text-lg font-semibold text-amber-800 dark:text-amber-100">{csvPreview.duplicateRows}</p>
              </div>
              <div className="rounded-md bg-white/70 p-3 dark:bg-gray-900/40">
                <p className="text-xs uppercase tracking-wide text-red-700 dark:text-red-300">Invalid rows</p>
                <p className="mt-1 text-lg font-semibold text-red-800 dark:text-red-100">{csvPreview.invalidRows}</p>
              </div>
            </div>
            {csvPreview.invalidRows > 0 && (
              <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200">
                <p className="font-medium">Import blocked until invalid rows are fixed.</p>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {csvPreview.rows.filter((row) => row.status === 'invalid').slice(0, 5).map((row) => (
                    <li key={`${row.row}-${row.email || row.reason || 'invalid'}`}>
                      Row {row.row}: {row.reason || 'Invalid row'}{row.email ? ` (${row.email})` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {importResult !== null && (
          <div className="rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 p-4 text-sm">
            <p className="font-medium text-green-800 dark:text-green-200">
              ✔ {importResult.imported} leads imported
              {importResult.created !== undefined && importResult.updated !== undefined && (
                <span className="text-green-700 dark:text-green-300"> ({importResult.created} new, {importResult.updated} updated)</span>
              )}
            </p>
            {importResult.skipped > 0 && (
              <p className="mt-1 text-amber-700 dark:text-amber-200">
                ⚠ {importResult.skipped} skipped (invalid or missing email)
              </p>
            )}
          </div>
        )}

        {/* Error Display */}
        {error && (
          <ErrorMessage
            type={error.type}
            title={error.title}
            message={error.message}
            onDismiss={() => setError(null)}
          />
        )}


      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Users className="h-6 w-6 text-brand-primary" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-brand-text/70 dark:text-gray-400 truncate">Total Leads</dt>
                <dd className="text-2xl font-semibold text-brand-text dark:text-white">{leadStats.total}</dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Star className="h-6 w-6 text-brand-secondary" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-brand-text/70 dark:text-gray-400 truncate">Qualified Leads</dt>
                <dd className="text-2xl font-semibold text-brand-text dark:text-white">
                  {leadStats.qualified}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Mail className="h-6 w-6 text-brand-accent" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-brand-text/70 dark:text-gray-400 truncate">Contacted</dt>
                <dd className="text-2xl font-semibold text-brand-text dark:text-white">
                  {leadStats.contacted}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Building className="h-6 w-6 text-brand-warning" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-brand-text/70 dark:text-gray-400 truncate">Companies</dt>
                <dd className="text-2xl font-semibold text-brand-text dark:text-white">
                  {new Set(leads.map(lead => lead.company)).size}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Kanban Pipeline */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-brand-text dark:text-white">Pipeline board</h3>
            <p className="text-sm text-brand-text/70 dark:text-gray-400">
              Stages match the CRM API (<code className="text-xs">new → contacted → replied → qualified → closed</code>
              ). Inbox leads appear after you connect email and run sync or automations.
            </p>
          </div>
        </div>

        <DragDropContext onDragEnd={handleDragEnd}>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
            {pipelineStages.map((stage) => {
              const stageLeads = pipeline[stage.id] || []
              const stageTotal = stageLeads.length
              const visibleLimit = visibleByStage[stage.id] ?? PIPELINE_STAGE_PAGE_SIZE
              const visibleLeads = stageLeads.slice(0, visibleLimit)
              const hiddenCount = stageTotal - visibleLeads.length

              return (
              <Droppable droppableId={stage.id} key={stage.id}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={`rounded-2xl border ${stage.accent} shadow-sm transition p-4 ${
                      snapshot.isDraggingOver ? 'ring-2 ring-brand-primary/40' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <p className="text-sm uppercase tracking-wide text-brand-text/60 dark:text-gray-400">{stage.title}</p>
                        <p className="text-xs text-brand-text/50 dark:text-gray-500">{stage.helper}</p>
                      </div>
                      <span className="text-sm font-semibold text-brand-text dark:text-white">
                        {stageTotal}
                      </span>
                    </div>
                    {stageTotal > 0 && (
                      <p className="mb-2 text-[11px] text-brand-text/50 dark:text-gray-500">
                        Showing {visibleLeads.length} of {stageTotal}
                      </p>
                    )}
                    <div className="space-y-3 min-h-[120px]">
                      {visibleLeads.map((lead, index) => {
                        const tier = scoreTierForLead(lead)
                        return (
                        <Draggable draggableId={lead.id} index={index} key={lead.id}>
                          {(dragProvided, dragSnapshot) => (
                            <div
                              ref={dragProvided.innerRef}
                              {...dragProvided.draggableProps}
                              {...dragProvided.dragHandleProps}
                              className={`rounded-xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 shadow-sm transition ${
                                dragSnapshot.isDragging ? 'ring-2 ring-brand-primary/40' : ''
                              }`}
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0 flex-1">
                                  <p className="font-semibold text-brand-text dark:text-white truncate">{lead.name}</p>
                                  <p className="text-xs text-brand-text/60 dark:text-gray-400 truncate">{lead.email}</p>
                                </div>
                                <div
                                  className="flex shrink-0 flex-col items-end gap-1"
                                  title={scoreBreakdownSummary(lead) ?? undefined}
                                >
                                  <span className={`whitespace-nowrap text-xs font-semibold px-2 py-1 rounded-full ${tier.className}`}>
                                    {tier.label}
                                  </span>
                                  <span className={`text-[11px] font-medium ${getScoreColor(lead.score)}`}>
                                    {lead.score}/100
                                  </span>
                                </div>
                              </div>
                              <div className="mt-3 flex items-center justify-between text-xs text-brand-text/60 dark:text-gray-400">
                                <div className="flex items-center gap-1">
                                  <Mail className="h-3.5 w-3.5" />
                                  {lead.source || 'Inbox'}
                                </div>
                                <div className="flex items-center gap-1">
                                  <Activity className="h-3.5 w-3.5" />
                                  {new Date(lead.lastContact).toLocaleDateString()}
                                </div>
                              </div>
                              <button
                                type="button"
                                className="mt-2 inline-flex w-full items-center justify-center gap-1 rounded-lg border border-brand-text/15 py-1.5 text-[11px] font-medium text-brand-primary hover:bg-brand-primary/5 dark:border-gray-600 dark:text-brand-accent"
                                onMouseDown={(e) => e.stopPropagation()}
                                onPointerDown={(e) => e.stopPropagation()}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setTraceLead(lead)
                                }}
                              >
                                <GitBranch className="h-3 w-3" />
                                View trace
                              </button>
                            </div>
                          )}
                        </Draggable>
                      )})}
                      {provided.placeholder}
                      {stageTotal === 0 && (
                        <div className="rounded-xl border border-dashed border-brand-text/20 dark:border-gray-700 p-4 text-center text-sm text-brand-text/60 dark:text-gray-400">
                          {pipelineEmptyCopy[stage.id]}
                        </div>
                      )}
                    </div>
                    {hiddenCount > 0 && (
                      <button
                        type="button"
                        onClick={() => loadMorePipelineStage(stage.id)}
                        className="mt-3 w-full rounded-lg border border-brand-text/15 py-2 text-xs font-medium text-brand-primary hover:bg-brand-primary/5 dark:border-gray-600 dark:text-brand-accent"
                      >
                        Load more ({hiddenCount} remaining)
                      </button>
                    )}
                  </div>
                )}
              </Droppable>
            )})}
          </div>
        </DragDropContext>
      </div>

      {/* Filters and Search */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
          <div className="flex-1 max-w-lg">
            <label htmlFor="crm-leads-search" className="sr-only">
              Search leads
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-brand-text/60" />
              </div>
              <input
                id="crm-leads-search"
                name="q"
                type="text"
                className="bg-white dark:bg-gray-800 text-brand-text dark:text-white placeholder-brand-text/60 dark:placeholder-gray-400 border border-brand-text/20 dark:border-gray-600 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 pl-10 w-full"
                placeholder="Search leads by name, email, or company..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-brand-text/60" aria-hidden />
              <label htmlFor="crm-filter-stage" className="sr-only">
                Filter by pipeline stage
              </label>
              <select
                id="crm-filter-stage"
                name="filter_stage"
                className="bg-white dark:bg-gray-800 text-brand-text dark:text-white border border-brand-text/20 dark:border-gray-600 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2"
                value={filterStage}
                onChange={(e) => setFilterStage(e.target.value)}
              >
                <option value="all">All Stages</option>
                {pipelineStages.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.title}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-brand-text dark:text-white">
            Leads ({tablePagination.total_count})
          </h3>
        </div>
        
        {tableLoading && tableLeads.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary"></div>
          </div>
        ) : (
          <TableScroll size="medium" label="Leads table">
            <table className="w-full divide-y divide-brand-text/10 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-brand-text/70 dark:text-gray-400 uppercase tracking-wider">
                    Lead
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-brand-text/70 dark:text-gray-400 uppercase tracking-wider">
                    Company
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-brand-text/70 dark:text-gray-400 uppercase tracking-wider">
                    Stage
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-brand-text/70 dark:text-gray-400 uppercase tracking-wider">
                    Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-brand-text/70 dark:text-gray-400 uppercase tracking-wider">
                    Last Contact
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-brand-text/70 dark:text-gray-400 uppercase tracking-wider">
                    Source
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-brand-text/70 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-brand-text/10 dark:divide-gray-700">
                {tableLeads.map((lead) => {
                  const tier = scoreTierForLead(lead)
                  return (
                  <tr key={lead.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10">
                          <div className="h-10 w-10 rounded-full bg-brand-accent/20 flex items-center justify-center">
                            <span className="text-sm font-medium text-brand-primary">
                              {lead.name.split(' ').map(n => n[0]).join('')}
                            </span>
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-brand-text dark:text-white">{lead.name}</div>
                          <div className="text-sm text-brand-text/70 dark:text-gray-400">{lead.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-brand-text dark:text-white">{lead.company}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStageColor(lead.stage)}`}>
                        {lead.stage}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div
                        className="flex flex-col gap-1"
                        title={scoreBreakdownSummary(lead) ?? undefined}
                      >
                        <span className={`text-sm font-medium ${getScoreColor(lead.score)}`}>
                          {lead.score}/100
                        </span>
                        <span className={`inline-flex w-fit items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${tier.className}`}>
                          {tier.label}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-brand-text/70 dark:text-gray-400">
                      {lead.lastContact}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-brand-text/70 dark:text-gray-400">
                      {lead.source}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 rounded-md border border-brand-text/15 px-2 py-1 text-xs font-medium text-brand-primary hover:bg-brand-primary/5 dark:border-gray-600 dark:text-brand-accent"
                        onClick={() => setTraceLead(lead)}
                      >
                        <GitBranch className="h-3.5 w-3.5" />
                        View trace
                      </button>
                    </td>
                  </tr>
                )})}
              </tbody>
            </table>
            
            {tableLeads.length === 0 && !tableLoading && (
              <EmptyState 
                type="crm" 
                onAction={searchTerm || filterStage !== 'all' ? undefined : () => {
                  setShowAddLeadModal(true)
                }}
              />
            )}

            <div className="flex flex-col gap-3 border-t border-gray-200 px-6 py-4 dark:border-gray-700 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-brand-text/70 dark:text-gray-400">
                Showing {tableRangeStart}–{tableRangeEnd} of {tablePagination.total_count}
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  aria-label="Previous"
                  disabled={tableOffset === 0 || tableLoading}
                  onClick={() => setTableOffset((prev) => Math.max(0, prev - TABLE_PAGE_SIZE))}
                  className="rounded-lg border border-brand-text/20 px-4 py-2 text-sm font-medium text-brand-text transition-colors hover:bg-brand-background/50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
                >
                  Previous
                </button>
                <button
                  type="button"
                  aria-label="Next"
                  disabled={!tablePagination.has_more || tableLoading}
                  onClick={() => setTableOffset((prev) => prev + TABLE_PAGE_SIZE)}
                  className="rounded-lg border border-brand-text/20 px-4 py-2 text-sm font-medium text-brand-text transition-colors hover:bg-brand-background/50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
                >
                  Next
                </button>
              </div>
            </div>
          </TableScroll>
        )}
      </div>

      <LeadTraceModal
        lead={traceLead}
        open={traceLead !== null}
        onClose={() => setTraceLead(null)}
      />

      {/* Add Lead Modal */}
      {showAddLeadModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border border-gray-200 dark:border-gray-700 w-96 shadow-lg rounded-md bg-white dark:bg-gray-800">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-brand-text dark:text-white mb-4">Add New Lead</h3>
              
              <div className="space-y-4">
                <div>
                  <label htmlFor="new-lead-name" className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-1">
                    Name *
                  </label>
                  <input
                    id="new-lead-name"
                    name="new_lead_name"
                    type="text"
                    className="bg-white dark:bg-gray-800 text-brand-text dark:text-white placeholder-brand-text/60 dark:placeholder-gray-400 border border-brand-text/20 dark:border-gray-600 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
                    value={newLead.name}
                    onChange={(e) => setNewLead({...newLead, name: e.target.value})}
                    placeholder="Enter lead name"
                  />
                </div>
                
                <div>
                  <label htmlFor="new-lead-email" className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-1">
                    Email *
                  </label>
                  <input
                    id="new-lead-email"
                    name="email"
                    type="email"
                    className="bg-white dark:bg-gray-800 text-brand-text dark:text-white placeholder-brand-text/60 dark:placeholder-gray-400 border border-brand-text/20 dark:border-gray-600 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
                    value={newLead.email}
                    onChange={(e) => setNewLead({...newLead, email: e.target.value})}
                    placeholder="Enter email address"
                  />
                </div>
                
                <div>
                  <label htmlFor="new-lead-phone" className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-1">
                    Phone
                  </label>
                  <input
                    id="new-lead-phone"
                    name="tel"
                    type="tel"
                    className="bg-white dark:bg-gray-800 text-brand-text dark:text-white placeholder-brand-text/60 dark:placeholder-gray-400 border border-brand-text/20 dark:border-gray-600 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
                    value={newLead.phone}
                    onChange={(e) => setNewLead({...newLead, phone: e.target.value})}
                    placeholder="Enter phone number"
                  />
                </div>
                
                <div>
                  <label htmlFor="new-lead-company" className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-1">
                    Company
                  </label>
                  <input
                    id="new-lead-company"
                    name="organization"
                    type="text"
                    className="bg-white dark:bg-gray-800 text-brand-text dark:text-white placeholder-brand-text/60 dark:placeholder-gray-400 border border-brand-text/20 dark:border-gray-600 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
                    value={newLead.company}
                    onChange={(e) => setNewLead({...newLead, company: e.target.value})}
                    placeholder="Enter company name"
                  />
                </div>
                
                <div>
                  <label htmlFor="new-lead-source" className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-1">
                    Source
                  </label>
                  <select
                    id="new-lead-source"
                    name="lead_source"
                    className="bg-white text-brand-text border border-brand-text/20 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
                    value={newLead.source}
                    onChange={(e) => setNewLead({...newLead, source: e.target.value})}
                  >
                    <option value="web">Web</option>
                    <option value="email">Email</option>
                    <option value="referral">Referral</option>
                    <option value="social">Social Media</option>
                    <option value="phone">Phone</option>
                  </select>
                </div>
              </div>
              
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowAddLeadModal(false)}
                  className="px-4 py-2 text-sm font-medium text-brand-text dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-200 dark:border-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddLead}
                  disabled={isLoading || !newLead.name || !newLead.email}
                  className="px-4 py-2 text-sm font-medium text-white bg-brand-primary hover:bg-brand-secondary disabled:opacity-50 disabled:cursor-not-allowed rounded-lg"
                >
                  {isLoading ? 'Adding...' : 'Add Lead'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
