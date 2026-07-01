/** Shared types for the first-party Fikiri marketing site bot API. */

export interface FikiriSiteLeadAssessment {
  score: number
  tier: 'casual' | 'possible' | 'warm' | 'hot' | string
  signals: string[]
  synopsis: string
  recommended_handoff: string | null
}

export interface FikiriSiteChatHandoff {
  applicable: boolean
  primary?: string | null
  secondary?: string | null
  handoff_type?: string | null
}

export interface FikiriSiteChatIntake {
  active?: boolean
  complete?: boolean
  next_slot?: string | null
  filled_core_count?: number
  slots?: Record<string, unknown>
}

export interface FikiriSiteChatSource {
  id: string
  topic?: string
  source_url?: string
  score?: number
}

export interface FikiriSiteChatMessageData {
  schema_version: string
  session_id: string
  mode: string
  response: string
  handoff: FikiriSiteChatHandoff
  lead_intent: Record<string, unknown>
  lead_assessment: FikiriSiteLeadAssessment
  turn_count: number
  grounded?: boolean
  confidence?: number
  sources?: FikiriSiteChatSource[]
  intake?: FikiriSiteChatIntake
}

export interface FikiriSiteChatSessionData {
  schema_version: string
  session_id: string
  welcome: string
}
