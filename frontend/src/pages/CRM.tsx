import React, { useState, useEffect } from 'react'
import { Users, Mail, Phone, Building, Calendar, Star, Filter, Search, Plus } from 'lucide-react'
import { apiClient, LeadData } from '../services/apiClient'
import { EmptyState } from '../components/EmptyState'
import { ErrorMessage, getUserFriendlyError } from '../components/ErrorMessage'
import { FeatureStatus, getFeatureStatus } from '../components/FeatureStatus'

export const CRM: React.FC = () => {
  const [leads, setLeads] = useState<LeadData[]>([])
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
      setError({
        type: 'success',
        title: 'Lead Added Successfully',
        message: 'The new lead has been added to your CRM.'
      })
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
    } catch (error) {
      // Failed to fetch leads
      setError(getUserFriendlyError(error))
    } finally {
      setIsLoading(false)
    }
  }

  const filteredLeads = leads.filter(lead => {
    const matchesSearch = lead.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         lead.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         lead.company.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesStage = filterStage === 'all' || lead.stage === filterStage
    
    return matchesSearch && matchesStage
  })

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
              <h1 className="text-2xl font-bold text-gray-900">CRM - Lead Management</h1>
              <FeatureStatus status={getFeatureStatus('crm')} />
            </div>
            <p className="mt-1 text-sm text-gray-600">
              Track and manage your customer leads and relationships.
            </p>
          </div>
          <button 
            onClick={() => setShowAddLeadModal(true)}
            className="btn-primary flex items-center space-x-2"
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
        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Users className="h-6 w-6 text-gray-400" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Total Leads</dt>
                <dd className="text-2xl font-semibold text-gray-900">{leads.length}</dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Star className="h-6 w-6 text-gray-400" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Qualified Leads</dt>
                <dd className="text-2xl font-semibold text-gray-900">
                  {leads.filter(lead => lead.stage === 'qualified').length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Mail className="h-6 w-6 text-gray-400" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Contacted</dt>
                <dd className="text-2xl font-semibold text-gray-900">
                  {leads.filter(lead => lead.stage === 'contacted').length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Building className="h-6 w-6 text-gray-400" />
            </div>
            <div className="ml-4 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Companies</dt>
                <dd className="text-2xl font-semibold text-gray-900">
                  {new Set(leads.map(lead => lead.company)).size}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="card">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
          <div className="flex-1 max-w-lg">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                className="input-field pl-10"
                placeholder="Search leads by name, email, or company..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <select
                className="input-field"
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
      <div className="card">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Leads ({filteredLeads.length})</h3>
        </div>
        
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Lead
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Company
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Stage
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Contact
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredLeads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10">
                          <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                            <span className="text-sm font-medium text-blue-600">
                              {lead.name.split(' ').map(n => n[0]).join('')}
                            </span>
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{lead.name}</div>
                          <div className="text-sm text-gray-500">{lead.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{lead.company}</div>
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
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {lead.lastContact}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
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
                  // Add lead functionality would go here
                  // Add lead clicked
                }}
              />
            )}
          </div>
        )}
      </div>

      {/* Add Lead Modal */}
      {showAddLeadModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Add New Lead</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Name *
                  </label>
                  <input
                    type="text"
                    className="input-field"
                    value={newLead.name}
                    onChange={(e) => setNewLead({...newLead, name: e.target.value})}
                    placeholder="Enter lead name"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email *
                  </label>
                  <input
                    type="email"
                    className="input-field"
                    value={newLead.email}
                    onChange={(e) => setNewLead({...newLead, email: e.target.value})}
                    placeholder="Enter email address"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Phone
                  </label>
                  <input
                    type="tel"
                    className="input-field"
                    value={newLead.phone}
                    onChange={(e) => setNewLead({...newLead, phone: e.target.value})}
                    placeholder="Enter phone number"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Company
                  </label>
                  <input
                    type="text"
                    className="input-field"
                    value={newLead.company}
                    onChange={(e) => setNewLead({...newLead, company: e.target.value})}
                    placeholder="Enter company name"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Source
                  </label>
                  <select
                    className="input-field"
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
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddLead}
                  disabled={isLoading || !newLead.name || !newLead.email}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-md"
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
