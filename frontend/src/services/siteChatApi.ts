/**
 * First-party Fikiri marketing site chat API (no tenant API key).
 */

import { config } from '../config'
import type {
  FikiriSiteChatHandoff,
  FikiriSiteChatIntake,
  FikiriSiteChatMessageData,
  FikiriSiteChatSessionData,
  FikiriSiteChatSource,
  FikiriSiteLeadAssessment,
} from '../types/fikiriSiteBot'

export type {
  FikiriSiteChatHandoff as SiteChatHandoff,
  FikiriSiteChatIntake as SiteChatIntake,
  FikiriSiteChatMessageData as SiteChatMessageData,
  FikiriSiteChatSessionData as SiteChatSessionData,
  FikiriSiteChatSource as SiteChatSource,
  FikiriSiteLeadAssessment as SiteChatLeadAssessment,
}

const SITE_CHAT_BASE = `${config.apiUrl.replace(/\/+$/, '')}/site/chat`

interface ApiEnvelope<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

async function postJson<T>(path: string, body?: Record<string, unknown>): Promise<T> {
  const response = await fetch(`${SITE_CHAT_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: body ? JSON.stringify(body) : '{}',
  })

  const payload = (await response.json()) as ApiEnvelope<T>
  if (!response.ok || !payload.success || !payload.data) {
    const message = payload.error || payload.message || `Site chat request failed (${response.status})`
    throw new Error(message)
  }
  return payload.data
}

export function siteChatApiBase(): string {
  return SITE_CHAT_BASE
}

export async function startSiteChatSession(): Promise<FikiriSiteChatSessionData> {
  return postJson<FikiriSiteChatSessionData>('/session/start')
}

export async function sendSiteChatMessage(
  sessionId: string,
  message: string
): Promise<FikiriSiteChatMessageData> {
  return postJson<FikiriSiteChatMessageData>('/message', {
    session_id: sessionId,
    message,
  })
}

export function handoffPath(handoff: FikiriSiteChatHandoff): string | null {
  if (!handoff.applicable || !handoff.secondary) return null
  return handoff.secondary
}
