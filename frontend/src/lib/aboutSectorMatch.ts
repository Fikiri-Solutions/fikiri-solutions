/**
 * Lightweight sector → feature fit matcher for the public About page.
 * Keyword/substring scoring only (no backend, no AI) — recommendations come from
 * fixed templates per sector, never generated prose (no hallucinated “fits”).
 * Cast wide via many sector rows + keywords; stay honest via weak-word filters,
 * score thresholds, and ambiguity detection when two verticals tie.
 */

export type FeatureFitId = 'email_automation' | 'crm_management' | 'ai_assistant'

const FEATURE_LABELS: Record<FeatureFitId, string> = {
  email_automation: 'Email Automation',
  crm_management: 'CRM Management',
  ai_assistant: 'AI Assistant',
}

type SectorTemplate = {
  id: string
  displayName: string
  keywords: string[]
  /** One short paragraph: real workflow pain, not marketing fluff */
  summary: string
  fits: Record<FeatureFitId, string>
}

type SectorScoring = SectorTemplate & {
  /** Top-level bucket (Automotive, Food & beverage, B2B services, …) */
  category: string
  /** Pre-normalized keyword phrases (see normalizeQuery) */
  normalizedPhrases: string[]
}

/** Single words too vague to match alone — avoids “service company” → random vertical */
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
])

/** If the top two sectors score within this margin, ask for detail instead of guessing */
const AMBIGUITY_SCORE_MARGIN = 3

const FALLBACK_SUMMARY =
  'Most teams we work with live in email for leads, scheduling, quotes, vendors, or renewals. Name your sector (even loosely)—we map it to how inbox automation, CRM structure, and assistant-style help usually land first.'

const FALLBACK_FITS: Record<FeatureFitId, string> = {
  email_automation:
    'Surface urgent threads first and cut down on copy-paste so responses go out the same day.',
  crm_management:
    'One thread of truth per contact: who spoke last, what’s pending, and what stage the relationship is in.',
  ai_assistant:
    'Turn long threads into short internal briefs and suggested next steps—your team sends the final message.',
}

function stripCombiningMarks(value: string): string {
  try {
    return value.replace(/\p{M}+/gu, '')
  } catch {
    // Older browsers without Unicode property escapes still get NFKD decomposition.
    return value
  }
}

function normalizeQuery(raw: string): string {
  return stripCombiningMarks(raw.normalize('NFKD'))
    .toLowerCase()
    .replace(/[&]+/g, ' and ')
    .replace(/[^a-z0-9\s-+]+/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/** Source-of-truth sector rows; summaries tuned to typical SMB operational patterns in each vertical */
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
      'catering',
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
      'vet clinic',
      'animal hospital',
      'chiropract',
      'podiatrist',
      'dermatolog',
      'ophthalmolog',
      'optometr',
      'med spa',
      'medspa',
      'plastic surgery',
      'pharmacy',
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
      'hvac',
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
      'barbershop',
      ' nail salon',
      'spa ',
      'day spa',
      'massage therapy',
      'med spa',
      'aesthetics',
      'waxing ',
      'lashes',
      'grooming',
      'boutique spa',
      'tanning ',
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
      'used car',
      'auto sales',
      'parts department',
      'automotive detailing',
      'detail shop',
      'tow company',
      'towing',
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
      'msp ',
      'mssp ',
      'it support company',
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
      'commercial clean',
      'office clean',
      'housekeep serv',
      'maid service ',
      'post construction clean',
      'window clean commercial',
      'disinfection serv',
      'facility service contract',
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
  normalizedPhrases: s.keywords.map((k) => normalizeQuery(k)).filter((p) => p.length >= 2),
}))

export function scoreSectorMatch(normalizedQuery: string, sector: SectorScoring): number {
  if (!normalizedQuery) return 0
  let score = 0
  const q = normalizedQuery
  const words = q.split(/\s+/).filter((w) => w.length >= 2)

  for (const p of sector.normalizedPhrases) {
    if (p.length < 2) continue
    const isSingleWord = !p.includes(' ')
    if (isSingleWord && WEAK_SINGLE_WORDS.has(p)) continue

    // Whole-query equals a keyword ("hvac", "trainer", "gym") — strong single-word sector signal
    if (q === p) {
      score += 10
      continue
    }
    if (q.includes(p)) {
      if (isSingleWord && WEAK_SINGLE_WORDS.has(p)) continue
      score += Math.min(12, Math.max(3, Math.round(p.length * 1.5)))
      continue
    }
    const pTokens = p.split(/\s+/).filter(Boolean)
    const allTokensHit = pTokens.every((tok) =>
      words.some((w) => w === tok || (tok.length >= 4 && (w.includes(tok) || tok.includes(w))))
    )
    if (pTokens.length > 1 && allTokensHit) {
      score += 5
      continue
    }
    if (isSingleWord && WEAK_SINGLE_WORDS.has(p)) continue

    const wordHit =
      words.some((w) => w === p) ||
      words.some((w) => w.length >= 4 && (w.startsWith(p) || (p.length >= 4 && w.includes(p))))
    if (wordHit) score += 3
  }
  return score
}

function rankSectorMatches(normalized: string): Array<{ sector: SectorScoring; score: number }> {
  return SCORING_SECTORS.map((sector) => ({
    sector,
    score: scoreSectorMatch(normalized, sector),
  }))
    .filter((row) => row.score > 0)
    .sort((a, b) => b.score - a.score)
}

export type SectorFitPresentation = {
  headline: string
  matchStrength: 'high' | 'medium' | 'broad'
  /** Top-level bucket when confidently matched */
  category: string | null
  /** True when we have input but could not map to a sector template confidently */
  needsMoreDetail: boolean
  /** Set when two sectors score similarly — we ask for detail instead of guessing */
  ambiguousAlternates: ReadonlyArray<string> | null
  summary: string
  featuresOrdered: ReadonlyArray<{
    id: FeatureFitId
    title: string
    fit: string
  }>
}

/** Minimum primary description length before we ask for follow-up context */
export const MIN_PRIMARY_CHARS_FOR_FOLLOW_UP = 6

export function combineSectorQueries(primary: string, additional: string): string {
  const parts = [primary.trim(), additional.trim()].filter((p) => p.length > 0)
  return parts.join(' ')
}

const FEATURE_ORDER: FeatureFitId[] = ['email_automation', 'crm_management', 'ai_assistant']

/** Slightly tighter than early versions: broader index ⇒ more accidental hits without intent */
const MIN_SCORE_HIGH = 10
const MIN_SCORE_MEDIUM = 6

function fallbackPresentation(
  queryRaw: string,
  normalized: string,
  opts?: { ambiguousAlternates?: string[]; summary?: string }
): SectorFitPresentation {
  const headline = normalized ? `What could help • “${truncateDisplay(queryRaw.trim(), 48)}”` : 'Tell us what you do'
  const summary =
    opts?.summary ??
    (normalized
      ? 'Add your industry or how leads reach you in the box below—we’ll map Email Automation, CRM, and AI Assistant to workflows that fit.'
      : FALLBACK_SUMMARY)
  return {
    headline,
    matchStrength: 'broad',
    category: null,
    needsMoreDetail: Boolean(normalized),
    ambiguousAlternates: opts?.ambiguousAlternates ?? null,
    summary,
    featuresOrdered: FEATURE_ORDER.map((id) => ({
      id,
      title: FEATURE_LABELS[id],
      fit: FALLBACK_FITS[id],
    })),
  }
}

export function getSectorFitPresentation(queryRaw: string): SectorFitPresentation {
  const normalized = normalizeQuery(queryRaw)
  const ranked = rankSectorMatches(normalized)
  const best = ranked[0] ?? null
  const second = ranked[1] ?? null

  if (!normalized || !best || best.score < MIN_SCORE_MEDIUM) {
    return fallbackPresentation(queryRaw, normalized)
  }

  const isAmbiguous =
    second !== null &&
    second.score >= MIN_SCORE_MEDIUM &&
    best.score - second.score < AMBIGUITY_SCORE_MARGIN

  if (isAmbiguous) {
    const a = best.sector.displayName
    const b = second.sector.displayName
    return fallbackPresentation(queryRaw, normalized, {
      ambiguousAlternates: [a, b],
      summary: `That could fit ${a} or ${b}. Add one concrete detail—what you sell, who buys it, and how inquiries arrive—so we map the right playbook instead of guessing.`,
    })
  }

  const strength = best.score >= MIN_SCORE_HIGH ? 'high' : 'medium'
  const category = best.sector.category
  return {
    headline: `Matched fit • ${category} — ${best.sector.displayName}`,
    matchStrength: strength,
    category,
    needsMoreDetail: false,
    ambiguousAlternates: null,
    summary: best.sector.summary,
    featuresOrdered: FEATURE_ORDER.map((id) => ({
      id,
      title: FEATURE_LABELS[id],
      fit: best.sector.fits[id],
    })),
  }
}

function truncateDisplay(s: string, maxLen: number): string {
  if (s.length <= maxLen) return s
  return `${s.slice(0, Math.max(0, maxLen - 1)).trim()}…`
}
