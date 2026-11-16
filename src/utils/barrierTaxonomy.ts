/**
 * Public Spatial Hazard Categorizer Taxonomy Engine
 * Standardizes spatial barriers into structured accessibility categories.
 * Benchmarked against:
 *   - AS 1428.1:2021 (Design for access and mobility - General requirements for access)
 *   - Victorian Dementia-Friendly Communities Policy & Environmental Design Principles (DFFH Victoria)
 *   - Dementia Australia Environmental Design Toolkit (Section 4: Corridors & Thresholds)
 */

export type StandardHazardCategory =
  | 'Low-Contrast Entrance Frame'
  | 'Specular Floor Glare'
  | 'Confusing Signage Clutter'
  | 'Floor-to-Wall Visual Camouflage'
  | 'Busy Visual Pattern / Illusion Obstacle'
  | 'Protruding Spatial Hazard'
  | 'Unmarked Step / Threshold Change'

export interface TaxonomyDefinition {
  code: string
  category: StandardHazardCategory
  icon: string
  standardRef: string
  standardClause: string
  targetLrvRule: string
  cognitiveRamification: string
  recommendedRemedy: string
}

export const SPATIAL_HAZARD_TAXONOMY: Record<StandardHazardCategory, TaxonomyDefinition> = {
  'Low-Contrast Entrance Frame': {
    code: 'HAZ-CONTRAST-01',
    category: 'Low-Contrast Entrance Frame',
    icon: '🚪',
    standardRef: 'AS 1428.1:2021',
    standardClause: 'Clause 13.1 (Luminance Contrast of Doorways & Entrances)',
    targetLrvRule: '≥ 30% LRV difference between door frame and adjacent wall',
    cognitiveRamification: 'Without high visual contrast, older Victorians with dementia perceive the door and wall as a continuous plane, triggering disorientation and doorway hesitation.',
    recommendedRemedy: 'Repaint entrance architraves or apply contrast perimeter tape (≥ 30% LRV difference) to establish a distinct spatial doorway cue.'
  },
  'Specular Floor Glare': {
    code: 'HAZ-GLARE-02',
    category: 'Specular Floor Glare',
    icon: '✨',
    standardRef: 'Victorian Dementia-Friendly Communities Framework',
    standardClause: 'Principle 3 (Specular Reflections & Visual Comfort in Municipal Corridors)',
    targetLrvRule: '< 50% LRV specular reflectance (Matte finish required)',
    cognitiveRamification: 'Harsh reflections from high windows or glossy corridor tiles appear as puddles of standing water or physical holes in the floor, causing gait hesitation and fall risks.',
    recommendedRemedy: 'Apply non-reflective matte floor sealant, lay anti-glare corridor runners, or install diffuse solar blinds to soften beam reflections.'
  },
  'Confusing Signage Clutter': {
    code: 'HAZ-SIGN-03',
    category: 'Confusing Signage Clutter',
    icon: '🪧',
    standardRef: 'AS 1428.1:2021',
    standardClause: 'Clause 13.5 (Signage Contrast, Font Legibility & Placement)',
    targetLrvRule: '≥ 30% LRV contrast between characters and background plaque',
    cognitiveRamification: 'Cluttered notices, ornate serif fonts, or poor visual contrast overwhelm working memory, preventing independent navigation through municipal buildings.',
    recommendedRemedy: 'Replace cluttered boards with clear, sans-serif wayfinding placards featuring recognized dementia-friendly pictograms mounted at 1200–1600mm eye level.'
  },
  'Floor-to-Wall Visual Camouflage': {
    code: 'HAZ-CAMO-04',
    category: 'Floor-to-Wall Visual Camouflage',
    icon: '🧱',
    standardRef: 'AS 1428.1:2021 & DFFH Victoria',
    standardClause: 'Clause 13.2 (Visual Boundary Definition at Floor-Wall Junctions)',
    targetLrvRule: '≥ 30% LRV contrast between flooring and wall/skirting',
    cognitiveRamification: 'Monochromatic floor-to-wall transitions erode depth perception, causing people living with dementia to struggle identifying where walkways end and vertical walls begin.',
    recommendedRemedy: 'Install contrasting skirting boards (minimum 50mm height, ≥ 30% LRV variance) to clearly demarcate corridor edges.'
  },
  'Busy Visual Pattern / Illusion Obstacle': {
    code: 'HAZ-PATTERN-05',
    category: 'Busy Visual Pattern / Illusion Obstacle',
    icon: '🏁',
    standardRef: 'Victorian Dementia-Friendly Communities Framework',
    standardClause: 'Principle 4 (Visual Noise & Geometric Floor Patterns)',
    targetLrvRule: 'Uniform floor tone (variance < 15% across pattern elements)',
    cognitiveRamification: 'Geometric patterns, checkerboards, or heavy stripes are frequently perceived as physical barriers, holes, or steps, provoking sudden gait freezing and anxiety.',
    recommendedRemedy: 'Replace high-contrast patterned rugs and floor coverings with calm, uniform, solid color surfaces.'
  },
  'Protruding Spatial Hazard': {
    code: 'HAZ-OBSTACLE-06',
    category: 'Protruding Spatial Hazard',
    icon: '⚠️',
    standardRef: 'AS 1428.1:2021',
    standardClause: 'Clause 6.4 (Continuous Accessible Paths of Travel & Overhead Clearance)',
    targetLrvRule: 'Corridor clearance: 2000mm vertical, protrusions ≤ 100mm',
    cognitiveRamification: 'Fixtures extending into the corridor travel path present serious collision hazards, especially for older Victorians with constricted peripheral vision.',
    recommendedRemedy: 'Recess wall-mounted dispensers, water stations, and noticeboards, or install cane-detectable floor guidance barriers beneath them.'
  },
  'Unmarked Step / Threshold Change': {
    code: 'HAZ-STEP-07',
    category: 'Unmarked Step / Threshold Change',
    icon: '🪜',
    standardRef: 'AS 1428.1:2021',
    standardClause: 'Clause 11.1 (Luminance Contrast Nosings for Stairs & Changes of Level)',
    targetLrvRule: '50–75mm wide strip with ≥ 30% LRV contrast along step edge',
    cognitiveRamification: 'Unmarked transitions between rooms or floor textures look completely flat to impaired visual perception, leading to missteps and serious fall trauma.',
    recommendedRemedy: 'Install durable 50–75mm wide contrast nosing strips (≥ 30% LRV difference) across the full width of all steps and door thresholds.'
  }
}

export interface ClassifiedSpatialHazard {
  id: string
  title: string
  taxonomyCode: string
  category: StandardHazardCategory
  icon: string
  detectedLrv: number
  targetLrvRule: string
  isCompliant: boolean
  standardRef: string
  standardClause: string
  cognitiveRamification: string
  remedyRecommendation: string
  locationBox: number[]
}

/**
 * Classifies an environmental barrier detection into the standardized municipal taxonomy.
 */
export function classifySpatialBarrier(sug: any, idx = 0): ClassifiedSpatialHazard {
  const lrv = Math.round(Number(sug.lrv_score || sug.lrv || 15))
  const titleLower = (sug.title || '').toLowerCase()
  const catLower = (sug.category || '').toLowerCase()
  const issueLower = (sug.issue || '').toLowerCase()
  const text = `${titleLower} ${catLower} ${issueLower}`

  let matchedCategory: StandardHazardCategory = 'Low-Contrast Entrance Frame'

  if (text.includes('glare') || text.includes('reflection') || text.includes('shiny') || lrv > 75) {
    matchedCategory = 'Specular Floor Glare'
  } else if (text.includes('sign') || text.includes('plaque') || text.includes('text') || text.includes('notice') || text.includes('poster')) {
    matchedCategory = 'Confusing Signage Clutter'
  } else if (text.includes('pattern') || text.includes('checker') || text.includes('stripe') || text.includes('mosaic') || text.includes('busy')) {
    matchedCategory = 'Busy Visual Pattern / Illusion Obstacle'
  } else if (text.includes('skirting') || text.includes('camouflage') || text.includes('junction') || text.includes('perimeter')) {
    matchedCategory = 'Floor-to-Wall Visual Camouflage'
  } else if (text.includes('protrud') || text.includes('extending') || text.includes('obstacle') || text.includes('barrier') || text.includes('chair') || text.includes('table')) {
    matchedCategory = 'Protruding Spatial Hazard'
  } else if (text.includes('step') || text.includes('stair') || text.includes('nosing') || text.includes('threshold') || text.includes('level')) {
    matchedCategory = 'Unmarked Step / Threshold Change'
  } else if (text.includes('door') || text.includes('exit') || text.includes('entrance') || text.includes('frame') || text.includes('architrave')) {
    matchedCategory = 'Low-Contrast Entrance Frame'
  } else {
    // Default fallback based on LRV
    if (lrv < 25) {
      matchedCategory = 'Low-Contrast Entrance Frame'
    } else {
      matchedCategory = 'Busy Visual Pattern / Illusion Obstacle'
    }
  }

  const def = SPATIAL_HAZARD_TAXONOMY[matchedCategory]
  const isCompliant = matchedCategory === 'Specular Floor Glare' ? lrv <= 50 : lrv >= 30

  return {
    id: sug.id || `barrier-${idx + 1}`,
    title: `${matchedCategory}: ${lrv}% LRV`,
    taxonomyCode: def.code,
    category: matchedCategory,
    icon: def.icon,
    detectedLrv: lrv,
    targetLrvRule: def.targetLrvRule,
    isCompliant,
    standardRef: def.standardRef,
    standardClause: def.standardClause,
    cognitiveRamification: def.cognitiveRamification,
    remedyRecommendation: sug.recommendation || def.recommendedRemedy,
    locationBox: sug.location_box || [0, 0, 100, 100]
  }
}
