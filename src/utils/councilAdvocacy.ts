/**
 * Accessibility Advocacy & Environmental Modification Engine
 * Compliance Standards:
 *  - AS 1428.1: Design for access and mobility - Luminance contrast criteria (>= 30% LRV difference)
 *  - Victorian Dementia-Friendly Communities Policy & Design Principles (DFFH Victoria)
 *  - Dementia Australia Environmental Design Toolkit (Corridors, Entrances & Living Spaces)
 */

import { 
  classifySpatialBarrier, 
  SPATIAL_HAZARD_TAXONOMY, 
  type StandardHazardCategory, 
  type ClassifiedSpatialHazard 
} from './barrierTaxonomy'

export { classifySpatialBarrier, SPATIAL_HAZARD_TAXONOMY, type StandardHazardCategory, type ClassifiedSpatialHazard }

export interface BarrierStatistic {
  id: string
  title: string
  category: string
  taxonomyCode: string
  taxonomyCategory: StandardHazardCategory
  icon: string
  detectedLrv: number
  targetLrv: string
  isCompliant: boolean
  citation: string
  issue: string
  recommendation: string
  cognitiveRamification: string
}

export interface CouncilContact {
  council_name: string
  ceo_name: string
  mayor_name: string | null
  deputy_mayor_name: string | null
  telephone: string
  email: string | null
  website: string
  postal_address: string
  postal_suburb: string
  postcode: string
}

export interface EmailDraftPayload {
  recipientCouncil: CouncilContact
  senderName: string
  senderEmail: string
  locationName: string
  facilityType: string
  barriers: BarrierStatistic[]
  customNotes?: string
}

export interface HomeRenovationPlanPayload {
  roomName: string
  roomType: string
  residentName?: string
  contactEmail?: string
  barriers: BarrierStatistic[]
  personalNotes?: string
}

/**
 * Extracts clear barrier summary statistics from raw computer vision audit suggestions
 * and categorizes them through the standardized environmental taxonomy.
 */
export function extractBarrierStatistics(suggestions: any[]): BarrierStatistic[] {
  if (!suggestions || suggestions.length === 0) {
    return []
  }

  return suggestions.map((sug, idx) => {
    const classified = classifySpatialBarrier(sug, idx)

    return {
      id: classified.id,
      title: classified.title,
      category: classified.category,
      taxonomyCode: classified.taxonomyCode,
      taxonomyCategory: classified.category,
      icon: classified.icon,
      detectedLrv: classified.detectedLrv,
      targetLrv: classified.targetLrvRule,
      isCompliant: classified.isCompliant,
      citation: `${classified.standardRef} (${classified.standardClause})`,
      issue: classified.cognitiveRamification,
      recommendation: classified.remedyRecommendation,
      cognitiveRamification: classified.cognitiveRamification
    }
  })
}

/**
 * Generates an actionable Home Renovation & Caregiver Modification Plan
 * for indoor private rooms (living room, hallway, bedroom, bathroom, kitchen).
 * Formatted specifically for family caregivers, occupational therapists (OT), and home renovation specialists.
 */
export function generateHomeRenovationPlan(payload: HomeRenovationPlanPayload): { subject: string; summary: string; text: string } {
  const {
    roomName,
    roomType,
    residentName,
    barriers,
    personalNotes
  } = payload

  const label = roomName || roomType || 'Private Home Room'
  const subject = `Home Accessibility & Modification Plan: ${label}`

  const barrierItems = barriers.map((b, i) => {
    const codeTag = b.taxonomyCode ? ` [${b.taxonomyCode}]` : ''
    return `Item ${i + 1}: ${b.title}${codeTag}
• Category: ${b.taxonomyCategory || b.category}
• Measured Contrast: ${b.detectedLrv}% LRV (Standard Target: ${b.targetLrv})
• Identified Difficulty: ${b.cognitiveRamification || b.issue}
• Recommended Renovation / Fix: ${b.recommendation}
• Design Standard Reference: ${b.citation}`
  }).join('\n\n')

  const notesSection = personalNotes && personalNotes.trim().length > 0
    ? `\nPersonal Resident Observations & Daily Routine Notes:\n${personalNotes.trim()}\n`
    : ''

  const summary = `Identified ${barriers.length} environmental barrier${barriers.length === 1 ? '' : 's'} across ${label} requiring visual contrast enhancement or glare mitigation.`

  const text = `===================================================================
HOME ACCESSIBILITY & DEMENTIA-FRIENDLY RENOVATION PLAN
===================================================================
Space Assessed: ${label} (${roomType || 'Private Residence'})
Resident / Homeowner: ${residentName || 'Resident'}
Assessment Date: ${new Date().toLocaleDateString('en-AU', { day: '2-digit', month: 'short', year: 'numeric' })}
Guidelines: Dementia Australia Environmental Design Toolkit & AS 1428.1

PURPOSE OF THIS REPORT:
This modification plan is prepared for family caregivers, occupational therapists, and home renovation specialists (painters, carpenters, electricians). It details environmental adjustments designed to reduce confusion, eliminate disorientation, and minimize slip/trip hazards for people living with cognitive decline or age-related visual changes.

-------------------------------------------------------------------
IDENTIFIED ENVIRONMENTAL ADJUSTMENTS & SPECIFICATIONS:
-------------------------------------------------------------------

${barrierItems.length > 0 ? barrierItems : 'No significant visual or glare barriers detected in this area.'}
${notesSection}
-------------------------------------------------------------------
KEY RECOMMENDATIONS FOR CONTRACTORS & CAREGIVERS:
-------------------------------------------------------------------
1. LUMINANCE CONTRAST (LRV): Ensure a minimum 30% Light Reflectance Value difference between doorways/architraves and adjoining walls. Paint door frames or skirting boards in contrasting tones so thresholds are easily identified.
2. GLARE ELIMINATION: Replace high-gloss floor finishes with matte or satin sealants. Strong specular reflections often appear as deep holes or wet puddles, triggering gait hesitation and anxiety.
3. CLEAR PATHWAYS & HARDWARE: Upgrade light switches and door handles with high-contrast surrounds (e.g. dark switch plates on light walls) to support independence without searching.

Generated via NeighbourlyMinds Home Accessibility Assistant
===================================================================`

  return { subject, summary, text }
}

/**
 * Builds a polite, professionally formatted advocacy email draft for Victorian public spaces.
 * Ready for the user to review, copy, or open directly in their own email client.
 */
export function generateCouncilEmailDraft(payload: EmailDraftPayload): { subject: string; body: string } {
  const {
    recipientCouncil,
    senderName,
    senderEmail,
    locationName,
    facilityType,
    barriers,
    customNotes
  } = payload

  const councilName = recipientCouncil.council_name || 'Local Council'
  const contactEmail = recipientCouncil.email || 'enquiries@vic.gov.au'

  const subject = `Accessibility Feedback: Enhancing Visual Contrast & Dementia-Friendly Corridors at ${locationName}`

  const barrierBulletPoints = barriers.map((b, i) => {
    const codeTag = b.taxonomyCode ? ` [${b.taxonomyCode}]` : ''
    return `${i + 1}. ${b.title}${codeTag}
   - Category: ${b.taxonomyCategory || b.category}
   - Observed Metric: ${b.detectedLrv}% LRV (Benchmark Target: ${b.targetLrv})
   - Standard Reference: ${b.citation}
   - Cognitive Impact: ${b.cognitiveRamification || b.issue}
   - Proposed Solution: ${b.recommendation}`
  }).join('\n\n')

  const notesSection = customNotes && customNotes.trim().length > 0
    ? `\nAdditional Community Observations:\n${customNotes.trim()}\n`
    : ''

  const body = `Dear ${councilName} Infrastructure & Accessibility Team,

I am writing as a local community member and accessibility advocate. During a recent visit to ${locationName} (${facilityType}), I observed spatial and visual contrast features that may present navigation challenges and safety hazards for community members experiencing dementia or age-related visual changes.

Using an assistive environmental contrast auditor based on Victorian Dementia-Friendly Community principles and AS 1428.1, I reviewed the space and identified the following points that would benefit from minor adjustments:

${barrierBulletPoints}
${notesSection}
Official Guidelines Context:
Under Australian Standard AS 1428.1 (Design for Access and Mobility) and the Victorian Government Dementia-Friendly Communities Policy, providing clear luminance contrast (a minimum of 30% LRV difference) on doorway frames and wall-floor boundaries, and eliminating specular glare on polished surfaces, are recognized as high-impact, low-cost modifications. These measures prevent gait-freezing, reduce fall risks, and support community independence.

I would appreciate it if your facilities and maintenance team could review these areas during your upcoming maintenance schedule. Small enhancements, such as contrasting door frame trims or matte surface treatments, make public spaces safer and more welcoming for all residents.

Thank you for your ongoing commitment to building an inclusive and accessible municipality.

Kind regards,

${senderName || 'Community Member'}
${senderEmail ? `Email: ${senderEmail}\n` : ''}Date of Review: ${new Date().toLocaleDateString('en-AU', { day: '2-digit', month: 'short', year: 'numeric' })}
Generated via NeighbourlyMinds Civic Hub
`

  return { subject, body }
}
