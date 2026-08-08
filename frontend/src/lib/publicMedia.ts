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
    /** Approved production hero plates — compositing only; do not recreate. */
    hero: {
      desktop: publicAsset('brand/hero/fikiri-hero-desktop.png'),
      mobile: publicAsset('brand/hero/fikiri-hero-mobile.png'),
      /**
       * Baked black RGB plate (no alpha). Do not overlay until a transparent export exists.
       * Path kept for when asset cleanup lands.
       */
      tripleF: publicAsset('brand/hero/fikiri-triple-f.png'),
    },
    bento: {
      email: inImages('email.png'),
      /** Person + tablet (lifestyle) — not the in-app UI snapshot; that’s `tab.crm` below Features. */
      crm: inImages('landing-bento-crm.png'),
      automation: inImages('automation.png'),
    },
    tab: {
      dashboard: inImages('preview-tab-dashboard.png'),
      inbox: inImages('preview-tab-inbox.webp'),
      /** In-app UI snapshot for the tab strip + large preview (below Features). */
      crm: inImages('preview-tab-crm.png'),
      automations: inImages('preview-tab-automations.png'),
    },
  },
} as const
