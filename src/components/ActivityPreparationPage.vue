<script setup lang="ts">
import { ref, computed, inject, onMounted, watch } from 'vue'
import { outingScheduleStore } from '../store'
import {
  getDaytimeSchedule,
  getRecommendedHour,
  fetchDynamicDaytimeSchedule,
  type DaytimeHourData,
  type MatchedSensorInfo
} from '../utils/sensorySchedule'
import {
  COLD_START_ANCHORS,
  type DestinationAnchor
} from '../utils/activityData'
import { useRecentDestinations } from '../composables/useRecentDestinations'
import RoutingView from './RoutingView.vue'
import DepartureChecklist from './DepartureChecklist.vue'

const navigateTo = inject<(view: string) => void>('navigateTo', () => {})

// Recent Destinations composable
const { recentDestinations, saveRecentDestination } = useRecentDestinations()

// Destination selection (synced with store)
const destination = ref(outingScheduleStore.destination || '')
const destinationCoords = ref<{ lat: number; lon: number } | null>(outingScheduleStore.destinationCoords || null)
const hasDestination = computed(() => Boolean(destination.value && destination.value.trim().length > 1))

const currentAnchor = computed<DestinationAnchor>(() => {
  const lower = destination.value.toLowerCase()
  return (
    COLD_START_ANCHORS.find(a => 
      lower.includes(a.name.toLowerCase()) || 
      lower.includes(a.category.toLowerCase()) ||
      a.name.toLowerCase().includes(lower)
    ) || COLD_START_ANCHORS[0]!
  )
})

const selectPresetPill = (destName: string) => {
  destination.value = destName
  destinationCoords.value = null
  saveRecentDestination(destName)
  syncToStore()
}

const handleDestinationInput = () => {
  syncToStore()
}

const onDestinationBlur = () => {
  if (destination.value && destination.value.trim().length > 2) {
    saveRecentDestination(destination.value.trim())
  }
}

// Live database-backed sensory calculations (with seamless fallback)
const liveSchedule = ref<DaytimeHourData[] | null>(null)
const isLive = ref(false)
const matchedSensor = ref<MatchedSensorInfo | null>(null)

const loadDynamicSensory = async () => {
  try {
    const res = await fetchDynamicDaytimeSchedule(
      destination.value, 
      destinationCoords.value || undefined
    )
    if (res && res.schedule && res.schedule.length > 0) {
      liveSchedule.value = res.schedule
      isLive.value = res.isLive
      if (res.matchedSensor) {
        matchedSensor.value = res.matchedSensor
      }
      syncToStore()
    }
  } catch (e) {
    console.warn('Could not load live sensory data:', e)
  }
}

// Automatically re-query database when destination or coordinates change
watch([destination, destinationCoords], () => {
  loadDynamicSensory()
})

onMounted(() => {
  loadDynamicSensory()
})

const daytimeSchedule = computed(() => {
  return liveSchedule.value || getDaytimeSchedule(destination.value, destinationCoords.value || undefined)
})
const recommendedHour = computed(() => getRecommendedHour(daytimeSchedule.value))

const selectedHour = ref<number>(outingScheduleStore.selectedHour || 10)

const activeHourData = computed(() => {
  return (
    daytimeSchedule.value.find(h => h.hour === selectedHour.value) ||
    recommendedHour.value
  )
})

const selectHour = (hour: number) => {
  selectedHour.value = hour
  syncToStore()
}

const resetToQuietestHour = () => {
  selectedHour.value = recommendedHour.value.hour
  syncToStore()
}

const syncToStore = () => {
  outingScheduleStore.destination = destination.value
  outingScheduleStore.selectedHour = selectedHour.value
  outingScheduleStore.recommendedWindow = activeHourData.value.window
  outingScheduleStore.noiseLevel = activeHourData.value.noise
  outingScheduleStore.crowdLevel = activeHourData.value.crowd
  outingScheduleStore.decibels = activeHourData.value.decibels
  outingScheduleStore.pedestrianCount = activeHourData.value.pedestrianCount
  outingScheduleStore.isPrepared = true
}

const isRouteReady = ref(false)
const routeStats = ref<any>(null)

const handleRouteCalculated = (stats: any) => {
  isRouteReady.value = true
  routeStats.value = stats
  if (stats) {
    if (stats.destination) destination.value = stats.destination
    if (stats.destinationCoords) {
      destinationCoords.value = stats.destinationCoords
      outingScheduleStore.destinationCoords = stats.destinationCoords
    }
    syncToStore()
  }
}

const handleDestinationChanged = (payload: any) => {
  if (typeof payload === 'string') {
    if (payload.trim()) {
      destination.value = payload.trim()
      destinationCoords.value = null
      outingScheduleStore.destinationCoords = null
    }
  } else if (payload && payload.name) {
    destination.value = payload.name.trim()
    if (payload.coords) {
      destinationCoords.value = payload.coords
      outingScheduleStore.destinationCoords = payload.coords
    }
  }
  syncToStore()
}

const scrollToStep2 = () => {
  const el = document.getElementById('step2-section')
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  }
}

const scrollToStep3 = () => {
  const el = document.getElementById('step3-section')
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  }
}

const comfortTier = computed(() => {
  const db = activeHourData.value.decibels
  if (db < 55) {
    return {
      status: 'Calm & Quiet',
      badgeClass: 'comfort-calm',
      emoji: '🟢',
      soundSummary: 'Gentle ambient sound & conversation-friendly (under 55 dB)',
      crowdSummary: 'Light foot traffic with clear, unhurried paths',
      bgClass: 'banner-calm'
    }
  } else if (db <= 62) {
    return {
      status: 'Moderate Sound',
      badgeClass: 'comfort-moderate',
      emoji: '🟡',
      soundSummary: 'Normal neighborhood sounds & steady street ambiance (55–62 dB)',
      crowdSummary: 'Moderate pedestrian flow; companion awareness helpful',
      bgClass: 'banner-moderate'
    }
  } else {
    return {
      status: 'Busy Period',
      badgeClass: 'comfort-busy',
      emoji: '🔴',
      soundSummary: 'Noticeable urban traffic and higher activity (over 62 dB)',
      crowdSummary: 'Brisk foot traffic; consider our recommended quieter hour',
      bgClass: 'banner-busy'
    }
  }
})

const goToPocketCard = () => {
  ;(outingScheduleStore as any).plannerStep = 2
  syncToStore()
  navigateTo('walk-planner')
}
</script>

<template>
  <div class="prep-page-container">
    <!-- Header Section -->
    <header class="page-header">
      <div class="prep-header-top">
        <h1 class="page-title">Prepare for an everyday activity</h1>
      </div>
      <p class="page-subtitle">
        A calm, step-by-step guide designed for low stress: choose where you are heading, check the quietest daytime hours (strictly 9:00 AM – 5:00 PM), and review comforting cues before you walk.
      </p>
    </header>

    <!-- STEP 1: Plan a Safe Walk (Straight-Path Landmark Route) -->
    <section class="activity-selector-card routing-step-card" aria-labelledby="step1-heading">
      <div class="step-badge-row">
        <span class="step-badge highlight-badge">STEP 1</span>
        <span class="step-badge-label">Straight-Path Landmark Route</span>
      </div>
      <h2 id="step1-heading" class="step-card-title">Plan a Safe Walk</h2>
      <p class="step-card-desc">
        Prioritize straight paths with continuous tree shade, resting benches, and visible physical landmarks without confusing map layers:
      </p>

      <RoutingView 
        @routeCalculated="handleRouteCalculated"
        @destinationChanged="handleDestinationChanged"
      />

      <div class="step1-actions-row">
        <button 
          v-if="hasDestination"
          type="button" 
          class="next-step-btn"
          @click="scrollToStep2"
        >
          Check Quietest Time to Walk &darr;
        </button>
        <div v-else class="step1-waiting-hint">
          <span class="hint-icon" aria-hidden="true">📍</span>
          <span>Please choose or type a destination above to see quiet walk times.</span>
        </div>
      </div>
    </section>

    <!-- STEP 2: Recommended Calm Daytime Window (Epic 4: Sensory Scheduling Tool) -->
    <section id="step2-section" class="guided-step-card calm-window-section" aria-labelledby="step2-heading">
      <div class="step-badge-row">
        <span class="step-badge highlight-badge">STEP 2</span>
        <span class="step-badge-label">Daytime Sensory Schedule</span>
      </div>
      <h2 id="step2-heading" class="step-card-title">Calmest Time to Walk</h2>
      <p class="step-card-desc">
        {{ hasDestination 
          ? `Review daytime sound and foot traffic for "${destination}" between 9:00 AM and 5:00 PM:` 
          : 'Check sensory comfort levels and uncrowded footpaths strictly between 9:00 AM and 5:00 PM:'
        }}
      </p>

      <!-- Waiting State: Shown when no destination is entered yet -->
      <div v-if="!hasDestination" class="calm-waiting-card" role="status">
        <div class="waiting-icon-box" aria-hidden="true">
          <span class="waiting-icon">📍</span>
        </div>
        <div class="waiting-content">
          <h3 class="waiting-title">Enter your destination in Step 1 above</h3>
          <p class="waiting-desc">
            Once you choose or type where you are heading, we will show you the quietest daytime hours (9:00 AM – 5:00 PM) and footpath activity for your walk.
          </p>
        </div>
      </div>

      <!-- Active State: Full Sensory Schedule once destination is entered -->
      <div v-else class="step2-active-content">
        <!-- Large Color-Coded Comfort Card -->
        <div class="calm-window-banner" :class="[comfortTier.bgClass, { 'is-recommended-banner': activeHourData.isRecommended }]">
          <div class="calm-time-block">
            <div class="calm-badge-line">
              <span class="comfort-status-badge" :class="comfortTier.badgeClass">
                <span class="comfort-emoji" aria-hidden="true">{{ comfortTier.emoji }}</span>
                {{ comfortTier.status }}
              </span>
              <span v-if="activeHourData.isRecommended" class="recommended-tag">★ Quietest Choice</span>
            </div>
            
            <div class="calm-time-value">
              <span class="clock-icon" aria-hidden="true">🕒</span>
              <strong>{{ activeHourData.window }}</strong>
            </div>

            <!-- Reassurance Context Tip -->
            <p class="calm-reassurance">
              {{ activeHourData.tip }}
            </p>
          </div>

          <div class="calm-metrics-pill-group">
            <div class="metric-pill">
              <span class="metric-label">Estimated Sound</span>
              <span 
                class="metric-status"
                :class="activeHourData.noise === 'Low' ? 'low-noise' : activeHourData.noise === 'Moderate' ? 'mod-noise' : 'high-noise'"
              >
                {{ activeHourData.noise === 'Low' ? '🟢' : activeHourData.noise === 'Moderate' ? '🟡' : '🔴' }}
                {{ activeHourData.decibels }} dB
              </span>
              <span class="metric-sub">{{ comfortTier.soundSummary }}</span>
            </div>

            <div class="metric-pill">
              <span class="metric-label">Foot Traffic</span>
              <span 
                class="metric-status"
                :class="activeHourData.crowd === 'Light' ? 'light-crowd' : activeHourData.crowd === 'Moderate' ? 'mod-crowd' : 'busy-crowd'"
              >
                {{ activeHourData.crowd === 'Light' ? '🟢' : activeHourData.crowd === 'Moderate' ? '🟡' : '🔴' }}
                {{ activeHourData.crowd }}
              </span>
              <span class="metric-sub">{{ comfortTier.crowdSummary }}</span>
            </div>
          </div>
        </div>

        <!-- Sensor Transparency Note -->
        <!-- <div v-if="matchedSensor" class="sensor-attribution-note">
          <span class="sensor-icon" aria-hidden="true">📍</span>
          <span class="sensor-text">
            Sensory readings matched to nearest civic sensor: <strong>{{ matchedSensor.name }}</strong> ({{ matchedSensor.distanceMeters }}m away).
          </span>
        </div> -->

        <!-- Interactive 9 AM - 5 PM Hourly Daytime Strip -->
        <div class="timeline-section" role="region" aria-label="Daytime hour exploration">
          <div class="timeline-header">
            <span class="timeline-title">Explore Daytime Hours (9:00 AM – 5:00 PM):</span>
            <button 
              v-if="selectedHour !== recommendedHour.hour" 
              type="button" 
              class="reset-quiet-btn"
              @click="resetToQuietestHour"
            >
              ↺ Return to recommended quietest hour ({{ recommendedHour.label }})
            </button>
          </div>

          <div class="hours-strip" role="group" aria-label="Daytime hours">
            <button
              v-for="item in daytimeSchedule"
              :key="item.hour"
              type="button"
              class="hour-btn"
              :class="{
                selected: selectedHour === item.hour,
                recommended: item.isRecommended
              }"
              :aria-pressed="selectedHour === item.hour"
              @click="selectHour(item.hour)"
            >
              <span class="hour-label">{{ item.label }}</span>
              <span class="hour-comfort-dot" aria-hidden="true">
                {{ item.decibels < 55 ? '🟢' : item.decibels <= 62 ? '🟡' : '🔴' }}
              </span>
              <span v-if="item.isRecommended" class="hour-tag">★ Quietest</span>
            </button>
          </div>
        </div>

        <!-- DMP Section 7.4 Data Disclosure Footnote -->
        <!-- <div class="dmp-attribution-note">
          <span class="dmp-icon" aria-hidden="true">ℹ️</span>
          <span class="dmp-text">
            Ground-truth daytime noise & pedestrian sensor data from City of Melbourne Open Data. Analyzed strictly between 9:00 AM and 5:00 PM to support safe, natural routines.
          </span>
        </div> -->

        <!-- Navigation to Step 3 -->
        <div class="step-actions-row">
          <button 
            type="button" 
            class="next-step-btn"
            @click="scrollToStep3"
          >
            Next: Departure Checklist &darr;
          </button>
        </div>
      </div>
    </section>

    <!-- STEP 3: Interactive Departure Checklist -->
    <DepartureChecklist
      :destination="destination"
      :current-anchor="currentAnchor"
      @continue="goToPocketCard"
    />
  </div>
</template>

<style scoped>
.prep-page-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.5rem 1rem 4rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  font-family: inherit;
}

/* Page Header */
.page-header {
  margin-bottom: 0.5rem;
}

.prep-header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 800;
  color: #1c2e28;
  letter-spacing: -0.02em;
  margin: 0;
  line-height: 1.25;
}

.page-subtitle {
  font-size: 1.05rem;
  line-height: 1.55;
  color: #4b6358;
  margin: 0.5rem 0 0 0;
  max-width: 900px;
}

/* Step Card Containers (Shared base) */
.activity-selector-card,
.guided-step-card {
  background: #ffffff;
  border: 1.5px solid #d8e5df;
  border-radius: 16px;
  padding: 1.75rem;
  box-shadow: 0 2px 8px rgba(23, 93, 82, 0.04);
}

/* Step Badges & Headers */
.step-badge-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.75rem;
}

.step-badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  padding: 0.25rem 0.65rem;
  border-radius: 6px;
  background: #e9f2ee;
  color: #175d52;
  text-transform: uppercase;
}

.step-badge.highlight-badge {
  background: #175d52;
  color: #ffffff;
}

.step-badge-label {
  font-size: 0.85rem;
  font-weight: 700;
  color: #557266;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.live-sensor-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: #e2ede7;
  color: #175d52;
  border: 1px solid #c2dbd1;
  border-radius: 99px;
  padding: 0.2rem 0.65rem;
  font-size: 0.76rem;
  font-weight: 750;
  margin-left: auto;
}

.step-card-title {
  font-size: 1.55rem;
  font-weight: 800;
  color: #1c2e28;
  margin: 0 0 0.4rem 0;
  line-height: 1.3;
}

.step-card-desc {
  font-size: 1rem;
  color: #4b6358;
  margin: 0 0 1.5rem 0;
  line-height: 1.5;
}

.step1-actions-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px dashed #d8e5df;
}

.next-step-btn {
  background: #175d52;
  color: white;
  border: none;
  padding: 0.85rem 1.6rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(23, 93, 82, 0.2);
}

.next-step-btn:hover {
  background: #0f4038;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(23, 93, 82, 0.25);
}

/* Destination Search Box */
.destination-search-box {
  margin-bottom: 1.35rem;
}

.dest-input-label {
  display: block;
  font-size: 0.95rem;
  font-weight: 750;
  color: #1c2e28;
  margin-bottom: 0.5rem;
}

.input-with-icon {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 1.1rem;
  font-size: 1.25rem;
  pointer-events: none;
  opacity: 0.7;
}

.dest-text-input {
  width: 100%;
  padding: 0.95rem 1.2rem 0.95rem 3.2rem;
  font-size: 1.05rem;
  font-weight: 600;
  color: #1c2e28;
  background: #ffffff;
  border: 2px solid #badcd0;
  border-radius: 12px;
  outline: none;
  transition: all 0.2s ease;
  min-height: 52px;
}

.dest-text-input:focus {
  border-color: #175d52;
  box-shadow: 0 0 0 4px rgba(23, 93, 82, 0.15);
}

.dest-text-input::placeholder {
  color: #7b998d;
  font-weight: 500;
}

/* Preset Destination Pills */
.preset-pills-container {
  margin-bottom: 1.35rem;
}

.pills-label-row {
  margin-bottom: 0.65rem;
}

.categories-label {
  font-size: 0.9rem;
  font-weight: 750;
  color: #3e5e51;
}

.categories-pills-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.preset-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: #ffffff;
  border: 1.5px solid #d4e5dd;
  border-radius: 99px;
  padding: 0.6rem 1.15rem;
  font-size: 0.95rem;
  font-weight: 700;
  color: #233e33;
  cursor: pointer;
  transition: all 0.2s ease;
  min-height: 48px;
}

.preset-pill:hover {
  border-color: #175d52;
  background: #f4faf6;
  color: #175d52;
}

.preset-pill:focus-visible {
  outline: 3px solid #175d52;
  outline-offset: 2px;
}

.preset-pill.active {
  background: #175d52;
  border-color: #175d52;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(23, 93, 82, 0.2);
}

.pill-icon {
  font-size: 1.15rem;
}

/* Step 1 Hint when waiting for destination */
.step1-waiting-hint {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  background: #f0f7f4;
  border: 1.5px dashed #89a89d;
  color: #233e33;
  padding: 0.75rem 1.25rem;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 600;
}

.hint-icon {
  font-size: 1.2rem;
}

/* Step 2: Calm Window Banner & Metrics */
.calm-window-section {
  background: #f4faf6;
  border-color: #badcd0;
}

/* Step 2 Calm Waiting Card (Progressive Disclosure) */
.calm-waiting-card {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  background: #ffffff;
  border: 2px dashed #b2d5c8;
  border-radius: 16px;
  padding: 2rem 2.25rem;
  margin-top: 1rem;
  box-shadow: 0 4px 16px rgba(23, 93, 82, 0.04);
}

.waiting-icon-box {
  width: 58px;
  height: 58px;
  border-radius: 50%;
  background: #e8f5f0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.waiting-icon {
  font-size: 1.75rem;
}

.waiting-content {
  flex: 1;
}

.waiting-title {
  margin: 0 0 0.4rem 0;
  font-size: 1.2rem;
  font-weight: 800;
  color: #175d52;
}

.waiting-desc {
  margin: 0;
  font-size: 0.98rem;
  color: #436357;
  line-height: 1.55;
  max-width: 680px;
}

.calm-window-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
  flex-wrap: wrap;
  margin-top: 1rem;
  background: #ffffff;
  border: 2px solid #badcd0;
  border-radius: 14px;
  padding: 1.5rem;
  box-shadow: 0 3px 10px rgba(23, 93, 82, 0.05);
  transition: all 0.25s ease;
}

.calm-window-banner.banner-calm {
  border-left: 8px solid #059669;
  background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%);
}

.calm-window-banner.banner-moderate {
  border-left: 8px solid #d97706;
  background: linear-gradient(135deg, #ffffff 0%, #fffbeb 100%);
}

.calm-window-banner.banner-busy {
  border-left: 8px solid #dc2626;
  background: linear-gradient(135deg, #ffffff 0%, #fef2f2 100%);
}

.comfort-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 1.05rem;
  font-weight: 800;
  padding: 0.35rem 0.85rem;
  border-radius: 8px;
  letter-spacing: 0.01em;
}

.comfort-status-badge.comfort-calm {
  background: #d1fae5;
  color: #065f46;
  border: 1.5px solid #a7f3d0;
}

.comfort-status-badge.comfort-moderate {
  background: #fef3c7;
  color: #92400e;
  border: 1.5px solid #fde68a;
}

.comfort-status-badge.comfort-busy {
  background: #fee2e2;
  color: #991b1b;
  border: 1.5px solid #fecaca;
}

.comfort-emoji {
  font-size: 1.1rem;
}

.calm-time-block {
  flex: 1;
  min-width: 280px;
}

.calm-badge-line {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
  flex-wrap: wrap;
}

.calm-label {
  display: block;
  font-size: 0.82rem;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #175d52;
}

.recommended-tag {
  background: #175d52;
  color: #ffffff;
  font-size: 0.75rem;
  font-weight: 800;
  padding: 0.2rem 0.6rem;
  border-radius: 99px;
  letter-spacing: 0.03em;
}

.calm-time-value {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  font-size: 1.65rem;
  color: #0f463c;
  margin-bottom: 0.65rem;
}

.clock-icon {
  font-size: 1.8rem;
}

.calm-reassurance {
  font-size: 1rem;
  line-height: 1.55;
  color: #315144;
  margin: 0;
  max-width: 600px;
}

.calm-metrics-pill-group {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.metric-pill {
  background: #ffffff;
  border: 1.5px solid #c2ded3;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 140px;
  box-shadow: 0 2px 6px rgba(23, 93, 82, 0.04);
}

.metric-label {
  font-size: 0.78rem;
  font-weight: 700;
  color: #557266;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.metric-status {
  font-size: 1.15rem;
  font-weight: 800;
  color: #0f463c;
}

.metric-sub {
  font-size: 0.75rem;
  color: #557266;
  line-height: 1.3;
}

.low-noise, .light-crowd {
  color: #0f463c;
}

.mod-noise, .mod-crowd {
  color: #854d0e;
}

.high-noise, .busy-crowd {
  color: #991b1b;
}

/* Timeline Section inside Step 2 */
.timeline-section {
  margin-top: 1.5rem;
  background-color: #ffffff;
  border: 1.5px solid #d4e5dd;
  border-radius: 14px;
  padding: 1.25rem;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 0.875rem;
}

.timeline-title {
  font-size: 0.95rem;
  font-weight: 750;
  color: #1c2e28;
}

.reset-quiet-btn {
  background: none;
  border: none;
  color: #175d52;
  font-size: 0.88rem;
  font-weight: 750;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
  transition: opacity 0.2s;
}

.reset-quiet-btn:hover {
  opacity: 0.8;
}

.hours-strip {
  display: flex;
  gap: 0.55rem;
  overflow-x: auto;
  padding-bottom: 0.4rem;
}

.hour-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 80px;
  padding: 0.7rem 0.5rem;
  background-color: #f7faf8;
  border: 1.5px solid #d4e5dd;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.hour-btn:hover {
  border-color: #175d52;
  background-color: #eaf4f0;
}

.hour-btn.selected {
  border-color: #175d52;
  background-color: #175d52;
  color: #ffffff;
  box-shadow: 0 3px 8px rgba(23, 93, 82, 0.2);
}

.hour-btn.selected .hour-label {
  color: #ffffff;
}

.hour-btn.selected .hour-tag {
  background-color: #ffffff;
  color: #175d52;
}

.hour-label {
  font-size: 0.95rem;
  font-weight: 800;
  color: #1c2e28;
}

.hour-tag {
  font-size: 0.68rem;
  font-weight: 750;
  background-color: #d1fae5;
  color: #065f46;
  border-radius: 4px;
  padding: 0.15rem 0.4rem;
  margin-top: 0.35rem;
  letter-spacing: 0.02em;
}

.hour-comfort-dot {
  font-size: 0.8rem;
  margin-top: 0.25rem;
  line-height: 1;
}

/* Sensor Attribution Note */
.sensor-attribution-note {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.85rem;
  padding: 0.6rem 0.95rem;
  background: #ffffff;
  border: 1px solid #d4e5dd;
  border-radius: 8px;
  font-size: 0.84rem;
  color: #3b584c;
  line-height: 1.4;
}

.sensor-icon {
  font-size: 0.95rem;
  flex-shrink: 0;
}

.sensor-text {
  font-weight: 500;
}

/* DMP Attribution Disclosure */
.dmp-attribution-note {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  margin-top: 1.5rem;
  padding: 0.85rem 1.1rem;
  background: #eef5f1;
  border-left: 4px solid #175d52;
  border-radius: 8px;
  color: #3b584c;
  font-size: 0.84rem;
  line-height: 1.5;
}

.dmp-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
  margin-top: 0.05rem;
}

.dmp-text {
  font-weight: 500;
}

.step-actions-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px dashed #d8e5df;
}

/* Final Action Card (Step 4 / CTA) */
.final-action-card {
  background: linear-gradient(135deg, #175d52 0%, #10443c 100%);
  color: #ffffff;
  border-radius: 18px;
  padding: 2.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
  box-shadow: 0 10px 30px rgba(23, 93, 82, 0.18);
  margin-top: 0.5rem;
}

.action-card-content {
  flex: 1;
}

.action-tag {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #a3d8ca;
  margin-bottom: 0.5rem;
}

.action-title {
  font-size: 1.55rem;
  font-weight: 800;
  color: #ffffff;
  margin: 0 0 0.6rem 0;
  line-height: 1.25;
}

.action-desc {
  font-size: 1.05rem;
  color: #d1ebe3;
  margin: 0;
  line-height: 1.55;
  max-width: 650px;
}

.main-route-btn {
  background: #ffffff;
  color: #11463e;
  border: 2px solid #ffffff;
  border-radius: 12px;
  padding: 1rem 2rem;
  font-size: 1.15rem;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.25s ease;
  white-space: nowrap;
  min-height: 52px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.main-route-btn:hover {
  background: #e8f5f0;
  color: #0b342e;
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
}

.main-route-btn:focus-visible {
  outline: 3px solid #fbbf24;
  outline-offset: 4px;
}

/* Responsive Styles */
@media (max-width: 992px) {
  .final-action-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .main-route-btn {
    width: 100%;
    text-align: center;
  }
}

@media (max-width: 600px) {
  .prep-page-container {
    padding: 1rem 0.75rem 3rem;
  }

  .guided-step-card,
  .activity-selector-card {
    padding: 1.25rem 1rem;
  }

  .categories-pills-row {
    gap: 0.5rem;
  }

  .preset-pill {
    width: 100%;
    justify-content: flex-start;
  }

  .calm-waiting-card {
    flex-direction: column;
    text-align: center;
    padding: 1.5rem 1rem;
    gap: 1rem;
  }

  .calm-window-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .calm-metrics-pill-group {
    width: 100%;
  }

  .metric-pill {
    flex: 1;
  }
}
</style>