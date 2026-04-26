import { publicAsset } from './publicAsset'

const inImages = (file: string) => publicAsset(`images/${file}`)

/**
 * Single source of truth for public-folder marketing and UI preview images.
 * Keep About vs landing artwork on different paths so pages stay visually distinct.
 */
export const publicMedia = {
  about: {
    serviceEmail: inImages('about-service-email.png'),
    serviceCrm: inImages('about-service-crm.png'),
    serviceAi: inImages('about-service-ai.png'),
  },
  landing: {
    bento: {
      email: inImages('email.png'),
      /** Person + tablet (lifestyle) — not the in-app UI snapshot; that’s `tab.crm` below Features. */
      crm: inImages('landing-bento-crm.png'),
      automation: inImages('automation.png'),
    },
    tab: {
      dashboard: inImages('preview-tab-dashboard.png'),
      inbox: inImages('preview-tab-inbox.png'),
      /** In-app UI snapshot for the tab strip + large preview (below Features). */
      crm: inImages('preview-tab-crm.png'),
      automations: inImages('preview-tab-automations.png'),
    },
  },
} as const
