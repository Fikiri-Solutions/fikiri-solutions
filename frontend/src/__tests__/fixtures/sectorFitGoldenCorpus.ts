export type SectorEvalCase = {
  input: string
  expectedStatus: 'matched' | 'ambiguous' | 'needs_detail' | 'unsupported' | 'invalid' | 'idle'
  expectedSectorId?: string
  forbiddenSectorIds?: string[]
  notes?: string
}

/**
 * Curated golden corpus for Sector Fit Explorer.
 * Expand toward 250–350 cases over time; this seed covers acceptance-critical paths.
 */
export const SECTOR_FIT_GOLDEN_CORPUS: SectorEvalCase[] = [
  // Idle / empty
  { input: '', expectedStatus: 'idle' },
  { input: '   ', expectedStatus: 'idle' },
  { input: '\t\n\u00A0', expectedStatus: 'idle' },

  // Invalid / noise
  { input: 'asdfghjkl', expectedStatus: 'invalid' },
  { input: 'qwertyuiop', expectedStatus: 'invalid' },
  { input: 'zxcvbnm', expectedStatus: 'invalid' },
  { input: 'aaaaaaaaaaaa', expectedStatus: 'invalid' },
  { input: 'abababababababab', expectedStatus: 'invalid' },
  { input: '123456789', expectedStatus: 'invalid' },
  { input: '!!!@@@###', expectedStatus: 'invalid' },
  { input: '🔥🔥🔥', expectedStatus: 'invalid' },
  { input: '*** &&& /// !!!', expectedStatus: 'invalid' },
  { input: 'x', expectedStatus: 'invalid' },
  { input: '??', expectedStatus: 'invalid' },

  // Valid short aliases
  { input: 'gym', expectedStatus: 'matched', expectedSectorId: 'fitness-wellness' },
  { input: 'CPA', expectedStatus: 'matched', expectedSectorId: 'professional-services' },
  { input: 'MSP', expectedStatus: 'matched', expectedSectorId: 'msp-tech-services' },
  { input: 'HVAC', expectedStatus: 'matched', expectedSectorId: 'trades-home' },
  { input: 'SaaS', expectedStatus: 'matched', expectedSectorId: 'saas-tech-product' },

  // Valid noisy / unicode
  {
    input: '*** HVAC & PLUMBING ***',
    expectedStatus: 'matched',
    expectedSectorId: 'trades-home',
  },
  {
    input: 'We’re a café / bakery!!!',
    expectedStatus: 'matched',
    expectedSectorId: 'restaurant-hospitality',
  },
  {
    input: '24/7 towing & roadside assistance',
    expectedStatus: 'matched',
    expectedSectorId: 'automotive',
  },
  {
    input: 'Déjà Vu beauty salon',
    expectedStatus: 'matched',
    expectedSectorId: 'fitness-wellness',
  },
  {
    input: 'Café & Bakery',
    expectedStatus: 'matched',
    expectedSectorId: 'restaurant-hospitality',
  },

  // Insufficient
  { input: 'my company', expectedStatus: 'needs_detail' },
  { input: 'we help people', expectedStatus: 'needs_detail' },
  { input: 'need CRM', expectedStatus: 'needs_detail' },
  { input: 'automation', expectedStatus: 'needs_detail' },
  { input: 'small local business', expectedStatus: 'needs_detail' },
  { input: 'we help local businesses grow', expectedStatus: 'needs_detail' },
  { input: 'we provide service', expectedStatus: 'needs_detail' },

  // Unsupported but viable
  { input: 'I sell rare antique maps', expectedStatus: 'unsupported' },
  { input: 'custom underwater basket weaving cooperative', expectedStatus: 'unsupported' },
  { input: 'bespoke fountain pen restoration atelier', expectedStatus: 'unsupported' },

  // Ambiguous
  { input: 'food and beverage', expectedStatus: 'ambiguous' },
  { input: 'restaurant and food distributor', expectedStatus: 'ambiguous' },

  // Positive per major sector (seed)
  {
    input: 'Landscaping and seasonal cleanup',
    expectedStatus: 'matched',
    expectedSectorId: 'landscaping-field',
  },
  {
    input: 'Neighborhood bakery / café',
    expectedStatus: 'matched',
    expectedSectorId: 'restaurant-hospitality',
  },
  {
    input: 'Family dental clinic',
    expectedStatus: 'matched',
    expectedSectorId: 'medical-clinical',
  },
  {
    input: 'MSP / managed IT for SMBs',
    expectedStatus: 'matched',
    expectedSectorId: 'msp-tech-services',
  },
  {
    input: 'Staffing agency for healthcare hires',
    expectedStatus: 'matched',
    expectedSectorId: 'staffing-recruiting',
  },
  {
    input: 'Commercial janitorial contractor',
    expectedStatus: 'matched',
    expectedSectorId: 'cleaning-facilities',
  },
  {
    input: 'Independent insurance brokerage',
    expectedStatus: 'matched',
    expectedSectorId: 'insurance',
  },
  {
    input: 'Fitness studio memberships',
    expectedStatus: 'matched',
    expectedSectorId: 'fitness-wellness',
  },
  {
    input: 'we run a small HVAC company',
    expectedStatus: 'matched',
    expectedSectorId: 'trades-home',
  },
  {
    input: 'car dealership service department',
    expectedStatus: 'matched',
    expectedSectorId: 'automotive',
  },
  {
    input: 'field service dispatch for commercial clients',
    expectedStatus: 'matched',
    expectedSectorId: 'field-service-dispatch',
  },
  {
    input: 'content creator',
    expectedStatus: 'matched',
    expectedSectorId: 'creator-media',
  },
  {
    input: 'residential real estate brokerage',
    expectedStatus: 'matched',
    expectedSectorId: 'real-estate',
  },
  {
    input: 'ecommerce clothing brand on shopify',
    expectedStatus: 'matched',
    expectedSectorId: 'retail',
  },
  {
    input: 'nonprofit fundraising team',
    expectedStatus: 'matched',
    expectedSectorId: 'nonprofit',
  },
  {
    input: 'freight brokerage and 3PL fulfillment',
    expectedStatus: 'matched',
    expectedSectorId: 'logistics-supply-chain',
  },
  {
    input: 'precision CNC manufacturing shop',
    expectedStatus: 'matched',
    expectedSectorId: 'manufacturing-industrial',
  },
  {
    input: 'B2B SaaS product team',
    expectedStatus: 'matched',
    expectedSectorId: 'saas-tech-product',
  },
  {
    input: 'assisted living and senior care home',
    expectedStatus: 'matched',
    expectedSectorId: 'senior-care',
  },
  {
    input: 'wedding venue and event space',
    expectedStatus: 'matched',
    expectedSectorId: 'events-venues',
  },
  {
    input: 'organic farm and greenhouse produce',
    expectedStatus: 'matched',
    expectedSectorId: 'agriculture',
  },
  {
    input: 'digital marketing agency for PPC',
    expectedStatus: 'matched',
    expectedSectorId: 'creative-marketing-agency',
  },
  {
    input: 'law firm and estate attorney',
    expectedStatus: 'matched',
    expectedSectorId: 'professional-services',
  },
  {
    input: 'coding bootcamp and online academy',
    expectedStatus: 'matched',
    expectedSectorId: 'education-training',
  },
  {
    input: 'management consulting for operations',
    expectedStatus: 'matched',
    expectedSectorId: 'b2b-business-services',
  },
  {
    input: 'food distribution and CPG wholesale',
    expectedStatus: 'matched',
    expectedSectorId: 'food-beverage-supply',
  },

  // Collision / false-positive guards
  {
    input: 'public speaking coach for executives',
    expectedStatus: 'unsupported',
    forbiddenSectorIds: ['restaurant-hospitality'],
    notes: 'pub must not match inside public',
  },
  {
    input: 'winning sales strategies consulting firm',
    expectedStatus: 'matched',
    forbiddenSectorIds: ['restaurant-hospitality'],
    notes: 'inn must not match inside winning',
  },
  {
    input: 'backyard cookout catering tips blog',
    expectedStatus: 'matched',
    expectedSectorId: 'restaurant-hospitality',
    forbiddenSectorIds: ['landscaping-field'],
    notes: 'yard alone should not force landscaping when catering dominates',
  },

  // Extra coverage toward corpus target
  { input: 'lolololololololol', expectedStatus: 'invalid' },
  { input: '5555555555', expectedStatus: 'invalid' },
  { input: '............', expectedStatus: 'invalid' },
  { input: 'IT company', expectedStatus: 'matched', expectedSectorId: 'msp-tech-services' },
  { input: 'managed IT support for SMBs', expectedStatus: 'matched', expectedSectorId: 'msp-tech-services' },
  { input: 'dental orthodontics practice', expectedStatus: 'matched', expectedSectorId: 'medical-clinical' },
  { input: 'snow removal and lawn care', expectedStatus: 'matched', expectedSectorId: 'landscaping-field' },
  { input: 'hotel banquet catering', expectedStatus: 'matched', expectedSectorId: 'restaurant-hospitality' },
  { input: 'chiropractic clinic', expectedStatus: 'matched', expectedSectorId: 'medical-clinical' },
  { input: 'roofing and siding contractor', expectedStatus: 'matched', expectedSectorId: 'trades-home' },
  { input: 'bookkeeping and tax firm', expectedStatus: 'matched', expectedSectorId: 'professional-services' },
  { input: 'twitch streamer and youtube creator', expectedStatus: 'matched', expectedSectorId: 'creator-media' },
  { input: 'property management for landlords', expectedStatus: 'matched', expectedSectorId: 'real-estate' },
  { input: 'crossfit gym and personal trainers', expectedStatus: 'matched', expectedSectorId: 'fitness-wellness' },
  { input: 'preschool and tutoring academy', expectedStatus: 'matched', expectedSectorId: 'education-training' },
  { input: 'auto body repair and fleet maintenance', expectedStatus: 'matched', expectedSectorId: 'automotive' },
  { input: 'life insurance broker', expectedStatus: 'matched', expectedSectorId: 'insurance' },
  { input: 'hospice and home care coordination', expectedStatus: 'matched', expectedSectorId: 'senior-care' },
  { input: 'conference venue and expo hall', expectedStatus: 'matched', expectedSectorId: 'events-venues' },
  { input: 'vineyard and orchard agriculture', expectedStatus: 'matched', expectedSectorId: 'agriculture' },
  { input: 'revops consulting and outsourced ops', expectedStatus: 'matched', expectedSectorId: 'b2b-business-services' },

  // Common short-role / beauty / trade aliases
  { input: 'plumber', expectedStatus: 'matched', expectedSectorId: 'trades-home' },
  { input: 'lash tech', expectedStatus: 'matched', expectedSectorId: 'fitness-wellness' },
  { input: 'eyelash tech', expectedStatus: 'matched', expectedSectorId: 'fitness-wellness' },
  { input: 'nail tech', expectedStatus: 'matched', expectedSectorId: 'fitness-wellness' },
  { input: 'makeup artist', expectedStatus: 'matched', expectedSectorId: 'fitness-wellness' },
  { input: 'esthetician', expectedStatus: 'matched', expectedSectorId: 'fitness-wellness' },
  { input: 'barber', expectedStatus: 'matched', expectedSectorId: 'fitness-wellness' },
  { input: 'hairstylist', expectedStatus: 'matched', expectedSectorId: 'fitness-wellness' },
  { input: 'carpenter', expectedStatus: 'matched', expectedSectorId: 'trades-home' },
  { input: 'cleaner', expectedStatus: 'matched', expectedSectorId: 'cleaning-facilities' },
  { input: 'vet', expectedStatus: 'matched', expectedSectorId: 'medical-clinical' },
  { input: 'caterer', expectedStatus: 'matched', expectedSectorId: 'restaurant-hospitality' },
  { input: 'photographer', expectedStatus: 'matched', expectedSectorId: 'events-venues' },
  {
    input: 'event organizer',
    expectedStatus: 'matched',
    expectedSectorId: 'events-venues',
    forbiddenSectorIds: ['cleaning-facilities'],
  },

  // One-worders that must not be blocked by generic-context terms
  { input: 'restaurant', expectedStatus: 'matched', expectedSectorId: 'restaurant-hospitality' },
  { input: 'clinic', expectedStatus: 'matched', expectedSectorId: 'medical-clinical' },
  { input: 'software company', expectedStatus: 'matched', expectedSectorId: 'saas-tech-product' },
  { input: 'yoga', expectedStatus: 'matched', expectedSectorId: 'fitness-wellness' },
  { input: 'insurance agent', expectedStatus: 'matched', expectedSectorId: 'insurance' },
  { input: 'it company', expectedStatus: 'matched', expectedSectorId: 'msp-tech-services' },
  { input: 'dog groomer', expectedStatus: 'matched', expectedSectorId: 'medical-clinical' },
  { input: 'web designer', expectedStatus: 'matched', expectedSectorId: 'creative-marketing-agency' },
  { input: 'virtual assistant', expectedStatus: 'matched', expectedSectorId: 'b2b-business-services' },
  { input: 'chimney sweep', expectedStatus: 'matched', expectedSectorId: 'cleaning-facilities' },
]
