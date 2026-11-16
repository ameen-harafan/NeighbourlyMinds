<script setup lang="ts">
import { ref, computed, inject, onMounted, watch } from 'vue'
import type { ViewState } from '../App.vue'
import { outingScheduleStore } from '../store'
import {
  POPULAR_DESTINATIONS,
  DAYS_OF_WEEK,
  getDaytimeSchedule,
  getRecommendedHour,
  fetchDynamicDaytimeSchedule,
  type DaytimeHourData,
  type MatchedSensorInfo
} from '../utils/sensorySchedule'

const navigateTo = inject<(view: ViewState) => void>('navigateTo', () => {})
const goBack = inject<() => void>('goBack', () => {})

const searchQuery = ref(outingScheduleStore.destination || '')
const selectedDay = ref(outingScheduleStore.selectedDay || 'Tuesday')
const selectedHour = ref<number>(outingScheduleStore.selectedHour || 10)
const showPreparedToast = ref(false)

const liveSchedule = ref<DaytimeHourData[] | null>(null)
const isLive = ref(false)
const matchedSensor = ref<MatchedSensorInfo | null>(null)

const loadDynamicSensory = async () => {
  try {
    const res = await fetchDynamicDaytimeSchedule(searchQuery.value, selectedDay.value)
    if (res && res.schedule && res.schedule.length > 0) {
      liveSchedule.value = res.schedule
      isLive.value = res.isLive
      if (res.matchedSensor) {
        matchedSensor.value = res.matchedSensor
      }
    }
  } catch (e) {
    console.warn('Could not load live sensory data:', e)
  }
}

watch([searchQuery, selectedDay], () => {
  loadDynamicSensory()
})

onMounted(() => {
  loadDynamicSensory()
})

const daytimeSchedule = computed(() =>
  liveSchedule.value || getDaytimeSchedule(searchQuery.value, selectedDay.value)
)

const activeHourData = computed(() => {
  return (
    daytimeSchedule.value.find(h => h.hour === selectedHour.value) ||
    getRecommendedHour(daytimeSchedule.value)
  )
})

const selectDestination = (dest: string) => {
  searchQuery.value = dest
}

const handleUseForPreparation = () => {
  outingScheduleStore.destination = searchQuery.value || ''
  outingScheduleStore.selectedDay = selectedDay.value
  outingScheduleStore.selectedHour = selectedHour.value
  outingScheduleStore.recommendedWindow = activeHourData.value.window
  outingScheduleStore.noiseLevel = activeHourData.value.noise
  outingScheduleStore.crowdLevel = activeHourData.value.crowd
  outingScheduleStore.decibels = activeHourData.value.decibels
  outingScheduleStore.pedestrianCount = activeHourData.value.pedestrianCount
  outingScheduleStore.isPrepared = true

  navigateTo('prepare-activity')
}
</script>

<template>
  <div class="sensory-schedule-container" role="main" aria-labelledby="page-title">
    <div class="back-link-bar">
      <button 
        type="button" 
        class="return-btn"
        @click="navigateTo('prepare-activity')"
        aria-label="Return to Outing Preparation"
      >
        &larr; Return to Outing Preparation
      </button>
    </div>

    <header class="sensory-header">
      <h1 id="page-title" class="page-title">Daytime Sensory Schedule</h1>
      <p class="page-subtitle">
        Search your destination. See quieter daytime hours from microclimate noise and pedestrian data — strictly 9:00 AM to 5:00 PM only.
      </p>
    </header>

    <!-- Main Scheduler Card -->
    <div class="scheduler-card">
      <!-- Search Input Section -->
      <div class="search-section">
        <label for="destination-input" class="search-label">
          Where are you going?
        </label>
        <div class="input-wrapper">
          <input
            id="destination-input"
            v-model="searchQuery"
            type="text"
            class="destination-input"
            placeholder="Search destination, library, or community centre..."
            aria-describedby="safe-window-note"
          />
        </div>

        <!-- Quick Destination Suggestion Chips -->
        <div class="suggestions-row" role="group" aria-label="Suggested community destinations">
          <span class="suggestion-label">Suggestions:</span>
          <button
            v-for="dest in POPULAR_DESTINATIONS"
            :key="dest"
            type="button"
            class="suggestion-chip"
            :class="{ active: searchQuery === dest }"
            @click="selectDestination(dest)"
          >
            {{ dest }}
          </button>
        </div>

        <!-- Safe Outing Window Pills -->
        <div class="pills-row" role="region" aria-label="Operating window specifications">
          <span class="pill-badge pill-badge-primary">
            SAFE OUTING WINDOW
          </span>
          <span class="pill-badge pill-badge-secondary">
            9:00 AM – 5:00 PM only
          </span>
        </div>

        <!-- Clarification Helper Text -->
        <p id="safe-window-note" class="helper-note">
          Late-night hours are never suggested. Production connects Melbourne microclimate sensors + pedestrian counting (daytime filter).
        </p>
      </div>

      <!-- Results Subheading & Day Selector -->
      <div class="results-header-row">
        <h2 class="results-heading">
          {{ selectedDay }}{{ searchQuery ? ' — ' + searchQuery : '' }}
        </h2>
        <div class="day-selector-wrapper">
          <label for="day-select" class="visually-hidden">Select day of outing</label>
          <select id="day-select" v-model="selectedDay" class="day-select">
            <option v-for="day in DAYS_OF_WEEK" :key="day" :value="day">
              {{ day }}
            </option>
          </select>
        </div>
      </div>

      <!-- 3 Sensory Comfort Summary Cards matching Figma -->
      <div 
        class="cards-grid" 
        role="region" 
        aria-live="polite" 
        aria-label="Sensory summary for recommended outing"
      >
        <!-- Card 1: Recommended Quietest Window (Primary Highlight) -->
        <div 
          class="summary-card" 
          :class="activeHourData.isRecommended ? 'card-recommended' : 'card-selected'"
        >
          <div class="card-overline">
            {{ activeHourData.isRecommended ? 'Recommended' : 'Selected window' }}
          </div>
          <div 
            class="card-main-value" 
            :class="activeHourData.isRecommended ? 'text-recommended' : 'text-neutral'"
          >
            {{ activeHourData.window }}
          </div>
          <div class="card-subtext">
            {{ activeHourData.isRecommended ? 'Quietest daytime window' : activeHourData.tip }}
          </div>
        </div>

        <!-- Card 2: Noise Level -->
        <div class="summary-card card-neutral">
          <div class="card-overline">Noise level</div>
          <div class="card-main-value text-neutral">
            {{ activeHourData.noise }}
          </div>
          <div class="card-subtext">Microclimate sensor estimate</div>
        </div>

        <!-- Card 3: Crowd Level -->
        <div class="summary-card card-neutral">
          <div class="card-overline">Crowd level</div>
          <div class="card-main-value text-neutral">
            {{ activeHourData.crowd }}
          </div>
          <div class="card-subtext">Pedestrian counting data</div>
        </div>
      </div>

      <!-- Interactive 9 AM - 5 PM Hourly Daytime Strip -->
      <div class="timeline-section" role="region" aria-label="Daytime hour exploration">
        <div class="timeline-header">
          <span class="timeline-title">Explore Daytime Hours (9:00 AM – 5:00 PM)</span>
          <button 
            v-if="selectedHour !== 10" 
            type="button" 
            class="reset-quiet-btn"
            @click="selectedHour = 10"
          >
            Reset to quietest hour (10 AM)
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
            @click="selectedHour = item.hour"
          >
            <span class="hour-label">{{ item.label }}</span>
            <span v-if="item.isRecommended" class="hour-tag">Quietest</span>
          </button>
        </div>
      </div>

      <!-- Action Buttons Row -->
      <div class="actions-row">
        <button
          type="button"
          class="btn-primary"
          @click="handleUseForPreparation"
        >
          Use for my preparation &rarr;
        </button>
      </div>

      <!-- Preparation Confirmation Banner -->
      <div 
        v-if="showPreparedToast" 
        class="preparation-banner" 
        role="status" 
        aria-live="polite"
      >
        <span class="banner-icon" aria-hidden="true">&#10003;</span>
        <div class="banner-text">
          <strong>Sensory schedule saved!</strong> 
          Quiet window of {{ activeHourData.window }} on {{ selectedDay }} is saved for your preparation.
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sensory-schedule-container {
  max-width: 960px;
  margin: 0 auto;
  padding: 1.5rem 1rem 4rem;
}

.back-link-bar {
  margin-bottom: 1.25rem;
}

.return-btn {
  background: #ffffff;
  border: 1.5px solid #badcd0;
  color: #175d52;
  padding: 0.6rem 1.15rem;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 750;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.return-btn:hover {
  background: #175d52;
  color: #ffffff;
}

.sensory-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2.25rem;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.02em;
  margin-bottom: 0.5rem;
}

.page-subtitle {
  font-size: 1.125rem;
  color: #4b5563;
  line-height: 1.6;
  max-width: 720px;
}

/* Scheduler Main Card */
.scheduler-card {
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  padding: 2.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.search-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.search-label {
  font-size: 1.05rem;
  font-weight: 700;
  color: #111827;
}

.input-wrapper {
  position: relative;
  width: 100%;
}

.destination-input {
  width: 100%;
  padding: 0.875rem 1.25rem;
  font-size: 1.125rem;
  color: #111827;
  background-color: #ffffff;
  border: 1.5px solid #d1d5db;
  border-radius: 12px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  min-height: 52px;
}

.destination-input:focus {
  border-color: #1d443b;
  box-shadow: 0 0 0 3px rgba(29, 68, 59, 0.2);
}

/* Suggestion Chips */
.suggestions-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.15rem;
}

.suggestion-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 600;
}

.suggestion-chip {
  background-color: #f3f4f6;
  color: #374151;
  border: 1px solid #e5e7eb;
  padding: 0.3rem 0.75rem;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s;
}

.suggestion-chip:hover {
  background-color: #e5e7eb;
}

.suggestion-chip.active {
  background-color: #eaf4f0;
  color: #1d443b;
  border-color: #c7e2d6;
  font-weight: 600;
}

/* Pill Badges */
.pills-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.625rem;
  align-items: center;
  margin-top: 0.5rem;
}

.pill-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.35rem 0.85rem;
  font-size: 0.8125rem;
  font-weight: 600;
  border-radius: 9999px;
  line-height: 1.4;
}

.pill-badge-primary {
  background-color: #eaf4f0;
  color: #1d443b;
  border: 1px solid #c7e2d6;
  letter-spacing: 0.04em;
  font-weight: 700;
}

.pill-badge-secondary {
  background-color: #f0f7f4;
  color: #2b5a50;
  border: 1px solid #d8eae1;
}

.helper-note {
  font-size: 0.95rem;
  color: #6b7280;
  line-height: 1.5;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}

/* Results Header Row */
.results-header-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  margin-top: 2rem;
  margin-bottom: 1.25rem;
}

.results-heading {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.01em;
}

.day-select {
  padding: 0.4rem 0.85rem;
  border: 1.5px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #1f2937;
  background-color: #ffffff;
  outline: none;
  cursor: pointer;
}

.day-select:focus {
  border-color: #1d443b;
}

/* 3 Sensory Summary Cards Grid */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  margin-bottom: 1.75rem;
}

@media (max-width: 800px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }
}

.summary-card {
  border-radius: 16px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  min-height: 160px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.card-recommended {
  background-color: #eaf4f0;
  border: 1.5px solid #c7e2d6;
}

.card-selected {
  background-color: #f3f8f5;
  border: 1.5px solid #a8d5c0;
}

.card-neutral {
  background-color: #ffffff;
  border: 1.5px solid #e5e7eb;
}

.card-overline {
  font-size: 1.05rem;
  font-weight: 700;
  color: #111827;
  margin-bottom: 0.875rem;
}

.card-main-value {
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: 0.5rem;
  line-height: 1.2;
}

.text-recommended {
  color: #1d443b;
}

.text-neutral {
  color: #111827;
}

.card-subtext {
  font-size: 0.95rem;
  color: #6b7280;
  line-height: 1.4;
}

/* Timeline Daytime Hours Strip */
.timeline-section {
  background-color: #f9fafb;
  border: 1px solid #f3f4f6;
  border-radius: 14px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.875rem;
}

.timeline-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #374151;
}

.reset-quiet-btn {
  background: none;
  border: none;
  color: #1d443b;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}

.hours-strip {
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
  padding-bottom: 0.5rem;
}

.hour-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  padding: 0.625rem 0.5rem;
  background-color: #ffffff;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.hour-btn:hover {
  border-color: #c7e2d6;
  background-color: #f0f7f4;
}

.hour-btn.selected {
  border-color: #1d443b;
  background-color: #eaf4f0;
  box-shadow: 0 0 0 2px rgba(29, 68, 59, 0.15);
}

.hour-label {
  font-size: 0.9375rem;
  font-weight: 700;
  color: #111827;
}

.hour-tag {
  font-size: 0.6875rem;
  font-weight: 700;
  color: #1d443b;
  background-color: #d1ebd8;
  padding: 0.15rem 0.35rem;
  border-radius: 4px;
  margin-top: 0.25rem;
}

/* Actions Row */
.actions-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  margin-top: 1.5rem;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: #1d443b;
  color: #ffffff;
  font-size: 1.0625rem;
  font-weight: 700;
  padding: 0.875rem 1.75rem;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s, transform 0.1s;
  min-height: 48px;
}

.btn-primary:hover {
  background-color: #15332c;
}

.btn-primary:focus-visible {
  outline: 3px solid #1d443b;
  outline-offset: 3px;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: #ffffff;
  color: #111827;
  font-size: 1.0625rem;
  font-weight: 700;
  padding: 0.875rem 1.75rem;
  border-radius: 12px;
  border: 1.5px solid #d1d5db;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s;
  min-height: 48px;
}

.btn-secondary:hover {
  background-color: #f9fafb;
  border-color: #9ca3af;
}

.btn-secondary:focus-visible {
  outline: 3px solid #1d443b;
  outline-offset: 3px;
}

.preparation-banner {
  margin-top: 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background-color: #eaf4f0;
  border: 1.5px solid #c7e2d6;
  border-radius: 12px;
  color: #1d443b;
  font-size: 1rem;
}

.banner-icon {
  font-weight: 900;
  font-size: 1.25rem;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Accessibility Focus States */
.suggestion-chip:focus-visible,
.hour-btn:focus-visible,
.day-select:focus-visible {
  outline: 3px solid #1d443b;
  outline-offset: 2px;
}

/* Accessibility Text Scaling for Seniors */
:global(.text-large) .page-title {
  font-size: 2.75rem;
}

:global(.text-large) .card-main-value {
  font-size: 2.35rem;
}

:global(.text-large) .card-overline {
  font-size: 1.25rem;
}

:global(.text-large) .destination-input {
  font-size: 1.35rem;
}

:global(.text-xlarge) .page-title {
  font-size: 3.25rem;
}

:global(.text-xlarge) .card-main-value {
  font-size: 2.75rem;
}

:global(.text-xlarge) .card-overline {
  font-size: 1.45rem;
}

:global(.text-xlarge) .destination-input {
  font-size: 1.55rem;
}
</style>
