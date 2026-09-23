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
       * One-shot seed→canopy entrance. Resting state remains the approved plates above.
       */
      growth: publicAsset('media/baobab-growth-hero.mp4'),
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
      /** Retina product previews (2× Lanczos export) — workspace strip below Features. */
      dashboard: {
        webp: inImages('preview-tabs/dashboard@2x.webp'),
        jpg: inImages('preview-tabs/dashboard@2x.jpg'),
      },
      inbox: {
        webp: inImages('preview-tabs/inbox@2x.webp'),
        jpg: inImages('preview-tabs/inbox@2x.jpg'),
      },
      crm: {
        webp: inImages('preview-tabs/crm@2x.webp'),
        jpg: inImages('preview-tabs/crm@2x.jpg'),
      },
      automations: {
        webp: inImages('preview-tabs/automations@2x.webp'),
        jpg: inImages('preview-tabs/automations@2x.jpg'),
      },
    },
  },
} as const
