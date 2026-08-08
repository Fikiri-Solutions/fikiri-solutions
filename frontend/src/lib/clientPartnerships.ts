import { publicAsset } from './publicAsset'

export type ClientPartnership = {
  name: string
  url: string
  category: string
  summary: string
  /** Local public path only — never a remote URL */
  logoSrc?: string
  logoAlt: string
  /** Initials used when logoSrc is missing or fails to load */
  fallbackMark: string
  /** Dark plate for white/light marks on black backgrounds */
  darkLogoPlate?: boolean
}

/**
 * Real client partnerships shown on the marketing landing page.
 * Keep copy honest: support/consulting language only — no fake metrics or quotes.
 */
export const clientPartnerships: ClientPartnership[] = [
  {
    name: 'ColorScalez',
    url: 'https://www.colorscalez.com/',
    category: 'Paint Workflow Systems',
    summary:
      'Supporting workflow and product systems for body shops and paint decision-making.',
    logoSrc: publicAsset('images/clients/colorscalez-logo.svg'),
    logoAlt: 'ColorScalez logo',
    fallbackMark: 'CS',
  },
  {
    name: 'Symbolics Technology',
    url: 'https://www.symbolicstech.com/',
    category: 'Cloud, Data & Product Engineering',
    summary:
      'Supporting technology execution across cloud, data, security, and product engineering.',
    logoSrc: publicAsset('images/clients/symbolics-technology-logo.png'),
    logoAlt: 'Symbolics Technology logo',
    fallbackMark: 'ST',
    darkLogoPlate: true,
  },
  {
    name: 'Shinkei Nettowaku Solutions',
    url: 'https://www.shinkeinettowaku.com/',
    category: 'AI Governance & Cloud Security',
    summary:
      'Supporting secure AI, cloud security, compliance, and enterprise modernization work.',
    logoSrc: publicAsset('images/clients/shinkei-nettowaku-logo.svg'),
    logoAlt: 'Shinkei Nettowaku Solutions logo',
    fallbackMark: 'SN',
  },
  {
    name: 'Aim High Hit Higher Enterprise',
    url: 'https://www.aimhighhithigher.com/',
    category: 'Events, Sound & Lighting',
    summary:
      'Supporting workflow and digital systems for an entertainment, sound, and lighting business.',
    logoSrc: publicAsset('images/clients/aim-high-hit-higher-logo.webp'),
    logoAlt: 'Aim High Hit Higher Enterprise logo',
    fallbackMark: 'AH',
    darkLogoPlate: true,
  },
]
