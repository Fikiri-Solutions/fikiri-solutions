import React, { useState, useEffect, useMemo } from 'react'
import { Users, Mail, Phone, Building, Calendar, Star, Filter, Search, Plus, Activity, Zap } from 'lucide-react'
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd'
import { apiClient, LeadData } from '../services/apiClient'
import { EmptyState } from '../components/EmptyState'
import { ErrorMessage, getUserFriendlyError } from '../components/ErrorMessage'
import { FeatureStatus, getFeatureStatus } from '../components/FeatureStatus'
import { useToast } from '../components/Toast'

const pipelineStages = [
  { id: 'new', title: 'New Leads', accent: 'border-blue-200 bg-blue-50 dark:bg-blue-900/30', helper: 'Synced from Gmail & forms' },
  { id: 'contacted', title: 'Contacted', accent: 'border-amber-200 bg-amber-50 dark:bg-amber-900/30', helper: 'Awaiting replies' },
  { id: 'qualified', title: 'Qualified', accent: 'border-emerald-200 bg-emerald-50 dark:bg-emerald-900/20', helper: 'Ready for meetings' },
  { id: 'booked', title: 'Booked', accent: 'border-purple-200 bg-purple-50 dark:bg-purple-900/30', helper: 'Won deals' }
] as const

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

  // Optimized: O(n) single pass instead of O(n²) nested loops
  const groupLeadsByStage = (items: LeadData[]) => {
    const grouped: Record<string, LeadData[]> = {}
    // Initialize all stages
    pipelineStages.forEach(stage => {
      grouped[stage.id] = []
    })
    // Single pass through items - O(n)
    items.forEach(lead => {
      if (grouped[lead.stage]) {
        grouped[lead.stage].push(lead)
      }
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
        return 'bg-blue-100 text-blue-800'
      case 'qualified':
        return 'bg-green-100 text-green-800'
      case 'contacted':
        return 'bg-yellow-100 text-yellow-800'
      case 'converted':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600'
    if (score >= 6) return 'text-yellow-600'
    return 'text-red-600'
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
          <button 
            onClick={() => setShowAddLeadModal(true)}
            className="bg-brand-primary hover:bg-brand-secondary text-white px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center space-x-2"
          >
            <Plus className="h-4 w-4" />
            <span>Add Lead</span>
          </button>
        </div>

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
        <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
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

        <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
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

        <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
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

        <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
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
              Drag leads across stages. Gmail sync automatically feeds the "New" column.
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm text-brand-text/70 dark:text-gray-300">
            <Zap className="h-4 w-4 text-brand-accent" />
            Auto-sync enabled
          </div>
        </div>

        <DragDropContext onDragEnd={handleDragEnd}>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
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
                                  lead.score >= 7 ? 'bg-emerald-100 text-emerald-700' :
                                  lead.score >= 4 ? 'bg-amber-100 text-amber-700' :
                                  'bg-rose-100 text-rose-700'
                                }`}>
                                  {lead.score}/10
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
      <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md p-6 border border-brand-text/10">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
          <div className="flex-1 max-w-lg">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-brand-text/60" />
              </div>
              <input
                type="text"
                className="bg-white text-brand-text placeholder-brand-text/60 border border-brand-text/20 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 pl-10 w-full"
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
                className="bg-white text-brand-text border border-brand-text/20 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2"
                value={filterStage}
                onChange={(e) => setFilterStage(e.target.value)}
              >
                <option value="all">All Stages</option>
                <option value="new">New</option>
                <option value="qualified">Qualified</option>
                <option value="contacted">Contacted</option>
                <option value="converted">Converted</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <div className="bg-brand-background dark:bg-gray-800 rounded-lg shadow-md border border-brand-text/10">
        <div className="px-6 py-4 border-b border-brand-text/10">
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
                      <div className={`text-sm font-medium ${getScoreColor(lead.score)}`}>
                        {lead.score}/10
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-brand-text/70 dark:text-gray-400">
                      {lead.lastContact}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-brand-text/70 dark:text-gray-400">
                      {lead.source}
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

      {/* Add Lead Modal */}
      {showAddLeadModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border border-brand-text/10 w-96 shadow-lg rounded-md bg-brand-background dark:bg-gray-800">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-brand-text dark:text-white mb-4">Add New Lead</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-brand-text dark:text-gray-300 mb-1">
                    Name *
                  </label>
                  <input
                    type="text"
                    className="bg-white text-brand-text placeholder-brand-text/60 border border-brand-text/20 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
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
                    className="bg-white text-brand-text placeholder-brand-text/60 border border-brand-text/20 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
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
                    className="bg-white text-brand-text placeholder-brand-text/60 border border-brand-text/20 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
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
                    className="bg-white text-brand-text placeholder-brand-text/60 border border-brand-text/20 focus:border-brand-accent focus:ring-brand-accent rounded-lg px-4 py-2 w-full"
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
                  className="px-4 py-2 text-sm font-medium text-brand-text bg-brand-background/50 hover:bg-brand-background/80 border border-brand-text/20 rounded-lg"
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
