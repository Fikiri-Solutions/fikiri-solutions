/**
 * Microsoft Clarity (session replay / heatmaps).
 * Project: Fikiri Solutions — Settings → Overview.
 */
import Clarity from '@microsoft/clarity'

const CLARITY_PROJECT_ID = 'zg88wpa171'

export function initMicrosoftClarity(): void {
  try {
    Clarity.init(CLARITY_PROJECT_ID)
  } catch {
    // Analytics must never break product UX
  }
}
