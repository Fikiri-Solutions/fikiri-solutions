"""
Pipeline Stage UI Component for Fikiri Solutions
Provides drag-and-drop pipeline management interface
"""

import React, { useState, useEffect } from 'react'
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd'
import { 
  Plus, 
  Edit3, 
  Trash2, 
  Users, 
  TrendingUp, 
  Clock, 
  CheckCircle,
  AlertCircle,
  XCircle
} from 'lucide-react'

interface PipelineStage {
  id: string
  name: string
  description: string
  order_index: number
  is_active: boolean
  lead_count: number
  color: string
}

interface Lead {
  id: string
  name: string
  email: string
  company: string
  stage: string
  score: number
  created_at: string
  last_contact: string
}

interface PipelineStageUIProps {
  leads: Lead[]
  onStageChange: (leadId: string, newStage: string) => void
  onLeadClick: (lead: Lead) => void
  onCreateStage: (stage: Omit<PipelineStage, 'id' | 'lead_count'>) => void
  onUpdateStage: (stageId: string, updates: Partial<PipelineStage>) => void
  onDeleteStage: (stageId: string) => void
}

const PipelineStageUI: React.FC<PipelineStageUIProps> = ({
  leads,
  onStageChange,
  onLeadClick,
  onCreateStage,
  onUpdateStage,
  onDeleteStage
}) => {
  const [stages, setStages] = useState<PipelineStage[]>([])
  const [isCreatingStage, setIsCreatingStage] = useState(false)
  const [editingStage, setEditingStage] = useState<string | null>(null)

  // Default pipeline stages
  const defaultStages: PipelineStage[] = [
    {
      id: 'new',
      name: 'New Leads',
      description: 'Recently added leads',
      order_index: 1,
      is_active: true,
      lead_count: 0,
      color: 'bg-blue-500'
    },
    {
      id: 'contacted',
      name: 'Contacted',
      description: 'Leads that have been contacted',
      order_index: 2,
      is_active: true,
      lead_count: 0,
      color: 'bg-yellow-500'
    },
    {
      id: 'qualified',
      name: 'Qualified',
      description: 'Leads that have been qualified',
      order_index: 3,
      is_active: true,
      lead_count: 0,
      color: 'bg-purple-500'
    },
    {
      id: 'proposal',
      name: 'Proposal',
      description: 'Leads with active proposals',
      order_index: 4,
      is_active: true,
      lead_count: 0,
      color: 'bg-orange-500'
    },
    {
      id: 'won',
      name: 'Won',
      description: 'Successfully converted leads',
      order_index: 5,
      is_active: true,
      lead_count: 0,
      color: 'bg-green-500'
    },
    {
      id: 'lost',
      name: 'Lost',
      description: 'Leads that did not convert',
      order_index: 6,
      is_active: true,
      lead_count: 0,
      color: 'bg-red-500'
    }
  ]

  useEffect(() => {
    // Initialize stages with lead counts
    const stagesWithCounts = defaultStages.map(stage => ({
      ...stage,
      lead_count: leads.filter(lead => lead.stage === stage.id).length
    }))
    setStages(stagesWithCounts)
  }, [leads])

  const handleDragEnd = (result: any) => {
    if (!result.destination) return

    const { source, destination, draggableId } = result
    
    // If moving between stages
    if (source.droppableId !== destination.droppableId) {
      const newStage = destination.droppableId
      onStageChange(draggableId, newStage)
    }
  }

  const getStageIcon = (stageId: string) => {
    switch (stageId) {
      case 'new':
        return <Users className="w-5 h-5" />
      case 'contacted':
        return <Clock className="w-5 h-5" />
      case 'qualified':
        return <TrendingUp className="w-5 h-5" />
      case 'proposal':
        return <Edit3 className="w-5 h-5" />
      case 'won':
        return <CheckCircle className="w-5 h-5" />
      case 'lost':
        return <XCircle className="w-5 h-5" />
      default:
        return <AlertCircle className="w-5 h-5" />
    }
  }

  const getStageLeads = (stageId: string) => {
    return leads.filter(lead => lead.stage === stageId)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-100'
    if (score >= 60) return 'text-yellow-600 bg-yellow-100'
    if (score >= 40) return 'text-orange-600 bg-orange-100'
    return 'text-red-600 bg-red-100'
  }

  return (
    <div className="pipeline-stage-ui">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Sales Pipeline
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Manage your leads through the sales process
          </p>
        </div>
        <button
          onClick={() => setIsCreatingStage(true)}
          className="bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-all duration-200"
        >
          <Plus className="w-4 h-4" />
          Add Stage
        </button>
      </div>

      {/* Pipeline Stages */}
      <DragDropContext onDragEnd={handleDragEnd}>
        <div className="flex gap-6 overflow-x-auto pb-4">
          {stages.map((stage) => (
            <div
              key={stage.id}
              className="flex-shrink-0 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
            >
              {/* Stage Header */}
              <div className={`${stage.color} text-white p-4 rounded-t-lg`}>
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    {getStageIcon(stage.id)}
                    <h3 className="font-semibold">{stage.name}</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="bg-white/20 px-2 py-1 rounded-full text-sm">
                      {stage.lead_count}
                    </span>
                    <button
                      onClick={() => setEditingStage(stage.id)}
                      className="hover:bg-white/20 p-1 rounded"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <p className="text-sm opacity-90 mt-1">{stage.description}</p>
              </div>

              {/* Stage Content */}
              <Droppable droppableId={stage.id}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={`p-4 min-h-96 ${
                      snapshot.isDraggingOver ? 'bg-orange-50 dark:bg-orange-900/20' : ''
                    }`}
                  >
                    {getStageLeads(stage.id).map((lead, index) => (
                      <Draggable key={lead.id} draggableId={lead.id} index={index}>
                        {(provided, snapshot) => (
                          <div
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            {...provided.dragHandleProps}
                            onClick={() => onLeadClick(lead)}
                            className={`mb-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg cursor-pointer hover:shadow-md transition-all duration-200 ${
                              snapshot.isDragging ? 'shadow-lg rotate-2' : ''
                            }`}
                          >
                            <div className="flex justify-between items-start mb-2">
                              <h4 className="font-medium text-gray-900 dark:text-white">
                                {lead.name}
                              </h4>
                              <span
                                className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreColor(lead.score)}`}
                              >
                                {lead.score}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                              {lead.company}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-500">
                              {lead.email}
                            </p>
                            <div className="flex justify-between items-center mt-2 text-xs text-gray-500 dark:text-gray-500">
                              <span>Added: {formatDate(lead.created_at)}</span>
                              {lead.last_contact && (
                                <span>Last: {formatDate(lead.last_contact)}</span>
                              )}
                            </div>
                          </div>
                        )}
                      </Draggable>
                    ))}
                    {provided.placeholder}
                    
                    {getStageLeads(stage.id).length === 0 && (
                      <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                        <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                        <p>No leads in this stage</p>
                      </div>
                    )}
                  </div>
                )}
              </Droppable>
            </div>
          ))}
        </div>
      </DragDropContext>

      {/* Create Stage Modal */}
      {isCreatingStage && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">Create New Stage</h3>
            <form onSubmit={(e) => {
              e.preventDefault()
              const formData = new FormData(e.target as HTMLFormElement)
              onCreateStage({
                name: formData.get('name') as string,
                description: formData.get('description') as string,
                order_index: stages.length + 1,
                is_active: true,
                color: formData.get('color') as string
              })
              setIsCreatingStage(false)
            }}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Stage Name</label>
                  <input
                    name="name"
                    type="text"
                    required
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    placeholder="e.g., Initial Contact"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Description</label>
                  <textarea
                    name="description"
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    placeholder="Describe this stage..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Color</label>
                  <select
                    name="color"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  >
                    <option value="bg-blue-500">Blue</option>
                    <option value="bg-green-500">Green</option>
                    <option value="bg-yellow-500">Yellow</option>
                    <option value="bg-orange-500">Orange</option>
                    <option value="bg-purple-500">Purple</option>
                    <option value="bg-red-500">Red</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setIsCreatingStage(false)}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white px-4 py-2 rounded-lg transition-all duration-200"
                >
                  Create Stage
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default PipelineStageUI
