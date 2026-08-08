/**
 * Fixed “never regress” release gate for the homepage Sector Fit Explorer.
 * Keep intentionally small (≈25–40). Expand the larger golden corpus separately.
 */
export type SectorReleaseGateCase = {
  input: string
  status?: 'matched' | 'ambiguous' | 'needs_detail' | 'unsupported' | 'invalid' | 'idle'
  sectorId?: string
  forbiddenSectorIds?: string[]
  notes?: string
}

export const SECTOR_EXPLORER_RELEASE_GATE: SectorReleaseGateCase[] = [
  // Valid short aliases
  { input: 'HVAC', status: 'matched', sectorId: 'trades-home' },
  { input: 'MSP', status: 'matched', sectorId: 'msp-tech-services' },
  { input: 'gym', status: 'matched', sectorId: 'fitness-wellness' },
  { input: 'CPA', status: 'matched', sectorId: 'professional-services' },
  { input: 'SaaS', status: 'matched', sectorId: 'saas-tech-product' },

  // Invalid
  { input: 'asdfghjkl', status: 'invalid' },
  { input: '123456789', status: 'invalid' },
  { input: '🔥🔥🔥', status: 'invalid' },
  { input: 'aaaaaaaaaaaa', status: 'invalid' },
  { input: '!!!@@@###', status: 'invalid' },
  { input: 'qwertyuiop', status: 'invalid' },

  // Insufficient
  { input: 'my company', status: 'needs_detail' },
  { input: 'we help people', status: 'needs_detail' },
  { input: 'automation', status: 'needs_detail' },
  { input: 'small local business', status: 'needs_detail' },

  // Ambiguous
  { input: 'food and beverage', status: 'ambiguous' },
  { input: 'restaurant and food distributor', status: 'ambiguous' },

  // Unsupported but understandable
  { input: 'I sell rare antique maps', status: 'unsupported' },
  { input: 'custom underwater basket weaving cooperative', status: 'unsupported' },

  // Unicode / noisy valid
  {
    input: 'We’re a café / bakery!!!',
    status: 'matched',
    sectorId: 'restaurant-hospitality',
  },
  {
    input: '*** HVAC & PLUMBING ***',
    status: 'matched',
    sectorId: 'trades-home',
  },
  {
    input: 'Landscaping and seasonal cleanup',
    status: 'matched',
    sectorId: 'landscaping-field',
  },

  // Known collision regressions
  {
    input: 'public relations consultancy',
    forbiddenSectorIds: ['restaurant-hospitality'],
    notes: 'pub must not match inside public',
  },
  {
    input: 'public speaking coach',
    forbiddenSectorIds: ['restaurant-hospitality'],
  },
  {
    input: 'yardstick analytics',
    forbiddenSectorIds: ['landscaping-field'],
    notes: 'yard must not match inside yardstick',
  },
  {
    input: 'winning sales strategies consulting',
    forbiddenSectorIds: ['restaurant-hospitality'],
    notes: 'inn must not match inside winning',
  },

  // Empty
  { input: '', status: 'idle' },
  { input: '   ', status: 'idle' },

  // Representative verticals (keep gate balanced, not exhaustive)
  {
    input: 'Family dental clinic',
    status: 'matched',
    sectorId: 'medical-clinical',
  },
  {
    input: 'Commercial janitorial contractor',
    status: 'matched',
    sectorId: 'cleaning-facilities',
  },
  {
    input: 'Independent insurance brokerage',
    status: 'matched',
    sectorId: 'insurance',
  },

  // Common one-word / short-role aliases
  { input: 'plumber', status: 'matched', sectorId: 'trades-home' },
  { input: 'lash tech', status: 'matched', sectorId: 'fitness-wellness' },
  { input: 'nail tech', status: 'matched', sectorId: 'fitness-wellness' },
  { input: 'makeup artist', status: 'matched', sectorId: 'fitness-wellness' },
  { input: 'barber', status: 'matched', sectorId: 'fitness-wellness' },
  { input: 'restaurant', status: 'matched', sectorId: 'restaurant-hospitality' },
]
