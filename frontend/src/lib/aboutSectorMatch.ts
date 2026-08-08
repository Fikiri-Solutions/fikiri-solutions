/**
 * Sector Fit Explorer matcher for the public homepage.
 * Deterministic, client-side, keyword/template based — no LLM in the primary path.
 * Pipeline: normalize → viability gate → typed keyword scoring → confidence/ambiguity → presentation.
 */

export type FeatureFitId = 'email_automation' | 'crm_management' | 'ai_assistant'

const FEATURE_LABELS: Record<FeatureFitId, string> = {
  email_automation: 'Email Automation',
  crm_management: 'CRM Management',
  ai_assistant: 'AI Assistant',
}

export type KeywordMatchType = 'exact' | 'token' | 'phrase' | 'prefix'

export type SectorKeyword = {
  value: string
  type: KeywordMatchType
  weight: number
  conceptId: string
}

type SectorTemplate = {
  id: string
  displayName: string
  /** Raw catalog strings; compiled to typed keywords at module init */
  keywords: string[]
  summary: string
  fits: Record<FeatureFitId, string>
}

type SectorScoring = SectorTemplate & {
  category: string
  positiveKeywords: SectorKeyword[]
}

export type SectorInputStatus =
  | 'empty'
  | 'too_short'
  | 'low_information'
  | 'nonsensical'
  | 'viable'
  | 'unsupported'
  | 'ambiguous'
  | 'matched'

export type SectorInputReasonCode =
  | 'EMPTY'
  | 'NO_MEANINGFUL_CHARACTERS'
  | 'TOO_SHORT'
  | 'ONLY_NUMBERS'
  | 'MOSTLY_SYMBOLS'
  | 'REPEATED_CHARACTER_SEQUENCE'
  | 'KEYBOARD_MASH'
  | 'INSUFFICIENT_INFORMATION'
  | 'UNSUPPORTED_LANGUAGE'
  | 'NO_SUPPORTED_SECTOR'
  | 'AMBIGUOUS_SECTORS'
  | 'VALID_MATCH'

export type SectorFitPresentationStatus =
  | 'idle'
  | 'invalid'
  | 'needs_detail'
  | 'unsupported'
  | 'ambiguous'
  | 'matched'

export type FeatureFit = {
  id: FeatureFitId
  title: string
  fit: string
}

export type SectorFitPresentation = {
  status: SectorFitPresentationStatus
  reasonCode: SectorInputReasonCode | null
  headline: string
  matchStrength: 'high' | 'medium' | 'broad' | null
  category: string | null
  sectorId: string | null
  needsMoreDetail: boolean
  ambiguousAlternates: ReadonlyArray<{ id: string; displayName: string }> | null
  summary: string
  featuresOrdered: ReadonlyArray<FeatureFit>
}

export type SectorInputAnalysis = {
  rawLength: number
  normalizedInput: string
  matchingInput: string
  status: SectorInputStatus
  reasonCode: SectorInputReasonCode | null
  presentation: SectorFitPresentation
}

/** Input limits (homepage safety) */
export const MAX_RAW_INPUT_CHARS = 500
export const MAX_MATCHING_INPUT_CHARS = 300
export const MIN_MEANINGFUL_CHARS = 2
export const MIN_MEANINGFUL_LETTERS = 2
export const MAX_TOKEN_COUNT = 60

/** Minimum primary description length before follow-up (legacy; prefer status-based UI) */
export const MIN_PRIMARY_CHARS_FOR_FOLLOW_UP = 6

const APPROVED_SHORT_TERMS = new Set([
  'ai',
  'it',
  'gym',
  'cpa',
  'msp',
  'hvac',
  'saas',
  'crm',
  'ngo',
  'cpg',
  'pos',
  'bpo',
  'oem',
  '3pl',
  'hoa',
  'spa',
  'pub',
  'inn',
  'mow',
  'ppc',
  'vet',
  'k9',
  '3d',
  'mua',
  'dj',
])

/** Intentional stem/prefix keywords from the catalog (token-boundary prefix, min 4 chars). */
const INTENTIONAL_PREFIXES = new Set([
  'landscap',
  'horticult',
  'orthodont',
  'endodont',
  'periodont',
  'veterinar',
  'chiropract',
  'dermatolog',
  'ophthalmolog',
  'optometr',
  'plumb',
  'bookkeep',
  'actuar',
  'fundraisin',
  'fabricat',
  'recruit',
  'agronom',
  'subcontract',
  'electric',
  'manufactur',
])

const BUSINESS_CONTEXT_TERMS = new Set([
  'sell',
  'selling',
  'provide',
  'providing',
  'repair',
  'install',
  'manage',
  'deliver',
  'manufacture',
  'consult',
  'train',
  'teach',
  // Keep these generic — do NOT include sector labels like restaurant/clinic/software
  // (those are real catalog keywords and must remain matchable as one-worders).
  'shop',
  'store',
  'agency',
  'firm',
  'contractor',
  'company',
  'business',
  'service',
  'services',
  'customers',
  'clients',
  'appointments',
  'products',
  'help',
  'helping',
  'need',
  'needs',
  'automation',
  'crm',
  'local',
  'small',
  'online',
  'team',
])

const WEAK_SINGLE_WORDS = new Set([
  'service',
  'services',
  'business',
  'company',
  'industry',
  'solutions',
  'local',
  'help',
  'customer',
  'clients',
  'sales',
  'team',
  'support',
  'provider',
  'consulting',
  'management',
  'operations',
  'professional',
  'people',
  'customers',
  'automation',
  'need',
  'needs',
  'want',
  'small',
])

const KEYBOARD_MASH_PATTERNS = [
  /qwerty/iu,
  /asdfgh/iu,
  /zxcvbn/iu,
  /qazwsx/iu,
  /poiuyt/iu,
  /asdfasdf/iu,
  /hjkl/iu,
]

const SAME_CHARACTER_RE = /^(.)\1{5,}$/u
const REPEATED_BLOCK_RE = /^(.{1,3})\1{4,}$/u

const AMBIGUITY_SCORE_MARGIN = 3
const MIN_SCORE_HIGH = 10
const MIN_SCORE_MEDIUM = 6

const FALLBACK_FITS: Record<FeatureFitId, string> = {
  email_automation:
    'Surface urgent threads first and cut down on copy-paste so responses go out the same day.',
  crm_management:
    'One thread of truth per contact: who spoke last, what’s pending, and what stage the relationship is in.',
  ai_assistant:
    'Turn long threads into short internal briefs and suggested next steps—your team sends the final message.',
}

const FEATURE_ORDER: FeatureFitId[] = ['email_automation', 'crm_management', 'ai_assistant']

function stripCombiningMarks(value: string): string {
  try {
    return value.replace(/\p{M}+/gu, '')
  } catch {
    return value
  }
}

/** Display-safe normalized input: preserves readable Unicode letters. */
export function normalizeForValidation(input: string): string {
  let value = input
  try {
    value = value.normalize('NFKC')
  } catch {
    // ignore
  }
  try {
    value = value.replace(/\p{C}+/gu, ' ')
  } catch {
    value = value.replace(/[\u0000-\u001F\u007F-\u009F\u200B-\u200F\u202A-\u202E\u2060\uFEFF]/g, ' ')
  }
  return value.replace(/\s+/gu, ' ').trim()
}

/** English matching form for the current keyword catalog. */
export function normalizeForMatching(input: string): string {
  let value = normalizeForValidation(input)
  try {
    value = value.normalize('NFKD')
  } catch {
    // ignore
  }
  value = stripCombiningMarks(value)
  try {
    value = value.toLocaleLowerCase('en-US')
  } catch {
    value = value.toLowerCase()
  }
  return value
    .replace(/&/gu, ' and ')
    .replace(/[’']/gu, '')
    .replace(/[‐-‒–—―]/gu, '-')
    .replace(/[^\p{L}\p{N}\s+/-]+/gu, ' ')
    .replace(/\s+/gu, ' ')
    .trim()
}

/** @deprecated Prefer normalizeForMatching — kept for existing call sites/tests */
export function normalizeQuery(raw: string): string {
  return normalizeForMatching(raw)
}

export function combineSectorQueries(primary: string, additional: string): string {
  const parts = [primary.trim(), additional.trim()].filter((p) => p.length > 0)
  return parts.join(' ')
}

function countByClass(normalized: string): {
  letterCount: number
  numberCount: number
  symbolCount: number
  whitespaceCount: number
  meaningfulCount: number
} {
  let letterCount = 0
  let numberCount = 0
  let symbolCount = 0
  let whitespaceCount = 0
  for (const char of normalized) {
    if (/\s/u.test(char)) {
      whitespaceCount += 1
    } else if (/\p{L}/u.test(char)) {
      letterCount += 1
    } else if (/\p{N}/u.test(char)) {
      numberCount += 1
    } else {
      symbolCount += 1
    }
  }
  return {
    letterCount,
    numberCount,
    symbolCount,
    whitespaceCount,
    meaningfulCount: letterCount + numberCount,
  }
}

function tokenizeMatching(matchingInput: string): string[] {
  if (!matchingInput) return []
  return matchingInput
    .split(/[\s/+-]+/u)
    .map((t) => t.trim())
    .filter((t) => t.length > 0)
    .slice(0, MAX_TOKEN_COUNT)
}

function compactedNoSpace(matchingInput: string): string {
  return matchingInput.replace(/\s+/gu, '')
}

function vowelRatio(token: string): number {
  const letters = [...token].filter((c) => /\p{L}/u.test(c))
  if (letters.length === 0) return 0
  const vowels = letters.filter((c) => /[aeiouy]/i.test(c)).length
  return vowels / letters.length
}

function isApprovedShortAlias(matchingInput: string, tokens: string[]): boolean {
  if (APPROVED_SHORT_TERMS.has(matchingInput)) return true
  if (tokens.length === 1 && APPROVED_SHORT_TERMS.has(tokens[0])) return true
  return false
}

function hasNonLatinLetters(normalizedValidation: string): boolean {
  // Letters that survive matching-normalization as non [a-z] after accent stripping
  // indicate non-Latin scripts (Cyrillic, CJK, Arabic, etc.).
  try {
    const letters = normalizedValidation.match(/\p{L}/gu) ?? []
    return letters.some((ch) => !/[a-zA-Z]/.test(ch))
  } catch {
    return /[^\u0000-\u007Fa-zA-Z0-9\s]/.test(normalizedValidation)
  }
}

function looksLikeKeyboardMash(matchingInput: string, tokens: string[]): boolean {
  const compact = compactedNoSpace(matchingInput)
  if (compact.length < 6) return false

  // Non-Latin script input is never "keyboard mash" in the QWERTY sense
  const latinOnly = /^[a-z0-9]+$/i.test(compact)
  if (!latinOnly && !/[a-z]/i.test(compact)) return false

  const hasMashPattern = KEYBOARD_MASH_PATTERNS.some((re) => re.test(compact))
  if (hasMashPattern) return true

  const lowVowels = vowelRatio(compact) < 0.18 && compact.length >= 7
  const repeatedAdjacent = /(.)\1{3,}/u.test(compact)
  const repeatedBlock = /([a-z]{2,3})\1{2,}/iu.test(compact)

  // Require a strong noise signal — do not flag ordinary long English words like "automation"
  if (tokens.length === 1 && lowVowels && (repeatedAdjacent || repeatedBlock || compact.length >= 8)) {
    return true
  }
  if (tokens.length === 1 && repeatedBlock && compact.length >= 10) return true
  if (tokens.length === 1 && repeatedAdjacent && lowVowels) return true

  return false
}

function looksLikeRepeatedNoise(matchingInput: string): boolean {
  const compact = compactedNoSpace(matchingInput)
  if (compact.length < 6) return false
  if (SAME_CHARACTER_RE.test(compact)) return true
  if (REPEATED_BLOCK_RE.test(compact)) return true
  return false
}

type ViabilityResult = {
  status: SectorInputStatus
  reasonCode: SectorInputReasonCode
} | null

function assessViability(
  rawInput: string,
  normalizedInput: string,
  matchingInput: string
): ViabilityResult {
  if (!normalizedInput) {
    return { status: 'empty', reasonCode: 'EMPTY' }
  }

  const counts = countByClass(normalizedInput)
  if (counts.meaningfulCount === 0) {
    return { status: 'nonsensical', reasonCode: 'NO_MEANINGFUL_CHARACTERS' }
  }

  const tokens = tokenizeMatching(matchingInput)
  const matchingCounts = countByClass(matchingInput)

  // Numbers only (matching form has no letters)
  if (matchingCounts.letterCount === 0 && matchingCounts.numberCount > 0) {
    return { status: 'nonsensical', reasonCode: 'ONLY_NUMBERS' }
  }

  if (
    matchingCounts.letterCount === 0 &&
    matchingCounts.numberCount === 0 &&
    (matchingCounts.symbolCount > 0 || counts.symbolCount > 0)
  ) {
    return { status: 'nonsensical', reasonCode: 'MOSTLY_SYMBOLS' }
  }

  // Mostly symbols: symbols dominate and almost no letters
  if (
    matchingCounts.letterCount > 0 &&
    counts.symbolCount >= matchingCounts.letterCount * 2 &&
    matchingCounts.letterCount < MIN_MEANINGFUL_LETTERS
  ) {
    return { status: 'nonsensical', reasonCode: 'MOSTLY_SYMBOLS' }
  }

  if (looksLikeRepeatedNoise(matchingInput)) {
    return { status: 'nonsensical', reasonCode: 'REPEATED_CHARACTER_SEQUENCE' }
  }

  if (looksLikeKeyboardMash(matchingInput, tokens)) {
    return { status: 'nonsensical', reasonCode: 'KEYBOARD_MASH' }
  }

  // Too short / too little — unless approved alias
  if (!isApprovedShortAlias(matchingInput, tokens)) {
    if (matchingCounts.meaningfulCount < MIN_MEANINGFUL_CHARS || matchingCounts.letterCount < MIN_MEANINGFUL_LETTERS) {
      return { status: 'too_short', reasonCode: 'TOO_SHORT' }
    }
    if (matchingInput.length < 2) {
      return { status: 'too_short', reasonCode: 'TOO_SHORT' }
    }
  }

  // Substantial non-Latin letters with little Latin → unsupported language for this catalog
  const latinLetterCount = (matchingInput.match(/[a-z]/gi) || []).length
  if (hasNonLatinLetters(normalizedInput) && latinLetterCount < 3 && matchingCounts.letterCount >= 4) {
    return { status: 'low_information', reasonCode: 'UNSUPPORTED_LANGUAGE' }
  }

  // Insufficient business information (vague but not nonsense)
  if (isInsufficientBusinessDescription(matchingInput, tokens)) {
    return { status: 'low_information', reasonCode: 'INSUFFICIENT_INFORMATION' }
  }

  return null
}

function isInsufficientBusinessDescription(matchingInput: string, tokens: string[]): boolean {
  if (isApprovedShortAlias(matchingInput, tokens)) return false
  // Single weak generic token
  if (tokens.length === 1 && WEAK_SINGLE_WORDS.has(tokens[0])) return true
  // Only weak/business-context generics, no distinctive sector token yet —
  // defer to scoring; only flag clearly vague phrases here
  const distinctive = tokens.filter(
    (t) =>
      !WEAK_SINGLE_WORDS.has(t) &&
      !BUSINESS_CONTEXT_TERMS.has(t) &&
      t.length >= 3
  )
  const vaguePhrases = [
    'my company',
    'our company',
    'we help people',
    'we help customers',
    'need crm',
    'need help',
    'want automation',
    'small business',
    'small local business',
    'local business',
    'help local businesses',
    'we help local businesses grow',
    'automation',
    'i want automation',
    'my company needs help',
  ]
  if (vaguePhrases.includes(matchingInput)) return true

  // Very short vague: only weak + context terms
  if (tokens.length <= 4 && distinctive.length === 0 && tokens.every((t) => WEAK_SINGLE_WORDS.has(t) || BUSINESS_CONTEXT_TERMS.has(t))) {
    return true
  }
  return false
}

function conceptIdFor(value: string): string {
  const base = value.replace(/\s+/g, '_').slice(0, 32)
  // Collapse common morphological variants into one concept when possible
  for (const prefix of INTENTIONAL_PREFIXES) {
    if (value === prefix || value.startsWith(prefix)) return prefix
  }
  if (value.endsWith('ing') && value.length > 5) return value.slice(0, -3)
  if (value.endsWith('ers') && value.length > 5) return value.slice(0, -1)
  if (value.endsWith('er') && value.length > 4) return value.slice(0, -2)
  if (value.endsWith('s') && !value.endsWith('ss') && value.length > 4) return value.slice(0, -1)
  return base
}

function compileKeyword(raw: string): SectorKeyword | null {
  const trimmed = raw.trim()
  if (!trimmed) return null
  const value = normalizeForMatching(trimmed)
  if (value.length < 2) return null

  const conceptId = conceptIdFor(value)

  if (value.includes(' ')) {
    // Phrase: if any token is an intentional prefix stem, still phrase type;
    // matching logic allows prefix on intentional last tokens.
    return { value, type: 'phrase', weight: 10, conceptId }
  }

  if (INTENTIONAL_PREFIXES.has(value)) {
    return { value, type: 'prefix', weight: 6, conceptId }
  }

  if (APPROVED_SHORT_TERMS.has(value) || value.length <= 3) {
    return { value, type: 'token', weight: 10, conceptId }
  }

  // Whole-input exact aliases get boosted at score time when q === value
  return { value, type: 'token', weight: 8, conceptId }
}

function compileKeywords(rawKeywords: string[]): SectorKeyword[] {
  const out: SectorKeyword[] = []
  const seen = new Set<string>()
  for (const raw of rawKeywords) {
    const kw = compileKeyword(raw)
    if (!kw) continue
    const key = `${kw.type}:${kw.value}`
    if (seen.has(key)) continue
    seen.add(key)
    out.push(kw)
  }
  return out
}


const SECTOR_SOURCE: SectorTemplate[] = [
  {
    id: 'landscaping-field',
    displayName: 'Landscaping & outdoor services',
    keywords: [
      'landscap',
      'lawn care',
      'lawn ',
      'yard',
      'mow',
      'mowing',
      'turf',
      'garden',
      'arbor',
      'tree trim',
      'tree service',
      'irrigation',
      'snow removal',
      'snow plow',
      'hardscape',
      'grounds keep',
      'horticult',
      'outdoor liv',
      'fence install',
      'deck build',
      'pressure wash',
      'pressure washing',
      'fence company',
      'fence contractor',
      'deck builder',
      'deck building',
      'commercial grounds',
    ],
    summary:
      'Route density and weather drive spikes: estimate requests, material delays, crew changes, and “are you still coming?” texts all compete for attention when you’re nowhere near a desk.',
    fits: {
      email_automation:
        'Separate quote requests from route changes so dispatch isn’t rebuilding the inbox every morning.',
      crm_management:
        'Jobs, revisit dates, and property-level history stay readable when the crew changes or season rolls over.',
      ai_assistant:
        'Rough-cut follow-ups after walk-throughs or bad-weather postponements—consistent tone without rewriting from zero.',
    },
  },
  {
    id: 'restaurant-hospitality',
    displayName: 'Restaurants, catering & hospitality',
    keywords: [
      'food and beverage',
      'food beverage',
      'food service',
      'food truck',
      'meal prep',
      'restaurant',
      'cafe',
      'coffee',
      'coffee shop',
      'cafeteria',
      'diner',
      'pub',
      'tavern',
      'brewpub',
      'taproom',
      'wine bar',
      'kitchen',
      'chef',
      'brewery',
      'distillery',
      'bakery',
      'barista',
      'catering',
      'caterer',
      'catering company',
      'ghost kitchen',
      'cloud kitchen',
      'food hall',
      'food truck',
      'quick service',
      'fast casual',
      'hotel',
      'motel',
      'inn ',
      ' bed and breakfast',
      'boutique hotel',
      'hospitality',
      'banquet',
      'room service',
    ],
    summary:
      'Thin margins ride on turnout, staffing, vendors, guest complaints, and event holds—much of it still arrives as email threads and forwarded screenshots.',
    fits: {
      email_automation:
        'Treat private events, refunds, allergy questions, and supplier POs differently so the right lead answers first.',
      crm_management:
        'Regulars, banquet leads, local accounts, and tour groups aren’t orphaned when managers rotate shifts.',
      ai_assistant:
        'Bulleted recap of messy guest-email chains before approvals or comps—fewer thumb-wrestling forwards.',
    },
  },
  {
    id: 'medical-clinical',
    displayName: 'Clinical & patient-facing care',
    keywords: [
      'medical',
      'clinic',
      'primary care',
      'urgent care',
      'walk in clinic',
      'patients',
      'patient care',
      'patient portal',
      'patient intake',
      'new patient',
      'patient schedul',
      'patient facing',
      'dentist',
      'dental',
      'orthodont',
      'endodont',
      'periodont',
      'veterinar',
      'vet',
      'vet clinic',
      'animal hospital',
      'doula',
      'midwife',
      'chiropract',
      'podiatrist',
      'dermatolog',
      'ophthalmolog',
      'optometr',
      'med spa',
      'medspa',
      'plastic surgery',
      'pharmacy',
      'pharmacist',
      'therapist',
      'therapy practice',
      'physical therap',
      'occupational therap',
      'mental health practice',
      'psychiatry',
      'counseling practice',
      'psychologist',
      'physician group',
      'healthcare provider',
      'clinical staff',
      'appointment schedul',
      'dog groomer',
      'pet groomer',
      'pet grooming',
      'dog walker',
      'pet sitter',
      'pet sitting',
      'mobile pet',
    ],
    summary:
      'Scheduling changes, refill requests, lab coordination, payer questions, recall campaigns, no-shows—front desk workflows still depend on orderly email triage.',
    fits: {
      email_automation:
        'Route routine reschedule or intake mail away from clinician escalations—without exposing draft replies as final outcomes.',
      crm_management:
        'Families, dependents, episodic visits, recalls, and payer contacts stay stitched to fewer duplicate records.',
      ai_assistant:
        'Neutral internal summaries before handoffs—you stay responsible for policy, HIPAA, and what actually gets sent.',
    },
  },
  {
    id: 'trades-home',
    displayName: 'Trades & home services',
    keywords: [
      'electric',
      'electrical',
      'electrician',
      'plumb',
      'plumber',
      'plumbing',
      'hvac',
      'ac tech',
      'ac repair',
      'air conditioning',
      'roofer',
      'roofing',
      'siding',
      'window install',
      'garage door',
      'flooring install',
      'kitchen remodel',
      'bathroom remodel',
      'home remodel',
      'general contractor',
      'construction',
      'subcontract',
      'painter ',
      'painting ',
      'handyman',
      'locksmith',
      'pool service',
      'pest control',
      'solar panel',
      'solar install',
      'battery storage',
      'generator install',
      'carpenter',
      'carpentry',
      'welder',
      'welding',
      'tiler',
      'tile setter',
      'drywall',
      'drywaller',
      'mason',
      'bricklayer',
      'glazier',
      'insulation contractor',
      'septic',
      'well pump',
      'appliance repair',
    ],
    summary:
      'Emergency tickets, quoting, permitting questions, subcontractor chatter, warranties, and inspections mean one delayed reply can cascade into rework or churn.',
    fits: {
      email_automation:
        'Bump after-hours outages and flooded-basement calls ahead of quoting mail so dispatch isn’t guessing priority.',
      crm_management:
        'Quotes, installs, change orders, and warranty windows stay keyed to homeowner email + job address.',
      ai_assistant:
        'Late-day status summaries you can skim before texting the homeowner—fewer repetitive “checking in” notes.',
    },
  },
  {
    id: 'professional-services',
    displayName: 'Professional & financial advisory',
    keywords: [
      'legal',
      'attorney',
      'lawyer',
      'law firm',
      'cpa',
      'tax prepar',
      'tax firm',
      'accounting firm',
      'bookkeep',
      'financial advis',
      'wealth manag',
      'fiduciary',
      'tax audit',
      'financial audit',
      'external audit',
      'statutory audit',
      'forensic accounting',
      'engineering firm',
      'structural engineer',
      'civil engineer',
      'mechanical engineer consulting',
      'surveying',
      'actuar',
      'notary',
      'notary public',
      'paralegal',
    ],
    summary:
      'Engagement letters, document requests, client status pings, auditor mail, counterparties—patterns repeat matter by matter.',
    fits: {
      email_automation:
        'Repeated intake questionnaires and chasing signatures don’t deserve bespoke typing every single time.',
      crm_management:
        'Parties, engagements, timelines, billing contacts—fewer “which thread is current?” hunts across juniors.',
      ai_assistant:
        'Prep bullets for partner review from long correspondent chains—approve before anything client-facing ships.',
    },
  },
  {
    id: 'creative-marketing-agency',
    displayName: 'Creative & digital agencies',
    keywords: [
      'marketing agency',
      'digital agency',
      'advertising agency',
      'creative agency',
      'branding agency',
      'design studio',
      'web agency',
      'web designer',
      'web developer',
      'graphic designer',
      'graphic design',
      'seo agency',
      'ppc ',
      'media buying',
      'content agency',
      'social media agency',
      'growth agency',
    ],
    summary:
      'Client approvals, revisions, asset handoffs, timelines, invoicing pings, scopes—agency inboxes behave like ticketing without the ticketing discipline.',
    fits: {
      email_automation:
        'Separate new business from active retainers so leads don’t languish behind client fire drills.',
      crm_management:
        'Retain clients, paused accounts, stakeholder maps, renewal dates—all visible without digging Slack + inbox.',
      ai_assistant:
        'Scope-change recaps pulled from sprawling CC threads before PMs reopen the worksheet.',
    },
  },
  {
    id: 'creator-media',
    displayName: 'Creators, influencers & digital media',
    keywords: [
      'content creator',
      'content creat',
      'creator',
      'creators',
      'influencer',
      'influencers',
      'youtuber',
      'youtube creator',
      'youtube channel',
      'tiktoker',
      'tiktok creator',
      'instagram creator',
      'ugc creator',
      'brand deal',
      'sponsorship',
      'podcast host',
      'podcaster',
      'podcast',
      'streamer',
      'twitch',
      'newsletter',
      'substack',
      'course creator',
      'online course',
      'digital product',
      'media kit',
      'fan mail',
    ],
    summary:
      'Inbox load is brand inquiries, sponsorship terms, collaboration briefs, and audience questions—often mixed with personal mail and hard to triage without a system.',
    fits: {
      email_automation:
        'Separate paid partnerships, gifting, and general audience mail so revenue opportunities do not sit behind newsletters.',
      crm_management:
        'Track brands, campaigns, deliverables, and renewal conversations without losing threads across platforms.',
      ai_assistant:
        'Summarize long brand threads into deal terms and next steps before you reply on camera or by email.',
    },
  },
  {
    id: 'retail',
    displayName: 'Retail & product brands',
    keywords: [
      'retail',
      'boutique ',
      'ecommerce',
      'e commerce',
      'dropship',
      'wholesale buyer',
      'distributor ',
      'reseller ',
      'shopify',
      'storefront ',
      'point of sale',
      'gift shop',
    ],
    summary:
      'Buyer inquiries, influencer mail, defective batches, storefront reviews forwarded as email—it’s ops support hiding in Gmail.',
    fits: {
      email_automation:
        'Separate wholesale from consumer support so SLA owners don’t collide.',
      crm_management:
        'Reorder cycles, influencer seeding, unhappy VIPs—with history by email alias and store.',
      ai_assistant:
        'Short internal brief ahead of escalation calls (“what shipped, what was promised”).',
    },
  },
  {
    id: 'real-estate',
    displayName: 'Real estate & property operations',
    keywords: [
      'realtor',
      'real estate agent',
      'real estate brokerage',
      'leasing agent',
      'property manager',
      'property management',
      'asset manager',
      'landlord ',
      'hoa ',
      'condo assoc',
      'short term rental',
      'vacation rental',
      'facility manager ',
    ],
    summary:
      'Showings, leases, inspections, maintenance tickets, HOA noise, turnover vendors—everything competes while “new lead just dropped.”',
    fits: {
      email_automation:
        'Separate renter emergencies from drip nurture so Sunday mail doesn’t erase Monday pipeline.',
      crm_management:
        'Buyer, seller, landlord, tenant, vendor—all with next steps your assistant can chase.',
      ai_assistant:
        'Prep for calls with distilled inspection or lease-contingency threads—not re-reading eighty messages.',
    },
  },
  {
    id: 'fitness-wellness',
    displayName: 'Fitness, salon & recurring appointments',
    keywords: [
      'gymnasium',
      'fitness',
      'fitness studio',
      'fitness center',
      'crossfit ',
      'yoga studio',
      'yoga',
      'yoga instructor',
      'pilates',
      'pilates studio',
      'spin studio',
      'personal train',
      'trainer',
      'trainers',
      'fitness coach',
      'strength coach',
      'wellness coach',
      'athletic coach',
      'gym',
      'salon ',
      'hair salon',
      'barber',
      'barbershop',
      'hairstylist',
      'hair stylist',
      'colorist',
      'balayage',
      'blow dry',
      'blowdry',
      'blowout',
      ' nail salon',
      'nails',
      'nail tech',
      'nail technician',
      'manicurist',
      'manicure',
      'pedicurist',
      'pedicure',
      'spa ',
      'day spa',
      'massage',
      'massage therapist',
      'massage therapy',
      'med spa',
      'aesthetics',
      'esthetician',
      'aesthetician',
      'cosmetologist',
      'cosmetology',
      'facialist',
      'waxing ',
      'lash',
      'lashes',
      'lash tech',
      'lash artist',
      'lash technician',
      'eyelash',
      'eyelash tech',
      'eyelash extensions',
      'brow tech',
      'brow artist',
      'makeup',
      'makeup artist',
      'make up artist',
      'bridal makeup',
      'mua',
      'grooming',
      'boutique spa',
      'tanning ',
      'spray tan',
      'facial',
      'facials',
      'microblading',
      'microblade',
      'permanent makeup',
      'threader',
      'threading',
      'brow threading',
      'tattoo',
      'tattoo artist',
      'tattoo shop',
      'piercer',
      'body piercing',
    ],
    summary:
      'Packages, cancellations, memberships, refill retail, Groupon fallout—confirmation discipline is half the retention story.',
    fits: {
      email_automation:
        'Treat “running late”, “paused membership”, versus “new bridal party” distinctly so desks don’t improvise wording.',
      crm_management:
        'Standing appointments, prepaid blocks, churn risk—all visible beyond the stylist’s clipboard.',
      ai_assistant:
        'Polite reschedule or win-back drafts your staff edits before hitting send.',
    },
  },
  {
    id: 'education-training',
    displayName: 'Schools & training providers',
    keywords: [
      'daycare ',
      'childcare',
      'child care',
      'preschool',
      'private school',
      'charter school',
      'tutoring',
      'tutor',
      'private tutor',
      'nanny',
      'nannying',
      'piano teacher',
      'music teacher',
      'voice coach',
      'voice teacher',
      'learning center',
      'test prep',
      'drivers ed',
      'trade school ',
      'bootcamp ',
      'corporate train',
      'instructor ',
      'academy ',
      'enrichment ',
      'homeschool coop',
      'education consultant',
      'esl school',
      'music school ',
      'driving school ',
    ],
    summary:
      'Enrollment questions, guardians (sometimes several), cancellations, invoicing reminders, excursion waivers—for many programs it never leaves email.',
    fits: {
      email_automation:
        'FAQ-style intake vs sensitive escalations routed clean so teachers aren’t drowning before class.',
      crm_management:
        'Families, guardians, invoices, semesters, waitlists—all tied neatly for admin turnover seasons.',
      ai_assistant:
        'Summarize “parent thread got long” bundles into actionable admin notes.',
    },
  },
  {
    id: 'automotive',
    displayName: 'Repair, dealerships & fleet',
    keywords: [
      'automotive',
      'auto repair',
      'automotive repair',
      'auto shop',
      'body shop',
      'collision',
      'collision repair',
      'mechanic',
      'mechanic shop',
      'fleet maint',
      'fleet service',
      'fleet management',
      'oil change',
      'tire shop',
      'tires',
      'brake shop',
      'transmission shop',
      'smog check',
      'quick lube',
      'diesel truck repair',
      'diesel repair',
      'motorcycle shop',
      'rv repair',
      'marine service',
      'car dealership',
      'auto dealership',
      'dealership',
      'used car',
      'auto sales',
      'parts department',
      'automotive detailing',
      'detail shop',
      'detailer',
      'car detailing',
      'auto detailing',
      'mobile detailing',
      'tow company',
      'tow truck',
      'towing',
      'roadside assistance',
    ],
    summary:
      'Estimates awaiting approval, OEM bulletins, fleet managers, towing partners, comeback complaints—everything chases bays and advisors.',
    fits: {
      email_automation:
        'Prioritize down-vehicle fleets ahead of brochure leads so writers stop context-switching all morning.',
      crm_management:
        'Fleet accounts, approvals, revisit intervals, and estimator ownership stay searchable.',
      ai_assistant:
        'Rough customer-facing ETA language after chaotic internal chatter—edited before SMS goes out.',
    },
  },
  {
    id: 'insurance',
    displayName: 'Insurance & brokers',
    keywords: [
      'insurance agency',
      'insurance broker',
      'insurance agent',
      'insurance',
      'producer license',
      'claims adjust',
      'independent broker',
      'captive agency',
      'risk advisor',
      'benefits brokerage',
      'employee benefits',
      'life insurance ',
      'property casualty',
    ],
    summary:
      'Quote requests, underwriting follow-ups, loss runs, policy endorsements—for smaller shops that’s inbox glue before it ever touches a PAS.',
    fits: {
      email_automation:
        'Separate quote intake from claims noise so turnaround promises stay coherent.',
      crm_management:
        'Renewal dates, dependents, beneficiaries, referral partners—all less likely to evaporate during busy season.',
      ai_assistant:
        'Prep coverage-option talking points distilled from sprawling carrier replies.',
    },
  },
  {
    id: 'nonprofit',
    displayName: 'Nonprofits & civic orgs',
    keywords: [
      'nonprofit',
      'not for profit',
      'foundation ',
      'charitable',
      'ngo ',
      'mission driven',
      'grant writer ',
      'fundraisin',
      'volunteer ',
      'board member org',
      'community org ',
    ],
    summary:
      'Volunteer scheduling, donor receipts, gala logistics, coalition partners—inboxes become project memory.',
    fits: {
      email_automation:
        'Treat donor stewardship, vendor invoices, journalist asks, grants—each with sane defaults.',
      crm_management:
        'Relationships and pledges clearer when coordinators rotate annually.',
      ai_assistant:
        'Brief board packets from operational email archaeology—edited for tone and correctness.',
    },
  },
  {
    id: 'logistics-supply-chain',
    displayName: 'Logistics, freight & fulfillment',
    keywords: [
      'logistics',
      'freight broker',
      'trucking ',
      'truck driver',
      'truck driving',
      '3pl ',
      'fulfillment center',
      'warehouse ops',
      'last mile ',
      'courier service',
      'expedite ',
      'drayage ',
      'supply chain ',
    ],
    summary:
      'Pickup windows, POD disputes, rework claims, appointment scheduling with DCs—all thread-based SLA pressure.',
    fits: {
      email_automation:
        'Escalate missed appointments or temperature-controlled exceptions faster than backlog browsing.',
      crm_management:
        'Lanes, reps, surcharge agreements—fewer orphaned PDFs forwarded “FYI”.',
      ai_assistant:
        'Turn multi-party failure threads into a tight bulleted recap for escalation calls.',
    },
  },
  {
    id: 'manufacturing-industrial',
    displayName: 'Manufacturing & industrial',
    keywords: [
      'manufacturer',
      'manufacturing',
      'cnc',
      'machine shop ',
      'fabricat',
      'metal fab',
      'precision machin',
      'oem ',
      'job shop ',
      'contract manufactur',
      'packaging manufacture',
      'tool and die ',
      'steel fab',
      'plastic injection',
      'circuit board ',
    ],
    summary:
      'Quotes, BOM clarifications, change orders, quality holds, tooling delays—engineering + sales coexist in forwarded threads.',
    fits: {
      email_automation:
        'Treat RFQs vs rework vs tooling POs distinctly so estimating capacity isn’t random.',
      crm_management:
        'Buyer plants, SKU families, deviations, concessions—readable through personnel changes.',
      ai_assistant:
        'Prep internal release notes distilled from sprawling technical mail before standups.',
    },
  },
  {
    id: 'msp-tech-services',
    displayName: 'IT services & MSPs',
    keywords: [
      'managed service',
      'managed it',
      'managed services',
      'msp ',
      'mssp ',
      'it company',
      'it support',
      'it support company',
      'tech support',
      'help desk',
      'helpdesk',
      'helpdesk outsource',
      'office 365 migra',
      'network operations',
      'cybersecurity serv',
      'vulnerability ',
      'cloud consult',
      'break fix ',
    ],
    summary:
      'Alert fatigue + customer expectations: renewals, project updates, escalation chains—email is still coordination rail for smaller MSPs.',
    fits: {
      email_automation:
        'Bump breach symptoms and total-down events ahead of “quick question about licensing.”',
      crm_management:
        'Stack per client—M365 tenant, backups, PSA tickets—paired with stakeholder mapping.',
      ai_assistant:
        'Incident recap bullets from noisy reply-all chains—before drafting customer comms manually.',
    },
  },
  {
    id: 'staffing-recruiting',
    displayName: 'Staffing & recruiting',
    keywords: [
      'staffing agency',
      'recruit',
      'headhunter',
      'talent acquis',
      'placement firm',
      'temp agency ',
      'workforce solution',
      'executive search',
      'employment agency ',
    ],
    summary:
      'Open reqs, resumes, hiring-manager feedback, calendars, declines—matching volume without dropping candidates is textbook CRM + inbox hygiene.',
    fits: {
      email_automation:
        'Treat active reqs vs dormant accounts so candidates don’t get ghost vibes.',
      crm_management:
        'Requisitions, placements, declines, revisit dates—all visible regardless of recruiter PTO overlap.',
      ai_assistant:
        'Brief hiring managers distilled from recruiter email chains.',
    },
  },
  {
    id: 'saas-tech-product',
    displayName: 'Software & SaaS teams',
    keywords: [
      'saas ',
      'software',
      'b2b software',
      'software startup',
      'software company',
      'product led ',
      'dev tool',
      'api platform ',
      'cloud software',
      'software vendor ',
    ],
    summary:
      'Inbound trials, onboarding questions, escalation engineering, SOC questionnaires—SMB software teams recycle the same nuanced answers endlessly.',
    fits: {
      email_automation:
        'Separate sales discovery from distressed production mail so Sev-1 chatter isn’t masked.',
      crm_management:
        'Organizations, workspaces, admins, invoices—fewer orphaned leads when AEs churn.',
      ai_assistant:
        'Turn long security-review threads into actionable internal checklists—not auto-sent compliance claims.',
    },
  },
  {
    id: 'senior-care',
    displayName: 'Senior living & home care coordination',
    keywords: [
      'assisted liv',
      'memory care ',
      'skilled nursing ',
      'home health ',
      'senior liv',
      'hospice ',
      'caregiving agency',
      'respite care ',
      'companionship care',
    ],
    summary:
      'Families, aides, coordinators, hospice partners—consent-heavy topics still cross email alongside scheduling chaos.',
    fits: {
      email_automation:
        'Treat family portal mail vs clinician escalations cleanly so nights/weekends decompress.',
      crm_management:
        'Who’s payer, guardian, POA—all less scrambled during shift changes.',
      ai_assistant:
        'Summaries for interdisciplinary huddles from accumulated family correspondence—with human review baked in.',
    },
  },
  {
    id: 'events-venues',
    displayName: 'Events, venues & experiences',
    keywords: [
      'event planner',
      'event organizer',
      'event venue ',
      'wedding venue',
      'conference center ',
      'banquet hall',
      'experience design',
      'corporate retreat',
      'festival ',
      'expo ',
      'wedding planner',
      'florist ',
      'photographer',
      'photography',
      'wedding photographer',
      'dj',
      'wedding dj',
      'mobile dj',
    ],
    summary:
      'Timelines slip when vendor threads splinter—inboxes become the unofficial Gantt.',
    fits: {
      email_automation:
        'Bump contract deadlines and payment friction ahead of “nice to meet you” introductions.',
      crm_management:
        'Ceremony couples, planners, decorators, AV partners—all versioned cleanly.',
      ai_assistant:
        'Rebuild day-of rundown bullets from frantic Friday mail—edited before staff broadcast.',
    },
  },
  {
    id: 'cleaning-facilities',
    displayName: 'Cleaning & janitorial',
    keywords: [
      'janitorial',
      'janitor',
      'commercial clean',
      'office clean',
      'housekeep serv',
      'housekeeper',
      'house cleaning',
      'home cleaning',
      'residential cleaning',
      'cleaner',
      'cleaning company',
      'maid',
      'maid service ',
      'carpet cleaning',
      'carpet cleaner',
      'window washing',
      'window cleaning',
      'gutter cleaning',
      'gutter cleaner',
      'chimney sweep',
      'chimney cleaning',
      'post construction clean',
      'window clean commercial',
      'disinfection serv',
      'facility service contract',
      'home organizer',
      'professional organizer',
      'home organization',
    ],
    summary:
      'Scope creep, SLA credits, nightly crew turnover, recurring inspections—all negotiated over email snapshots.',
    fits: {
      email_automation:
        'Treat emergency flood calls ahead of invoicing chatter so rotations stay predictable.',
      crm_management:
        'Sites, square footage assumptions, escalation contacts—all portable when account managers churn.',
      ai_assistant:
        'Quick recap drafts when customers forward photo evidence mid-thread.',
    },
  },
  {
    id: 'food-beverage-supply',
    displayName: 'Distribution, CPG & production',
    keywords: [
      'food and beverage',
      'food beverage',
      'f b distributor',
      'beverage distributor',
      'beverage distribution',
      'food distributor',
      'food distribution',
      'food wholesaler',
      'food wholesale',
      'food manufacturing',
      'food manufacturer',
      'food processor',
      'food processing',
      'bottling',
      'brewery supply',
      'cpg',
      'consumer packaged goods',
      'snack food',
      'ingredient supplier',
      'broadline',
      'cold chain',
      'perishable',
    ],
    summary:
      'PO confirmations, lot tracing, retailer chargebacks, and carrier delays stack up in threads—buyers expect same-day answers even when your team is in the plant or on the road.',
    fits: {
      email_automation:
        'Route retailer deductions, sample requests, and carrier updates separately so account reps are not re-triaging the same inbox.',
      crm_management:
        'Buyers, distributors, brokers, and plants stay tied to the right SKUs, pricing tiers, and delivery windows.',
      ai_assistant:
        'Condense multi-party shortage threads into what changed, who owns next steps, and what to tell the buyer.',
    },
  },
  {
    id: 'field-service-dispatch',
    displayName: 'Field crews & dispatch',
    keywords: [
      'field service',
      'field services',
      'field technician',
      'service industry',
      'mobile service',
      'on site service',
      'on-site service',
      'service call',
      'service calls',
      'dispatch',
      'dispatcher',
      'work order',
      'work orders',
      'route ticket',
      'truck roll',
      'service van',
      'installation service',
      'preventive maintenance',
      'pm schedule',
      'break fix',
    ],
    summary:
      'Dispatchers juggle SLA timers, parts availability, and “on my way” updates—most of it still lives in email and texts rather than a clean ticket board.',
    fits: {
      email_automation:
        'Separate emergency dispatches from billing and parts chatter so techs see the next job faster.',
      crm_management:
        'Sites, assets, contracts, and revisit intervals stay visible when crews or coordinators change.',
      ai_assistant:
        'Turn messy job threads into a short handoff note before the tech arrives on site.',
    },
  },
  {
    id: 'b2b-business-services',
    displayName: 'Consulting & outsourced operations',
    keywords: [
      'b2b services',
      'b2b service',
      'business services',
      'business service',
      'consulting firm',
      'management consulting',
      'management consult',
      'strategy consulting',
      'operations consulting',
      'advisory firm',
      'advisory services',
      'implementation partner',
      'implementation services',
      'outsourced operations',
      'business process outsourcing',
      'bpo',
      'fractional coo',
      'fractional cfo',
      'fractional executive',
      'hr consulting',
      'sales consulting',
      'revenue operations',
      'revops',
      'virtual assistant',
      'virtual assistants',
      'va services',
      'executive assistant services',
      'business coach',
      'business coaching',
    ],
    summary:
      'Proposals, SOW changes, stakeholder approvals, and delivery status all ride email—client work breaks when threads are the system of record.',
    fits: {
      email_automation:
        'Separate new business, active engagements, and AR/collections so partners are not context-switching all day.',
      crm_management:
        'Accounts, stakeholders, SOW milestones, and renewal risk stay in one place across managers.',
      ai_assistant:
        'Prep engagement recaps from long client threads before QBRs—your team approves what goes out.',
    },
  },
  {
    id: 'agriculture',
    displayName: 'Agriculture & producers',
    keywords: [
      'farm ',
      'row crop ',
      'greenhouse ',
      'nursery ',
      'vineyard ',
      'winery ',
      'orchard ',
      'ranch ',
      'livestock ',
      'grain elevator',
      'ag coop',
      'agronom',
      'equipment dealer',
    ],
    summary:
      'Weather windows, coop contracts, equipment dealer mail, inspectors—thin margins don’t tolerate “we’ll circle back Tuesday.”',
    fits: {
      email_automation:
        'Prioritize outages (power, coolers, recalls) separately from quoting season chatter.',
      crm_management:
        'Fields/lots/contracts/futures fewer orphan threads when interns rotate harvest weeks.',
      ai_assistant:
        'Condense forwarded regulatory PDF chatter into actionable checklists—not legal interpretations.',
    },
  },
]

const SECTOR_CATEGORIES: Record<string, string> = {
  'landscaping-field': 'Service industry',
  'restaurant-hospitality': 'Food & beverage',
  'food-beverage-supply': 'Food & beverage',
  'medical-clinical': 'Healthcare',
  'trades-home': 'Service industry',
  'field-service-dispatch': 'Service industry',
  'professional-services': 'B2B & professional',
  'b2b-business-services': 'B2B services',
  'creative-marketing-agency': 'B2B services',
  'creator-media': 'Media & creators',
  retail: 'Retail & commerce',
  'real-estate': 'Real estate',
  'fitness-wellness': 'Wellness & fitness',
  'education-training': 'Education & training',
  automotive: 'Automotive',
  insurance: 'Insurance & benefits',
  nonprofit: 'Nonprofit & civic',
  'logistics-supply-chain': 'Logistics & supply chain',
  'manufacturing-industrial': 'Manufacturing',
  'msp-tech-services': 'Technology services',
  'staffing-recruiting': 'Staffing & recruiting',
  'saas-tech-product': 'Software & SaaS',
  'senior-care': 'Healthcare',
  'events-venues': 'Events & venues',
  'cleaning-facilities': 'Service industry',
  agriculture: 'Agriculture',
}


const SCORING_SECTORS: SectorScoring[] = SECTOR_SOURCE.map((s) => ({
  ...s,
  category: SECTOR_CATEGORIES[s.id] ?? 'General business',
  positiveKeywords: compileKeywords(s.keywords),
}))

function phraseTokensHit(phrase: string, tokenSet: Set<string>, tokens: string[]): boolean {
  const pTokens = phrase.split(/\s+/).filter(Boolean)
  if (pTokens.length === 0) return false
  return pTokens.every((pt) => {
    if (tokenSet.has(pt)) return true
    if (INTENTIONAL_PREFIXES.has(pt)) {
      return tokens.some((t) => t.startsWith(pt) && pt.length >= 4)
    }
    // Allow one connector flexibility: already normalized "and" etc.
    return false
  })
}

function orderedPhraseLooseHit(phrase: string, matchingInput: string): boolean {
  // Phrase with optional "and" / hyphen connectors already normalized
  const compactPhrase = phrase.replace(/\band\b/g, ' ').replace(/\s+/g, ' ').trim()
  const compactQuery = matchingInput.replace(/\band\b/g, ' ').replace(/\s+/g, ' ').trim()
  if (compactQuery.includes(compactPhrase)) return true
  const pTokens = compactPhrase.split(' ').filter(Boolean)
  const qTokens = compactQuery.split(' ').filter(Boolean)
  if (pTokens.length < 2) return false
  let qi = 0
  for (const pt of pTokens) {
    let found = false
    while (qi < qTokens.length) {
      const qt = qTokens[qi]
      qi += 1
      if (qt === pt || (INTENTIONAL_PREFIXES.has(pt) && pt.length >= 4 && qt.startsWith(pt))) {
        found = true
        break
      }
    }
    if (!found) return false
  }
  return true
}

type ConceptHit = { conceptId: string; weight: number; kind: KeywordMatchType }

export function scoreSectorMatch(matchingInput: string, sector: SectorScoring): {
  score: number
  conceptCount: number
  strongestWeight: number
  strongestKind: KeywordMatchType | null
} {
  if (!matchingInput) {
    return { score: 0, conceptCount: 0, strongestWeight: 0, strongestKind: null }
  }

  const tokens = tokenizeMatching(matchingInput)
  const tokenSet = new Set(tokens)
  const bestByConcept = new Map<string, ConceptHit>()

  const consider = (hit: ConceptHit) => {
    const prev = bestByConcept.get(hit.conceptId)
    if (!prev || hit.weight > prev.weight) {
      bestByConcept.set(hit.conceptId, hit)
    }
  }

  for (const kw of sector.positiveKeywords) {
    if (WEAK_SINGLE_WORDS.has(kw.value) && kw.type !== 'phrase') {
      // Weak singles never create sector evidence alone / at all as tokens
      continue
    }

    if (matchingInput === kw.value) {
      // Bare intentional stems are not whole-input aliases — keep prefix weight
      if (kw.type === 'prefix') {
        consider({ conceptId: kw.conceptId, weight: kw.weight, kind: 'prefix' })
      } else {
        consider({ conceptId: kw.conceptId, weight: Math.max(kw.weight, 12), kind: 'exact' })
      }
      continue
    }

    if (kw.type === 'phrase') {
      if (matchingInput.includes(kw.value) || phraseTokensHit(kw.value, tokenSet, tokens)) {
        consider({ conceptId: kw.conceptId, weight: kw.weight, kind: 'phrase' })
      } else if (orderedPhraseLooseHit(kw.value, matchingInput)) {
        consider({ conceptId: kw.conceptId, weight: Math.min(kw.weight, 8), kind: 'phrase' })
      }
      continue
    }

    if (kw.type === 'prefix') {
      if (kw.value.length < 4) continue
      const matchedToken = tokens.find((t) => t.startsWith(kw.value))
      if (matchedToken) {
        // Morphological extension (landscap → landscaping) is strong; bare stem alone stays weaker
        const extended = matchedToken.length > kw.value.length
        const weight = extended ? Math.max(kw.weight, 10) : kw.weight
        const kind: KeywordMatchType = extended ? 'token' : 'prefix'
        consider({ conceptId: kw.conceptId, weight, kind })
      }
      continue
    }

    // token / exact-as-token
    if (tokenSet.has(kw.value)) {
      const weight = APPROVED_SHORT_TERMS.has(kw.value) ? Math.max(kw.weight, 10) : kw.weight
      consider({ conceptId: kw.conceptId, weight, kind: 'token' })
    }
  }

  let score = 0
  let strongestWeight = 0
  let strongestKind: KeywordMatchType | null = null
  for (const hit of bestByConcept.values()) {
    score += hit.weight
    if (hit.weight > strongestWeight) {
      strongestWeight = hit.weight
      strongestKind = hit.kind
    }
  }

  return {
    score,
    conceptCount: bestByConcept.size,
    strongestWeight,
    strongestKind,
  }
}

type RankedSector = {
  sector: SectorScoring
  score: number
  conceptCount: number
  strongestWeight: number
  strongestKind: KeywordMatchType | null
}

function rankSectorMatches(matchingInput: string): RankedSector[] {
  return SCORING_SECTORS.map((sector) => {
    const result = scoreSectorMatch(matchingInput, sector)
    return { sector, ...result }
  })
    .filter((row) => row.score > 0)
    .sort((a, b) => b.score - a.score || b.conceptCount - a.conceptCount)
}

function featuresFromFits(fits: Record<FeatureFitId, string>): FeatureFit[] {
  return FEATURE_ORDER.map((id) => ({
    id,
    title: FEATURE_LABELS[id],
    fit: fits[id],
  }))
}

function idlePresentation(): SectorFitPresentation {
  return {
    status: 'idle',
    reasonCode: 'EMPTY',
    headline: 'Tell us what your business does',
    matchStrength: null,
    category: null,
    sectorId: null,
    needsMoreDetail: false,
    ambiguousAlternates: null,
    summary:
      'Enter a business type or briefly explain what you sell, provide, repair, manage, or organize.',
    featuresOrdered: featuresFromFits(FALLBACK_FITS),
  }
}

function invalidPresentation(reasonCode: SectorInputReasonCode): SectorFitPresentation {
  return {
    status: 'invalid',
    reasonCode,
    headline: 'We need a clearer business description',
    matchStrength: null,
    category: null,
    sectorId: null,
    needsMoreDetail: false,
    ambiguousAlternates: null,
    summary: 'Please enter a real business type or a short description of what the business does.',
    featuresOrdered: featuresFromFits(FALLBACK_FITS),
  }
}

function needsDetailPresentation(
  reasonCode: SectorInputReasonCode,
  summary?: string
): SectorFitPresentation {
  const unsupportedLanguage = reasonCode === 'UNSUPPORTED_LANGUAGE'
  return {
    status: 'needs_detail',
    reasonCode,
    headline: 'Tell us a little more',
    matchStrength: null,
    category: null,
    sectorId: null,
    needsMoreDetail: true,
    ambiguousAlternates: null,
    summary:
      summary ??
      (unsupportedLanguage
        ? 'We could not confidently interpret that description yet. Please describe what the business sells or does in English, such as “commercial cleaning company” or “online clothing store.”'
        : 'What does the business sell or provide, and who does it serve?'),
    featuresOrdered: featuresFromFits(FALLBACK_FITS),
  }
}

function unsupportedPresentation(): SectorFitPresentation {
  return {
    status: 'unsupported',
    reasonCode: 'NO_SUPPORTED_SECTOR',
    headline: 'We do not have a specific sector match yet',
    matchStrength: null,
    category: null,
    sectorId: null,
    needsMoreDetail: true,
    ambiguousAlternates: null,
    summary:
      'Your business may still benefit from automation. Tell us how you currently handle inquiries, leads, follow-ups, scheduling, or repetitive administrative work.',
    featuresOrdered: featuresFromFits(FALLBACK_FITS),
  }
}

function ambiguousPresentation(alternates: RankedSector[]): SectorFitPresentation {
  const top = alternates.slice(0, 3)
  const names = top.map((r) => r.sector.displayName)
  const nameList =
    names.length === 2
      ? `${names[0]} or ${names[1]}`
      : names.length > 2
        ? `${names.slice(0, -1).join(', ')}, or ${names[names.length - 1]}`
        : names[0] ?? 'more than one sector'
  return {
    status: 'ambiguous',
    reasonCode: 'AMBIGUOUS_SECTORS',
    headline: 'We found a few possible matches',
    matchStrength: null,
    category: null,
    sectorId: null,
    needsMoreDetail: true,
    ambiguousAlternates: top.map((r) => ({
      id: r.sector.id,
      displayName: r.sector.displayName,
    })),
    summary: `This could fit ${nameList}. Tell us whether you primarily serve customers, distribute products, organize events, or something else so we map the right playbook.`,
    featuresOrdered: featuresFromFits(FALLBACK_FITS),
  }
}

function matchedPresentation(best: RankedSector, strength: 'high' | 'medium'): SectorFitPresentation {
  const category = best.sector.category
  return {
    status: 'matched',
    reasonCode: 'VALID_MATCH',
    headline: `Matched fit • ${category} — ${best.sector.displayName}`,
    matchStrength: strength,
    category,
    sectorId: best.sector.id,
    needsMoreDetail: false,
    ambiguousAlternates: null,
    summary: best.sector.summary,
    featuresOrdered: featuresFromFits(best.sector.fits),
  }
}

/**
 * Central processing entry: normalize → viability → match → presentation.
 */
export function analyzeSectorInput(rawInput: string): SectorInputAnalysis {
  const cappedRaw = rawInput.slice(0, MAX_RAW_INPUT_CHARS)
  const rawLength = cappedRaw.length
  const normalizedInput = normalizeForValidation(cappedRaw)
  let matchingInput = normalizeForMatching(cappedRaw)
  if (matchingInput.length > MAX_MATCHING_INPUT_CHARS) {
    matchingInput = matchingInput.slice(0, MAX_MATCHING_INPUT_CHARS).trim()
  }

  const viability = assessViability(cappedRaw, normalizedInput, matchingInput)
  if (viability) {
    let presentation: SectorFitPresentation
    if (viability.status === 'empty') {
      presentation = idlePresentation()
    } else if (
      viability.status === 'nonsensical' ||
      viability.status === 'too_short' ||
      viability.reasonCode === 'NO_MEANINGFUL_CHARACTERS' ||
      viability.reasonCode === 'ONLY_NUMBERS' ||
      viability.reasonCode === 'MOSTLY_SYMBOLS' ||
      viability.reasonCode === 'REPEATED_CHARACTER_SEQUENCE' ||
      viability.reasonCode === 'KEYBOARD_MASH' ||
      viability.reasonCode === 'TOO_SHORT'
    ) {
      presentation = invalidPresentation(viability.reasonCode)
    } else {
      presentation = needsDetailPresentation(viability.reasonCode)
    }
    return {
      rawLength,
      normalizedInput,
      matchingInput,
      status: viability.status === 'empty' ? 'empty' : viability.status,
      reasonCode: viability.reasonCode,
      presentation,
    }
  }

  const ranked = rankSectorMatches(matchingInput)
  const best = ranked[0] ?? null

  if (!best || best.score < MIN_SCORE_MEDIUM) {
    // Viable language but no sector evidence → unsupported (or still needs detail if very generic)
    const tokens = tokenizeMatching(matchingInput)
    const hasDistinctive = tokens.some(
      (t) => !WEAK_SINGLE_WORDS.has(t) && !BUSINESS_CONTEXT_TERMS.has(t) && t.length >= 4
    )
    if (!hasDistinctive) {
      const presentation = needsDetailPresentation('INSUFFICIENT_INFORMATION')
      return {
        rawLength,
        normalizedInput,
        matchingInput,
        status: 'low_information',
        reasonCode: 'INSUFFICIENT_INFORMATION',
        presentation,
      }
    }
    const presentation = unsupportedPresentation()
    return {
      rawLength,
      normalizedInput,
      matchingInput,
      status: 'unsupported',
      reasonCode: 'NO_SUPPORTED_SECTOR',
      presentation,
    }
  }

  // Ambiguity: all peers within margin that clear medium threshold
  const ambiguousPeers = ranked.filter(
    (row) =>
      row.score >= MIN_SCORE_MEDIUM &&
      best.score - row.score < AMBIGUITY_SCORE_MARGIN
  )

  if (ambiguousPeers.length >= 2) {
    const presentation = ambiguousPresentation(ambiguousPeers)
    return {
      rawLength,
      normalizedInput,
      matchingInput,
      status: 'ambiguous',
      reasonCode: 'AMBIGUOUS_SECTORS',
      presentation,
    }
  }

  // Confidence
  const weakOnly =
    best.conceptCount === 1 &&
    best.strongestKind === 'prefix' &&
    best.score < MIN_SCORE_HIGH

  if (weakOnly) {
    const presentation = needsDetailPresentation(
      'INSUFFICIENT_INFORMATION',
      'We picked up a partial signal—add one concrete detail (what you sell, who you serve, or how leads arrive) so we can map the right playbook.'
    )
    return {
      rawLength,
      normalizedInput,
      matchingInput,
      status: 'low_information',
      reasonCode: 'INSUFFICIENT_INFORMATION',
      presentation,
    }
  }

  const hasStrongSignal =
    best.strongestKind === 'exact' ||
    best.strongestKind === 'phrase' ||
    best.strongestKind === 'token' ||
    (best.strongestKind === 'prefix' && best.conceptCount >= 2)

  const strength: 'high' | 'medium' =
    best.score >= MIN_SCORE_HIGH && hasStrongSignal && best.strongestKind !== 'prefix'
      ? 'high'
      : 'medium'

  // Require high to lead runner-up safely (already non-ambiguous)
  const presentation = matchedPresentation(best, strength)
  return {
    rawLength,
    normalizedInput,
    matchingInput,
    status: 'matched',
    reasonCode: 'VALID_MATCH',
    presentation,
  }
}

/**
 * Compatibility wrapper — prefer analyzeSectorInput for new code.
 * Maps analysis presentation into the historical SectorFitPresentation shape used by the UI.
 */
export function getSectorFitPresentation(queryRaw: string): SectorFitPresentation {
  return analyzeSectorInput(queryRaw).presentation
}

/** Test helper: score a sector by id against a normalized/matching query string */
export function scoreSectorMatchById(
  matchingInput: string,
  sectorId: string
): number {
  const sector = SCORING_SECTORS.find((s) => s.id === sectorId)
  if (!sector) return 0
  return scoreSectorMatch(matchingInput, sector).score
}

/** Read-only catalog snapshot for integrity / regression gates (compiled keywords). */
export type SectorCatalogEntry = {
  id: string
  displayName: string
  category: string
  summary: string
  fits: Record<FeatureFitId, string>
  keywords: ReadonlyArray<SectorKeyword>
}

export function listSectorCatalog(): ReadonlyArray<SectorCatalogEntry> {
  return SCORING_SECTORS.map((s) => ({
    id: s.id,
    displayName: s.displayName,
    category: s.category,
    summary: s.summary,
    fits: { ...s.fits },
    keywords: s.positiveKeywords.map((k) => ({ ...k })),
  }))
}

export const FEATURE_FIT_IDS: ReadonlyArray<FeatureFitId> = [
  'email_automation',
  'crm_management',
  'ai_assistant',
]

