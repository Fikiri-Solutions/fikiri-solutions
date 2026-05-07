import React, { useState, useEffect, useMemo, useRef } from 'react'
import { Users, Mail, Phone, Building, Calendar, Star, Filter, Search, Plus, Activity, Download, Upload, GitBranch } from 'lucide-react'
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd'
import { apiClient, LeadData } from '../services/apiClient'
import { EmptyState } from '../components/EmptyState'
import { ErrorMessage, getUserFriendlyError } from '../components/ErrorMessage'
import { FeatureStatus, getFeatureStatus } from '../components/FeatureStatus'
import { useToast } from '../components/Toast'
import { LeadTraceModal } from '../components/LeadTraceModal'

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
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { addToast } = useToast()

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
      fetchLeads() // Refresh the leads list
    } catch (error) {
      // Failed to add lead
      setError(getUserFriendlyError(error))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchLeads()
  }, [])

  const fetchLeads = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const leadsData = await apiClient.getLeads()
      setLeads(leadsData)
      setPipeline(groupLeadsByStage(leadsData))
    } catch (error) {
      // Failed to fetch leads
      setError(getUserFriendlyError(error))
    } finally {
      setIsLoading(false)
    }
  }

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
    setIsImporting(true)
    setError(null)
    setImportResult(null)
    try {
      const result = await apiClient.importLeadsCsv(file)
      setImportResult({
        imported: result.imported,
        created: result.created,
        updated: result.updated,
        skipped: result.skipped,
        skipped_details: result.skipped_details || []
      })
      addToast({
        type: 'success',
        title: 'Import complete',
        message: `${result.imported} leads imported${result.skipped ? `, ${result.skipped} skipped` : ''}.`
      })
      fetchLeads()
    } catch (err) {
      setError(getUserFriendlyError(err))
    } finally {
      setIsImporting(false)
    }
  }

  // Optimized: O(n) single pass; maps legacy stages (e.g. booked) into canonical columns.
  const groupLeadsByStage = (items: LeadData[]) => {
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
      fetchLeads()
    } catch (err) {
      setPipeline(previous)
      addToast({ type: 'error', title: 'Update Failed', message: 'Failed to update lead. Please try again.' })
    }
  }

  // Optimized: memoize toLowerCase() calls
  // Optimized: memoize filter results and toLowerCase() calls
  const filteredLeads = useMemo(() => {
    if (!searchTerm && filterStage === 'all') return leads
    
    const searchLower = searchTerm.toLowerCase()
    return leads.filter(lead => {
      const matchesSearch = !searchTerm || 
        lead.name.toLowerCase().includes(searchLower) ||
        lead.email.toLowerCase().includes(searchLower) ||
        lead.company.toLowerCase().includes(searchLower)
      
      const matchesStage = filterStage === 'all' || lead.stage === filterStage
      
      return matchesSearch && matchesStage
    })
  }, [leads, searchTerm, filterStage])

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
              type="file"
              accept=".csv"
              className="hidden"
              onChange={handleImportCsv}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isImporting}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium border border-brand-text/20 dark:border-gray-600 text-brand-text dark:text-gray-200 hover:bg-brand-background/50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Upload className="h-4 w-4" />
              <span>{isImporting ? 'Importing…' : 'Import CSV'}</span>
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
            {pipelineStages.map((stage) => (
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
                        {pipeline[stage.id]?.length || 0}
                      </span>
                    </div>
                    <div className="space-y-3 min-h-[120px]">
                      {(pipeline[stage.id] || []).map((lead, index) => (
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
                              <div className="flex items-center justify-between">
                                <div>
                                  <p className="font-semibold text-brand-text dark:text-white">{lead.name}</p>
                                  <p className="text-xs text-brand-text/60 dark:text-gray-400">{lead.email}</p>
                                </div>
                                <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                                  lead.score >= 70 ? 'bg-emerald-100 text-emerald-700' :
                                  lead.score >= 40 ? 'bg-amber-100 text-amber-700' :
                                  'bg-rose-100 text-rose-700'
                                }`} title={scoreBreakdownSummary(lead) ?? undefined}>
                                  {lead.score}/100
                                </span>
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
                      ))}
                      {provided.placeholder}
                      {(pipeline[stage.id] || []).length === 0 && (
                        <div className="rounded-xl border border-dashed border-brand-text/20 dark:border-gray-700 p-4 text-center text-sm text-brand-text/60 dark:text-gray-400">
                          Drop leads here
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </Droppable>
            ))}
          </div>
        </DragDropContext>
      </div>

      {/* Filters and Search */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
          <div className="flex-1 max-w-lg">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-brand-text/60" />
              </div>
              <input
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
              <Filter className="h-4 w-4 text-brand-text/60" />
              <select
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
          <h3 className="text-lg font-medium text-brand-text dark:text-white">Leads ({filteredLeads.length})</h3>
        </div>
        
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary"></div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-brand-text/10 dark:divide-gray-700">
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
                {filteredLeads.map((lead) => (
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
                        className={`text-sm font-medium ${getScoreColor(lead.score)}`}
                        title={scoreBreakdownSummary(lead) ?? undefined}
                      >
                        {lead.score}/100
                      </div>
                      {scoreBreakdownSummary(lead) ? (
                        <div className="mt-0.5 text-[10px] text-brand-text/60 dark:text-gray-500 truncate max-w-[260px]">
                          {scoreBreakdownSummary(lead)}
                        </div>
                      ) : null}
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
                ))}
              </tbody>
            </table>
            
            {filteredLeads.length === 0 && (
              <EmptyState 
                type="crm" 
                onAction={searchTerm || filterStage !== 'all' ? undefined : () => {
                  setShowAddLeadModal(true)
                }}
              />
            )}
          </div>
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
                  <label className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-1">
                    Name *
                  </label>
                  <input
                    type="text"
                    className="bg-white dark:bg-gray-800 text-brand-text dark:text-white placeholder-brand-text/60 dark:placeholder-gray-400 border border-brand-text/20 dark:border-gray-600 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
                    value={newLead.name}
                    onChange={(e) => setNewLead({...newLead, name: e.target.value})}
                    placeholder="Enter lead name"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-1">
                    Email *
                  </label>
                  <input
                    type="email"
                    className="bg-white dark:bg-gray-800 text-brand-text dark:text-white placeholder-brand-text/60 dark:placeholder-gray-400 border border-brand-text/20 dark:border-gray-600 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
                    value={newLead.email}
                    onChange={(e) => setNewLead({...newLead, email: e.target.value})}
                    placeholder="Enter email address"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-1">
                    Phone
                  </label>
                  <input
                    type="tel"
                    className="bg-white dark:bg-gray-800 text-brand-text dark:text-white placeholder-brand-text/60 dark:placeholder-gray-400 border border-brand-text/20 dark:border-gray-600 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
                    value={newLead.phone}
                    onChange={(e) => setNewLead({...newLead, phone: e.target.value})}
                    placeholder="Enter phone number"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-1">
                    Company
                  </label>
                  <input
                    type="text"
                    className="bg-white dark:bg-gray-800 text-brand-text dark:text-white placeholder-brand-text/60 dark:placeholder-gray-400 border border-brand-text/20 dark:border-gray-600 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
                    value={newLead.company}
                    onChange={(e) => setNewLead({...newLead, company: e.target.value})}
                    placeholder="Enter company name"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-1">
                    Source
                  </label>
                  <select
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
