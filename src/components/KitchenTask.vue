<script setup lang="ts">
import { ref, inject, computed, onMounted } from 'vue'
import type { ViewState } from '../App.vue'
import KitchenVisualizer from './KitchenVisualizer.vue'
import { kitchenStore } from '../store'
import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'

const navigateTo = inject<(view: ViewState) => void>('navigateTo', () => {})

const hasSavedChanges = ref(kitchenStore.hasSavedChanges)
const saveChanges = () => {
  kitchenStore.savedStates = JSON.parse(JSON.stringify(itemStates.value))
  kitchenStore.hasSavedChanges = true
  hasSavedChanges.value = true
}

// Default to marker 1 so controls are immediately usable without hunting for clicks
const activeMarker = ref<number>(1)
const lightingLevel = ref(0)

const itemStates = ref<Record<number, { contrast: number; color: string }>>(
  JSON.parse(JSON.stringify(kitchenStore.savedStates))
)

const statusAnnouncement = ref('')

const contrastColorSwatches = [
  { name: 'Forest Teal', hex: '#175d52' },
  { name: 'Deep Navy', hex: '#1e3a8a' },
  { name: 'Safety Amber', hex: '#b45309' },
  { name: 'Boundary Charcoal', hex: '#1c1c1c' },
  { name: 'Terracotta', hex: '#c2410c' }
]

const kitchenElements = [
  { id: 1, name: '1. Cabinets' },
  { id: 2, name: '2. Countertop' },
  { id: 3, name: '3. Stove' },
  { id: 4, name: '4. Fridge' },
  { id: 5, name: '5. Oven' },
  { id: 6, name: '6. Sink' },
]

const isStateChanged = computed(() => {
  return JSON.stringify(itemStates.value) !== JSON.stringify(kitchenStore.savedStates)
})

const saveText = computed(() => isStateChanged.value ? 'Save this change' : 'Saved')

const selectMarker = (marker: number) => {
  activeMarker.value = marker
  const elem = kitchenElements.find(e => e.id === marker)
  if (elem) {
    statusAnnouncement.value = `Selected ${elem.name}.`
  }
}

const applyColorSwatch = (hex: string, name: string) => {
  const current = activeMarker.value !== undefined ? itemStates.value[activeMarker.value] : undefined
  if (current) {
    current.color = hex
    statusAnnouncement.value = `Applied ${name} color to ${kitchenElements.find(e => e.id === activeMarker.value)?.name || 'selected element'}.`
  }
}

const applyRecommendedPreset = () => {
  itemStates.value = {
    1: { contrast: 80, color: '#175d52' },
    2: { contrast: 85, color: '#175d52' },
    3: { contrast: 90, color: '#175d52' },
    4: { contrast: 80, color: '#175d52' },
    5: { contrast: 85, color: '#175d52' },
    6: { contrast: 90, color: '#175d52' },
  }
  lightingLevel.value = 40
  saveChanges()
  statusAnnouncement.value = 'Applied recommended high contrast colour preset to all kitchen elements.'
}

const resetAll = () => {
  itemStates.value = {
    1: { contrast: 0, color: '#3b5a51' },
    2: { contrast: 0, color: '#3b5a51' },
    3: { contrast: 0, color: '#3b5a51' },
    4: { contrast: 0, color: '#3b5a51' },
    5: { contrast: 0, color: '#3b5a51' },
    6: { contrast: 0, color: '#3b5a51' },
  }
  lightingLevel.value = 0
  saveChanges()
  statusAnnouncement.value = 'Reset all kitchen elements to default contrast.'
}

const handleCompare = () => {
  saveChanges()
  navigateTo('kitchen-compare')
}

function linearise(channel: number) {
  const value = channel / 255
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
}

function luminanceRgb(r: number, g: number, b: number) {
  return 0.2126 * linearise(r) + 0.7152 * linearise(g) + 0.0722 * linearise(b)
}

function contrastRatio(lum1: number, lum2: number) {
  const lighter = Math.max(lum1, lum2)
  const darker = Math.min(lum1, lum2)
  return (lighter + 0.05) / (darker + 0.05)
}

const hexToRgb = (hex: string): [number, number, number] => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result && result[1] && result[2] && result[3] ? [
    parseInt(result[1], 16),
    parseInt(result[2], 16),
    parseInt(result[3], 16)
  ] : [0, 0, 0];
}

const calculateRatio = (state: { contrast: number; color: string } | undefined, markerId: number) => {
  if (!state || state.contrast === 0) return 1.0;
  
  const targetRgb = hexToRgb(state.color);
  const amount = state.contrast / 100;
  
  // Kitchen Visualizer base blending colors
  let baseRgb: [number, number, number] = [251, 251, 251]; // Cabinet/Fridge
  if (markerId === 2) baseRgb = [230, 230, 230]; // Counter
  if ([3, 5, 6].includes(markerId)) baseRgb = [119, 119, 119]; // Stove/Oven/Sink strokes
  
  const currentR = Math.round(baseRgb[0] + (targetRgb[0] - baseRgb[0]) * amount);
  const currentG = Math.round(baseRgb[1] + (targetRgb[1] - baseRgb[1]) * amount);
  const currentB = Math.round(baseRgb[2] + (targetRgb[2] - baseRgb[2]) * amount);
  
  const lum1 = luminanceRgb(currentR, currentG, currentB);
  // Contrasting against white walls / counter tops
  const lum2 = luminanceRgb(255, 255, 255); 
  return contrastRatio(lum1, lum2);
}

const getContrastBadge = (state: { contrast: number; color: string } | undefined, markerId: number) => {
  const ratio = calculateRatio(state, markerId);
  
  if (ratio < 3.0) {
    return { label: `Low (${ratio.toFixed(1)}:1)`, class: 'badge-low' }
  } else if (ratio < 4.5) {
    return { label: `Improved (${ratio.toFixed(1)}:1)`, class: 'badge-improved' }
  } else {
    return { label: `High (${ratio.toFixed(1)}:1)`, class: 'badge-high' }
  }
}
interface FeedbackText {
  low: string
  improved: string
  high: string
}

const itemFeedback: Record<number, FeedbackText> = {
  1: {
    low: 'Low contrast between the cabinet doors and the wall can make it hard to locate storage areas.',
    improved: 'Moderate contrast outlines cabinet edges, making daily storage easier to distinguish.',
    high: 'Strong contrast clearly defines cabinets against the wall, supporting confident independent access.'
  },
  2: {
    low: 'The countertop blends into the floor or walls, making it difficult to recognise the workspace.',
    improved: 'Defined edging clarifies workspace boundaries, helping distinguish the surface from surroundings.',
    high: 'Clear high-contrast borders prominently separate the countertop, enhancing meal preparation safety.'
  },
  3: {
    low: 'The cooking surface lacks clear indicators, causing hesitation or safety concerns.',
    improved: 'Visible burner boundaries offer clearer visual cues, reducing hesitation during meal prep.',
    high: 'High-contrast definition prominently highlights cooktop hot zones, maximising cooking safety and ease of use.'
  },
  4: {
    low: 'The fridge exterior blends into the cabinets, making it difficult to locate.',
    improved: 'Enhanced outlines separate the refrigerator from adjacent cabinetry for quicker visual recognition.',
    high: 'Bold visual contrast makes the refrigerator immediately identifiable across the kitchen.'
  },
  5: {
    low: 'The oven panel is uniformly dark or matches the cabinets, hiding its presence.',
    improved: 'Improved edge contrast defines the oven perimeter, clarifying its location.',
    high: 'High-contrast framing ensures appliance doors and controls stand out distinctly and safely.'
  },
  6: {
    low: 'The sink blends into the countertop, making it hard to find and use.',
    improved: 'Clearer basin outlines assist in locating the sink when washing hands or preparing food.',
    high: 'Distinct high-contrast boundary provides immediate visual clarity for the water zone.'
  }
}

const getItemDescription = (markerId: number): string => {
  const feedback = itemFeedback[markerId]
  if (!feedback) return 'Each marker explains a different environmental consideration.'
  
  const state = itemStates.value[markerId]
  const ratio = calculateRatio(state, markerId)
  
  if (ratio < 3.0) return feedback.low
  if (ratio < 4.5) return feedback.improved
  return feedback.high
}

onMounted(() => {
  const hasSeenTour = localStorage.getItem('hasSeenKitchenTour')
  if (!hasSeenTour) {
    const tour = driver({
      showProgress: true,
      steps: [
        { element: '#tour-visualizer', popover: { title: '1. Explore & Identify', description: 'Click the numbered markers on the room image to discover potential barriers.', side: "right", align: 'start' } },
        { element: '#tour-identify', popover: { title: '2. Read about the barrier', description: 'Once you select a marker, this panel will explain why it might cause issues and how contrast helps.', side: "left", align: 'start' } },
        { element: '#tour-change', popover: { title: '3. Make Changes', description: 'Use these sliders to adjust the contrast and lighting of the selected element.', side: "left", align: 'start' } },
        { element: '#tour-save', popover: { title: '4. Save & Compare', description: 'When you are happy with the improvement, save your changes to compare them against the original environment!', side: "left", align: 'start' } }
      ]
    })
    
    setTimeout(() => {
      tour.drive()
      localStorage.setItem('hasSeenKitchenTour', 'true')
    }, 500)
  }
})
</script>

<template>
  <div class="kitchen-task-page">
    <div class="visually-hidden" aria-live="polite" aria-atomic="true">
      {{ statusAnnouncement }}
    </div>

    <header class="page-header">
      <div class="header-content">
        <div class="title-container">
          <div class="room-nav-bar">
            <button class="room-nav-btn" @click="navigateTo('bathroom-task')">Bathroom Guide</button>
            <button class="room-nav-btn active">Kitchen Guide</button>
            <button class="room-nav-btn" @click="navigateTo('explore')">All Rooms</button>
          </div>
          <h1 class="page-title">Kitchen — see the environment differently</h1>
          <p class="page-subtitle">
            Select an element below or click on the room image to adjust contrast, or apply 1-click presets.
          </p>
        </div>
        <div class="actions-container">
          <button class="btn-compare-header" @click="handleCompare">Compare Before & After →</button>
        </div>
      </div>
    </header>

    <div class="main-layout">
      <div class="left-column">
        <div class="visualizer-section" id="tour-visualizer">
          <KitchenVisualizer 
            :activeMarker="activeMarker" 
            :itemStates="itemStates"
            :lightingLevel="lightingLevel"
            @selectMarker="selectMarker" 
          />
        </div>
      </div>

      <div class="right-column">
        <!-- Quick Element Selector Pills -->
        <div class="element-selector-bar">
          <span class="selector-label">Elements:</span>
          <div class="chips-container" role="group" aria-label="Kitchen elements selector">
            <button 
              v-for="elem in kitchenElements" 
              :key="elem.id"
              type="button"
              class="element-chip"
              :class="{ 
                active: activeMarker === elem.id,
                adjusted: (itemStates[elem.id]?.contrast ?? 0) > 0
              }"
              :aria-pressed="activeMarker === elem.id"
              :aria-label="elem.name + ((itemStates[elem.id]?.contrast ?? 0) > 0 ? ' (contrast adjusted)' : '')"
              @click="selectMarker(elem.id)"
            >
              {{ elem.name }}
              <span v-if="(itemStates[elem.id]?.contrast ?? 0) > 0" class="chip-check" aria-hidden="true">✓</span>
            </button>
          </div>
        </div>

        <!-- 1-Click Quick Presets -->
        <div class="preset-actions-bar" role="group" aria-label="Contrast presets">
          <button type="button" class="btn-preset primary" @click="applyRecommendedPreset" title="Apply optimal contrast to all elements instantly">
            Apply High Contrast to All
          </button>
          <button type="button" class="btn-preset secondary" @click="resetAll" title="Reset all elements to default">
            Reset All
          </button>
        </div>

        <section class="task-section sticky-panel" style="margin-bottom: 1.5rem;" id="tour-identify">
          <div class="section-label">01 • Identify</div>
          <h2 class="section-heading">Possible area to review</h2>
          
          <div class="identify-box">
            <template v-if="activeMarker === 1">
              <div class="identify-header-row">
                <div class="identify-title">1. Cabinet distinction</div>
                <span class="contrast-feedback-badge" :class="getContrastBadge(itemStates[1], 1).class">
                  {{ getContrastBadge(itemStates[1], 1).label }}
                </span>
              </div>
              <div class="section-text">{{ getItemDescription(1) }}</div>
            </template>
            <template v-else-if="activeMarker === 2">
              <div class="identify-header-row">
                <div class="identify-title">2. Countertop visibility</div>
                <span class="contrast-feedback-badge" :class="getContrastBadge(itemStates[2], 2).class">
                  {{ getContrastBadge(itemStates[2], 2).label }}
                </span>
              </div>
              <div class="section-text">{{ getItemDescription(2) }}</div>
            </template>
            <template v-else-if="activeMarker === 3">
              <div class="identify-header-row">
                <div class="identify-title">3. Stove elements</div>
                <span class="contrast-feedback-badge" :class="getContrastBadge(itemStates[3], 3).class">
                  {{ getContrastBadge(itemStates[3], 3).label }}
                </span>
              </div>
              <div class="section-text">{{ getItemDescription(3) }}</div>
            </template>
            <template v-else-if="activeMarker === 4">
              <div class="identify-header-row">
                <div class="identify-title">4. Refrigerator</div>
                <span class="contrast-feedback-badge" :class="getContrastBadge(itemStates[4], 4).class">
                  {{ getContrastBadge(itemStates[4], 4).label }}
                </span>
              </div>
              <div class="section-text">{{ getItemDescription(4) }}</div>
            </template>
            <template v-else-if="activeMarker === 5">
              <div class="identify-header-row">
                <div class="identify-title">5. Oven front</div>
                <span class="contrast-feedback-badge" :class="getContrastBadge(itemStates[5], 5).class">
                  {{ getContrastBadge(itemStates[5], 5).label }}
                </span>
              </div>
              <div class="section-text">{{ getItemDescription(5) }}</div>
            </template>
            <template v-else-if="activeMarker === 6">
              <div class="identify-header-row">
                <div class="identify-title">6. Sink area</div>
                <span class="contrast-feedback-badge" :class="getContrastBadge(itemStates[6], 6).class">
                  {{ getContrastBadge(itemStates[6], 6).label }}
                </span>
              </div>
              <div class="section-text">{{ getItemDescription(6) }}</div>
            </template>
            <template v-else>
              <div class="identify-title">Choose an element</div>
              <div class="section-text">Select an element above or on the image.</div>
            </template>
          </div>
        </section>

        <section class="task-section sticky-panel" id="tour-change">
          <div class="section-label">02 • Change</div>
          <h2 class="section-heading">Try practical changes</h2>
          
          <div v-if="activeMarker !== undefined && itemStates[activeMarker]" class="metrics-list">
            <div class="identify-title" style="margin-bottom: 0.5rem;">Adjusting Selected Element ({{ activeMarker }})</div>
            <div class="metric-item">
              <div class="metric-label-row">
                <div class="metric-label-col">
                  <span class="metric-label" :id="'kitchen-contrast-label-' + activeMarker">Visual Distinction (Contrast)</span>
                  <span class="metric-hint">Adjust visibility against surroundings</span>
                </div>
                <span class="contrast-feedback-badge" :class="getContrastBadge(itemStates[activeMarker], activeMarker).class">
                  {{ getContrastBadge(itemStates[activeMarker], activeMarker).label }}
                </span>
              </div>
              <div class="metric-value-container">
                <button 
                  type="button" 
                  class="stepper-btn" 
                  @click="itemStates[activeMarker]!.contrast = Math.max(0, itemStates[activeMarker]!.contrast - 5)"
                  :disabled="itemStates[activeMarker]!.contrast <= 0"
                  :aria-label="'Decrease contrast for ' + (kitchenElements.find(e => e.id === activeMarker)?.name || 'selected element')"
                >−</button>
                <input 
                  type="range" 
                  v-model.number="itemStates[activeMarker]!.contrast" 
                  min="0" 
                  max="100" 
                  step="5"
                  class="metric-slider" 
                  :aria-labelledby="'kitchen-contrast-label-' + activeMarker"
                  :aria-valuenow="itemStates[activeMarker]!.contrast"
                  :aria-valuetext="itemStates[activeMarker]!.contrast + ' percent, ' + getContrastBadge(itemStates[activeMarker], activeMarker).label"
                  aria-valuemin="0"
                  aria-valuemax="100"
                />
                <button 
                  type="button" 
                  class="stepper-btn" 
                  @click="itemStates[activeMarker]!.contrast = Math.min(100, itemStates[activeMarker]!.contrast + 5)"
                  :disabled="itemStates[activeMarker]!.contrast >= 100"
                  :aria-label="'Increase contrast for ' + (kitchenElements.find(e => e.id === activeMarker)?.name || 'selected element')"
                >+</button>
                <span class="metric-badge">{{ itemStates[activeMarker]!.contrast }}%</span>
              </div>
            </div>
            
            <div class="metric-item">
              <div class="metric-label-row">
                <span class="metric-label" :id="'kitchen-color-label-' + activeMarker">Highlight Color</span>
                <span class="metric-hint">Recommended high distinction colour presets</span>
              </div>
              
              <div class="swatches-row" role="group" aria-label="High contrast color presets">
                <button
                  v-for="swatch in contrastColorSwatches"
                  :key="swatch.hex"
                  type="button"
                  class="color-swatch-btn"
                  :class="{ active: itemStates[activeMarker]?.color?.toLowerCase() === swatch.hex.toLowerCase() }"
                  :style="{ backgroundColor: swatch.hex }"
                  :aria-label="swatch.name + ' preset (' + swatch.hex + ')'"
                  :aria-pressed="itemStates[activeMarker]?.color?.toLowerCase() === swatch.hex.toLowerCase()"
                  :title="swatch.name"
                  @click="applyColorSwatch(swatch.hex, swatch.name)"
                >
                  <span v-if="itemStates[activeMarker]?.color?.toLowerCase() === swatch.hex.toLowerCase()" class="swatch-check" aria-hidden="true">✓</span>
                </button>
              </div>

              <div class="metric-value-container" style="margin-top: 0.25rem;">
                <input 
                  type="color" 
                  v-model="itemStates[activeMarker]!.color" 
                  class="color-picker" 
                  :aria-labelledby="'kitchen-color-label-' + activeMarker"
                />
                <span class="metric-badge">{{ itemStates[activeMarker]!.color.toUpperCase() }}</span>
              </div>
            </div>

            <!-- Keeping global elements below -->
            <div style="border-top: 1px solid var(--color-border); margin: 1rem 0;"></div>

            <div class="metric-item">
              <span class="metric-label" id="kitchen-global-lighting-label">Global Lighting</span>
              <div class="metric-value-container">
                <button 
                  type="button" 
                  class="stepper-btn" 
                  @click="lightingLevel = Math.max(0, lightingLevel - 10)"
                  :disabled="lightingLevel <= 0"
                  aria-label="Decrease lighting by 10%"
                >−</button>
                <input 
                  type="range" 
                  v-model.number="lightingLevel" 
                  min="0" 
                  max="100" 
                  step="5"
                  class="metric-slider" 
                  aria-labelledby="kitchen-global-lighting-label"
                  :aria-valuenow="lightingLevel"
                  :aria-valuetext="lightingLevel + ' percent brightness'"
                  aria-valuemin="0"
                  aria-valuemax="100"
                />
                <button 
                  type="button" 
                  class="stepper-btn" 
                  @click="lightingLevel = Math.min(100, lightingLevel + 10)"
                  :disabled="lightingLevel >= 100"
                  aria-label="Increase lighting by 10%"
                >+</button>
                <span class="metric-badge">{{ lightingLevel }}%</span>
              </div>
            </div>
          </div>
          <div v-else class="section-text empty-state">
            Select an element above or in the visualizer to adjust its specific contrast and color.
          </div>

          <div class="action-buttons" id="tour-save">
            <button type="button" class="btn-primary" @click="handleCompare">Compare Before & After →</button>
            <button type="button" class="btn-secondary" :disabled="!isStateChanged" @click="saveChanges">{{ saveText }}</button>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kitchen-task-page {
  width: 100%;
  max-width: 100%;
  margin: 0;
  padding: 1rem 6rem;
  font-family: inherit;
  box-sizing: border-box;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.room-nav-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.room-nav-btn {
  background: white;
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  padding: 0.35rem 0.85rem;
  border-radius: 99px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.room-nav-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-bg-sage);
}

.room-nav-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
  font-weight: 700;
}

.btn-compare-header {
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 0.75rem 1.25rem;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(23, 93, 82, 0.15);
  white-space: nowrap;
}

.btn-compare-header:hover {
  background: var(--color-primary-hover, #124b42);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(23, 93, 82, 0.25);
}

.element-selector-bar {
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.selector-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-text-muted);
  margin-bottom: 0.5rem;
  letter-spacing: 0.05em;
}

.chips-container {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.element-chip {
  background: var(--color-bg-sage);
  border: 1px solid transparent;
  color: var(--color-text-main);
  padding: 0.35rem 0.65rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.element-chip:hover {
  border-color: var(--color-primary);
  background: rgba(23, 93, 82, 0.1);
}

.element-chip.active {
  background: var(--color-primary);
  color: white;
  font-weight: 700;
}

.element-chip:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 2px;
}

.chip-check {
  font-size: 0.75rem;
  font-weight: 800;
  color: #10b981;
}

.element-chip.active .chip-check {
  color: #a7f3d0;
}

.preset-actions-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.btn-preset {
  flex: 1;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.btn-preset:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 2px;
}

.swatches-row {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.25rem;
  flex-wrap: wrap;
}

.color-swatch-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid white;
  box-shadow: 0 0 0 1px #cbd5e1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.85rem;
  font-weight: 800;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  padding: 0;
}

.color-swatch-btn:hover {
  transform: scale(1.15);
}

.color-swatch-btn:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 2px;
}

.color-swatch-btn.active {
  box-shadow: 0 0 0 2.5px var(--color-primary, #175d52);
  transform: scale(1.1);
}

.swatch-check {
  text-shadow: 0 1px 2px rgba(0,0,0,0.8);
}

.btn-preset.primary {
  background: rgba(23, 93, 82, 0.1);
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
}

.btn-preset.primary:hover {
  background: var(--color-primary);
  color: white;
}

.btn-preset.secondary {
  background: white;
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.btn-preset.secondary:hover {
  background: var(--color-bg-sage);
  color: var(--color-text-main);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.title-container {
  max-width: 70%;
}

.pill-badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-primary);
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin-bottom: 0.5rem;
}

.page-subtitle {
  font-size: 1.1rem;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.actions-container {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.75rem;
}

.pill-badge-outline {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-primary);
  background-color: var(--color-bg-sage);
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  letter-spacing: 0.05em;
}

.back-btn {
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  padding: 0.5rem 1.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.back-btn:hover {
  background: var(--color-bg-sage);
  border-color: var(--color-primary);
}

.main-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 1.5rem;
  align-items: stretch;
}

.left-column {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 100%;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.right-column {
  height: 100%;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.bottom-sections {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.empty-state {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--color-bg-sage);
  border-radius: 8px;
}

.task-section {
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
}

.section-label {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-primary);
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.section-heading {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin-bottom: 0.5rem;
}

.section-text {
  font-size: 1rem;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.tutorial-box {
  background: #eaf1ef;
  border: 1px solid #c8d8d3;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.tutorial-content h4 {
  margin: 0 0 0.5rem 0;
  color: var(--color-primary);
  font-size: 0.95rem;
}

.tutorial-content ul {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 0.9rem;
  color: var(--color-text-main);
}

.tutorial-content li {
  margin-bottom: 0.25rem;
}

.dismiss-btn {
  background: white;
  border: 1px solid #c8d8d3;
  padding: 0.25rem 0.75rem;
  border-radius: 99px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  color: var(--color-text-muted);
}

.dismiss-btn:hover {
  background: var(--color-bg-sage);
  color: var(--color-primary);
}

.identify-box {
  background: var(--color-bg-sage, #f7f9f7);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem 1.25rem;
  margin-top: 1rem;
}

.identify-title {
  font-weight: 700;
  color: var(--color-text-main);
  margin-bottom: 0.25rem;
}

.identify-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.contrast-feedback-badge {
  display: inline-flex;
  align-items: center;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.6rem;
  border-radius: 99px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.2s ease;
}

.contrast-feedback-badge.badge-low {
  background-color: #fde8e8;
  color: #9b1c1c;
  border: 1px solid #f8b4b4;
}

.contrast-feedback-badge.badge-improved {
  background-color: #fef3c7;
  color: #92400e;
  border: 1px solid #fcd34d;
}

.contrast-feedback-badge.badge-high {
  background-color: #def7ec;
  color: #03543f;
  border: 1px solid #84e1bc;
}

.metric-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.metrics-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin-top: 1rem;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.5rem;
}

.metric-label {
  font-weight: 600;
  color: var(--color-text-main);
  font-size: 0.95rem;
}

.metric-label-col {
  display: flex;
  flex-direction: column;
}

.metric-hint {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 0.1rem;
}

.metric-value-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
}

.stepper-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1px solid var(--color-border, #d1ddd7);
  background: white;
  color: var(--color-text-main, #1c1c1c);
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
  flex-shrink: 0;
}

.stepper-btn:hover:not(:disabled) {
  background: var(--color-bg-sage, #e9eee9);
  border-color: var(--color-primary, #175d52);
  color: var(--color-primary, #175d52);
}

.stepper-btn:focus-visible {
  outline: 3px solid var(--color-primary, #175d52);
  outline-offset: 2px;
}

.stepper-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.metric-slider {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  appearance: none;
  background: linear-gradient(90deg, #f2f5f3, #1d443b);
  cursor: pointer;
}
.metric-slider::-webkit-slider-thumb {
  width: 24px;
  height: 24px;
  border: 4px solid #fff;
  border-radius: 50%;
  appearance: none;
  background: #285e51;
  box-shadow: 0 0 0 1px #285e51, 0 3px 8px rgba(0,0,0,.2);
}

.color-picker {
  -webkit-appearance: none;
  border: none;
  width: 100%;
  height: 30px;
  border-radius: 4px;
  cursor: pointer;
  padding: 0;
}
.color-picker::-webkit-color-swatch-wrapper {
  padding: 0;
}
.color-picker::-webkit-color-swatch {
  border: 1px solid var(--color-border);
  border-radius: 4px;
}

.metric-badge {
  background: #e6f0ed;
  color: var(--color-primary);
  font-weight: 700;
  font-size: 0.8rem;
  padding: 0.25rem 0.6rem;
  border-radius: 12px;
  min-width: 40px;
  text-align: center;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 1rem;
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
  width: 100%;
}

.btn-primary:hover {
  background: #253a33;
}

.btn-secondary {
  background: var(--color-bg-sage, #f7f9f7);
  color: var(--color-primary);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
}

.btn-secondary:hover {
  background: #e6f0ed;
  border-color: var(--color-primary);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary:hover:disabled {
  background: var(--color-bg-sage, #f7f9f7);
  border-color: var(--color-border);
}

.fade-in {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
