<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import type { ViewState } from '../App.vue'

const navigateTo = inject<(view: ViewState) => void>('navigateTo', () => {})

const emit = defineEmits<{
  (e: 'proceed'): void
}>()

// 3 Major Interactive Demonstration Scenes:
// 1: 'indoor' - Indoor Spaces, Dementia Low Contrast vs Fix, and Camera Photo Audit
// 2: 'checklist' - Outing Preparation, Departure Checklist, and Pocket Support Card
// 3: 'walk' - Safe Outing Route: Straight path, Tree canopies, Rest benches
type Scene = 'indoor' | 'checklist' | 'walk'
const currentScene = ref<Scene>('indoor')

const isPlaying = ref(true)
const showWelcomeMsg = ref(false) // Keep clean since story panel now introduces context
let autoPlayTimer: number | null = null
let scenePhaseTimer: number | null = null

// --- SCENE 1: INDOOR & AUDIT STATE ---
const toiletContrastOn = ref(false)
const rugRemoved = ref(false)
const grabBarContrastOn = ref(false)
const isCameraScanning = ref(false)

// --- SCENE 2: CHECKLIST & POCKET CARD STATE ---
const checkKeys = ref(false)
const checkCard = ref(false)
const checkWater = ref(false)
const checkPhone = ref(false)
const pocketCardCompiled = ref(false)

// --- SCENE 3: SAFE OUTING WALK STATE ---
const canopyActive = ref(false)
const benchPresent = ref(false)
const straightPathActive = ref(false)

// Minimalist typewriter intro text in simple few words
const INTRO_LINES = [
  'Everyday environments can feel overwhelming for people living with dementia.',
  'NeighbourlyMinds makes spaces and routines simpler to navigate — reducing cognitive load and supporting daily independence.'
]

const allIntroWords = computed(() => {
  return INTRO_LINES.join(' \n\n ').split(' ')
})

const typedWordsCount = ref(0)
const isTyping = ref(false)
let typingTimer: number | null = null

const startTypewriter = () => {
  if (typingTimer) clearInterval(typingTimer)
  typedWordsCount.value = 0
  isTyping.value = true

  const total = allIntroWords.value.length
  typingTimer = window.setInterval(() => {
    if (typedWordsCount.value < total) {
      typedWordsCount.value++
    } else {
      if (typingTimer) clearInterval(typingTimer)
      isTyping.value = false
    }
  }, 70)
}

const displayedLines = computed(() => {
  const currentText = allIntroWords.value.slice(0, typedWordsCount.value).join(' ')
  return currentText
    .split('\n\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
})

// Character happiness reaction (Before using app: Angry & Stressed -> After using app: Happy & Calmer)
const isCharacterHappy = computed(() => {
  if (currentScene.value === 'indoor') {
    return toiletContrastOn.value && rugRemoved.value
  } else if (currentScene.value === 'checklist') {
    return checkKeys.value && checkCard.value && pocketCardCompiled.value
  } else {
    return canopyActive.value && benchPresent.value && straightPathActive.value
  }
})

// Scene Timings (in ms)
const SCENE_DURATIONS: Record<Scene, number> = {
  indoor: 7500,
  checklist: 7000,
  walk: 7500
}

// Cognitive load dynamically computed per scene
const cognitiveLoad = computed(() => {
  if (currentScene.value === 'indoor') {
    let load = 90
    if (toiletContrastOn.value) load -= 35
    if (rugRemoved.value) load -= 40
    return Math.max(15, load)
  } else if (currentScene.value === 'checklist') {
    let checkedCount = (checkKeys.value ? 1 : 0) + (checkCard.value ? 1 : 0) + (checkWater.value ? 1 : 0) + (checkPhone.value ? 1 : 0)
    let load = 85 - checkedCount * 15
    if (pocketCardCompiled.value) load -= 15
    return Math.max(15, load)
  } else {
    // walk scene
    let load = 80
    if (canopyActive.value) load -= 25
    if (benchPresent.value) load -= 25
    if (straightPathActive.value) load -= 15
    return Math.max(15, load)
  }
})

const resetSceneToBefore = (scene: Scene) => {
  if (scene === 'indoor') {
    toiletContrastOn.value = false
    rugRemoved.value = false
    grabBarContrastOn.value = false
  } else if (scene === 'checklist') {
    checkKeys.value = false
    checkCard.value = false
    checkWater.value = false
    checkPhone.value = false
    pocketCardCompiled.value = false
  } else {
    canopyActive.value = false
    benchPresent.value = false
    straightPathActive.value = false
  }
}

const applySceneSolution = (scene: Scene) => {
  if (scene === 'indoor') {
    triggerCameraScan()
    setTimeout(() => {
      toiletContrastOn.value = true
      rugRemoved.value = true
      grabBarContrastOn.value = true
    }, 700)
  } else if (scene === 'checklist') {
    checkKeys.value = true
    checkWater.value = true
    checkPhone.value = true
    setTimeout(() => {
      checkCard.value = true
      pocketCardCompiled.value = true
    }, 450)
  } else {
    straightPathActive.value = true
    canopyActive.value = true
    benchPresent.value = true
  }
}

// Auto-play scene loop
const scheduleNextScene = () => {
  if (!isPlaying.value) return
  if (autoPlayTimer) clearTimeout(autoPlayTimer)

  const currentDuration = SCENE_DURATIONS[currentScene.value]
  autoPlayTimer = window.setTimeout(() => {
    if (!isPlaying.value) return
    if (currentScene.value === 'indoor') {
      setScene('checklist', false)
    } else if (currentScene.value === 'checklist') {
      setScene('walk', false)
    } else {
      setScene('indoor', false)
    }
    scheduleNextScene()
  }, currentDuration)
}

const setScene = (scene: Scene, manualClick = true) => {
  currentScene.value = scene
  if (scenePhaseTimer) clearTimeout(scenePhaseTimer)

  // 1. Start in Before phase (Angry / Stressed)
  resetSceneToBefore(scene)

  // 2. After 2.6 seconds, apply NeighbourlyMinds solution (Transforms to Happy & Relieved)
  scenePhaseTimer = window.setTimeout(() => {
    applySceneSolution(scene)
  }, 2600)

  if (manualClick) {
    if (autoPlayTimer) clearTimeout(autoPlayTimer)
    scheduleNextScene()
  }
}

const togglePlayPause = () => {
  isPlaying.value = !isPlaying.value
  if (isPlaying.value) {
    scheduleNextScene()
  } else {
    if (autoPlayTimer) clearTimeout(autoPlayTimer)
    if (scenePhaseTimer) clearTimeout(scenePhaseTimer)
  }
}

const restartAll = () => {
  isPlaying.value = true
  setScene('indoor', true)
}

const triggerCameraScan = () => {
  isCameraScanning.value = true
  setTimeout(() => {
    isCameraScanning.value = false
  }, 2200)
}

onMounted(() => {
  startTypewriter()
  setScene('indoor', false)
  scheduleNextScene()
})

onUnmounted(() => {
  if (autoPlayTimer) clearTimeout(autoPlayTimer)
  if (scenePhaseTimer) clearTimeout(scenePhaseTimer)
  if (typingTimer) clearInterval(typingTimer)
})
</script>

<template>
  <div class="intro-split-layout" role="region" aria-label="NeighbourlyMinds Visual Story & Simulation">
    <!-- LEFT 65%: SVG ANIMATION COLUMN -->
    <div class="animation-column" aria-label="Interactive Visual Simulation">
      <svg 
        class="stage-svg" 
        viewBox="0 0 1200 750" 
        preserveAspectRatio="xMidYMid slice"
        role="img"
        aria-label="Animated illustration of indoor adjustments, departure checklist, and safe outdoor routes"
      >
      <defs>
        <!-- Soft Drop Shadow -->
        <filter id="scene-shadow" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="10" stdDeviation="12" flood-opacity="0.16" flood-color="#0f172a"/>
        </filter>

        <!-- Golden Glow Filter -->
        <filter id="item-glow" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="8" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <!-- Floor Glare Shimmer Gradient -->
        <radialGradient id="floor-glare" cx="50%" cy="40%" r="50%">
          <stop offset="0%" stop-color="#ffffff" stop-opacity="0.75" />
          <stop offset="45%" stop-color="#ffffff" stop-opacity="0.25" />
          <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
        </radialGradient>

        <!-- Abyss Black Hole Gradient -->
        <radialGradient id="hole-vortex" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#000000" stop-opacity="1" />
          <stop offset="55%" stop-color="#090d16" stop-opacity="0.95" />
          <stop offset="80%" stop-color="#1f2937" stop-opacity="0.85" />
          <stop offset="100%" stop-color="#374151" stop-opacity="0" />
        </radialGradient>

        <!-- Wall Tiles Pattern -->
        <pattern id="indoor-tiles" width="60" height="60" patternUnits="userSpaceOnUse">
          <rect width="60" height="60" fill="#f8fafc" />
          <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#e2e8f0" stroke-width="1.5" />
        </pattern>

        <!-- Outdoor Grass Pattern -->
        <linearGradient id="grass-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#e2ede5" />
          <stop offset="100%" stop-color="#c9dfd1" />
        </linearGradient>

        <!-- Sky Gradient -->
        <linearGradient id="sky-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#dbeafe" />
          <stop offset="70%" stop-color="#eff6ff" />
          <stop offset="100%" stop-color="#f8fafc" />
        </linearGradient>

        <!-- Tree Canopy Gradient -->
        <radialGradient id="canopy-gradient" cx="50%" cy="40%" r="50%">
          <stop offset="0%" stop-color="#2d6a4f" />
          <stop offset="60%" stop-color="#1b4332" />
          <stop offset="100%" stop-color="#081c15" />
        </radialGradient>
      </defs>

      <!-- ======================================================== -->
      <!-- SCENE 1: INDOOR SPACES, HIGH CONTRAST & CAMERA ROOM AUDIT -->
      <!-- ======================================================== -->
      <g v-if="currentScene === 'indoor'" class="scene-indoor">
        <!-- Fullscreen Wall Tiles -->
        <rect x="-300" y="-200" width="1800" height="680" fill="url(#indoor-tiles)" />
        <rect x="-300" y="-200" width="1800" height="240" fill="black" opacity="0.02" />

        <!-- Floor -->
        <rect x="-300" y="470" width="1800" height="600" :fill="!toiletContrastOn ? '#fcfdfd' : '#e8edea'" class="transition-smooth" />
        <!-- Skirting Baseboard -->
        <rect x="-300" y="462" width="1800" height="10" :fill="!toiletContrastOn ? '#e2e8f0' : '#175d52'" class="transition-smooth" />

        <!-- Glare if contrast not fixed -->
        <ellipse v-if="!toiletContrastOn" cx="660" cy="530" rx="220" ry="50" fill="url(#floor-glare)" class="glare-animation" />

        <!-- High-Contrast Safe Guide Line on floor -->
        <path v-if="toiletContrastOn" d="M 440 600 Q 640 575 800 550" fill="none" stroke="#175d52" stroke-width="7" stroke-dasharray="12 8" class="safe-path-dash" />

        <!-- Floor Rug / Abyss -->
        <g class="interactive-element" @click="rugRemoved = !rugRemoved">
          <!-- Normal / Fixed Floor (Rug Removed) -->
          <g v-if="rugRemoved">
            <ellipse cx="620" cy="580" rx="100" ry="32" fill="#d1fae5" stroke="#10b981" stroke-width="2" stroke-dasharray="6 4" opacity="0.6" />
            <text x="620" y="585" text-anchor="middle" font-size="14" fill="#047857" font-weight="bold">✓ SAFE CONTINUOUS FLOOR</text>
          </g>
          <!-- Deceptive Black Hole Rug Illusion -->
          <g v-else class="black-hole-group">
            <ellipse cx="620" cy="580" rx="135" ry="48" fill="url(#hole-vortex)" class="vortex-spinning" />
            <ellipse cx="620" cy="580" rx="98" ry="34" fill="#000000" />
            <ellipse cx="620" cy="580" rx="68" ry="22" fill="#050505" stroke="#dc2626" stroke-width="2.5" stroke-dasharray="6 6" />
            <text x="620" y="588" text-anchor="middle" font-size="24" fill="#ef4444">⚠️</text>
            <ellipse cx="620" cy="580" rx="150" ry="54" fill="none" stroke="#ef4444" stroke-width="2" opacity="0.5" class="hazard-ripple" />
          </g>
        </g>

        <!-- Grab Bar / Rail -->
        <g class="interactive-element" @click="grabBarContrastOn = !grabBarContrastOn">
          <rect x="740" y="240" width="14" height="18" rx="4" :fill="grabBarContrastOn ? '#175d52' : '#94a3b8'" />
          <rect x="740" y="380" width="14" height="18" rx="4" :fill="grabBarContrastOn ? '#175d52' : '#94a3b8'" />
          <rect 
            x="743" 
            y="240" 
            width="12" 
            height="158" 
            rx="6" 
            :fill="grabBarContrastOn ? '#f59e0b' : '#cbd5e1'" 
            :stroke="grabBarContrastOn ? '#b45309' : '#94a3b8'" 
            stroke-width="3"
            :filter="grabBarContrastOn ? 'url(#item-glow)' : 'none'"
            class="transition-smooth" 
          />
          <g v-if="grabBarContrastOn">
            <line x1="743" y1="280" x2="755" y2="280" stroke="#78350f" stroke-width="3" />
            <line x1="743" y1="315" x2="755" y2="315" stroke="#78350f" stroke-width="3" />
            <line x1="743" y1="350" x2="755" y2="350" stroke="#78350f" stroke-width="3" />
          </g>
        </g>

        <!-- The Toilet (Low Contrast vs High Contrast Seat) -->
        <g class="interactive-element" @click="toiletContrastOn = !toiletContrastOn">
          <rect x="830" y="200" width="105" height="180" rx="12" fill="#ffffff" stroke="#cbd5e1" stroke-width="3" filter="url(#scene-shadow)" />
          <rect x="824" y="190" width="117" height="16" rx="6" fill="#ffffff" stroke="#cbd5e1" stroke-width="3" />
          <circle cx="882" cy="198" r="6" fill="#94a3b8" />
          <path d="M 830 360 Q 800 430 820 520 L 890 520 Q 920 430 895 360 Z" fill="#ffffff" stroke="#cbd5e1" stroke-width="3" />
          <ellipse cx="855" cy="520" rx="42" ry="10" fill="#e2e8f0" />
          <ellipse cx="835" cy="365" rx="58" ry="32" fill="#ffffff" stroke="#cbd5e1" stroke-width="3" />

          <!-- Low Contrast (Invisible) vs Bold Royal Blue Seat -->
          <g v-if="!toiletContrastOn">
            <ellipse cx="832" cy="362" rx="60" ry="33" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5" opacity="0.6" />
            <text x="832" y="372" text-anchor="middle" font-size="26" fill="#94a3b8">❓</text>
          </g>
          <g v-else filter="url(#scene-shadow)">
            <ellipse cx="832" cy="362" rx="62" ry="34" fill="#1d4ed8" stroke="#1e3a8a" stroke-width="4" />
            <ellipse cx="832" cy="362" rx="38" ry="20" fill="#ffffff" stroke="#172554" stroke-width="3" />
            <circle cx="832" cy="362" r="68" fill="none" stroke="#38bdf8" stroke-width="2" stroke-dasharray="6 6" class="seat-glow-ring" />
          </g>
        </g>

        <!-- CAMERA SCANNING HUD (FEATURE 1: Take picture of rooms / Environment Auditor) -->
        <g class="camera-audit-overlay" @click="triggerCameraScan" style="cursor: pointer;">
          <!-- Camera Viewfinder Corners -->
          <path d="M 690 170 L 670 170 L 670 190" fill="none" stroke="#10b981" stroke-width="4" />
          <path d="M 960 170 L 980 170 L 980 190" fill="none" stroke="#10b981" stroke-width="4" />
          <path d="M 690 540 L 670 540 L 670 520" fill="none" stroke="#10b981" stroke-width="4" />
          <path d="M 960 540 L 980 540 L 980 520" fill="none" stroke="#10b981" stroke-width="4" />

          <!-- Camera Badge / Shutter icon -->
          <g transform="translate(685, 125)">
            <rect x="0" y="0" width="165" height="36" rx="18" fill="rgba(16, 185, 129, 0.95)" />
            <text x="14" y="24" font-size="18">📸</text>
            <text x="42" y="23" font-size="12" fill="white" font-weight="bold">PHOTO AUDIT & SCAN</text>
          </g>

          <!-- Laser Scan Line sweeping vertically -->
          <line v-if="isCameraScanning" x1="670" y1="180" x2="980" y2="180" stroke="#34d399" stroke-width="4" class="laser-scanner" />

          <!-- AI Detection Badges -->
          <g transform="translate(710, 215)">
            <rect x="0" y="0" width="125" height="24" rx="6" fill="#0f766e" opacity="0.9" />
            <text x="8" y="16" font-size="11" fill="#ffffff" font-weight="bold">✓ High Contrast 7.8:1</text>
          </g>
          <g transform="translate(560, 520)">
            <rect x="0" y="0" width="120" height="24" rx="6" fill="#0f766e" opacity="0.9" />
            <text x="8" y="16" font-size="11" fill="#ffffff" font-weight="bold">✓ Zero Trip Hazard</text>
          </g>
        </g>
      </g>

      <!-- ======================================================== -->
      <!-- SCENE 2: OUTING PREPARATION, CHECKLIST & POCKET SUPPORT CARD -->
      <!-- ======================================================== -->
      <g v-else-if="currentScene === 'checklist'" class="scene-checklist">
        <!-- Hallway Exit Wall -->
        <rect x="-300" y="-200" width="1800" height="680" fill="#f8fafc" />
        <rect x="-300" y="470" width="1800" height="600" fill="#ede8e1" />
        <rect x="-300" y="462" width="1800" height="10" fill="#78350f" opacity="0.8" />

        <!-- Front Exit Door with Handle -->
        <rect x="800" y="140" width="220" height="420" rx="8" fill="#175d52" stroke="#0f3d36" stroke-width="4" filter="url(#scene-shadow)" />
        <rect x="820" y="160" width="80" height="160" rx="4" fill="#1b6e61" />
        <rect x="920" y="160" width="80" height="160" rx="4" fill="#1b6e61" />
        <circle cx="828" cy="360" r="12" fill="#f59e0b" filter="url(#item-glow)" />

        <!-- INTERACTIVE DEPARTURE CHECKLIST BOARD -->
        <g class="checklist-board-group" transform="translate(480, 150)">
          <!-- Clipboard frame -->
          <rect x="0" y="0" width="270" height="340" rx="20" fill="white" stroke="#175d52" stroke-width="3" filter="url(#scene-shadow)" />
          <rect x="90" y="-12" width="90" height="24" rx="8" fill="#175d52" />
          <circle cx="135" cy="0" r="5" fill="#fef3c7" />

          <!-- Title -->
          <text x="25" y="45" font-size="16" font-weight="bold" fill="#175d52">📋 DEPARTURE CHECKLIST</text>
          <line x1="25" y1="58" x2="245" y2="58" stroke="#e2e8f0" stroke-width="2" />

          <!-- Item 1: Keys -->
          <g class="interactive-element" transform="translate(25, 75)" @click="checkKeys = !checkKeys">
            <rect x="0" y="0" width="220" height="42" rx="10" :fill="checkKeys ? '#ecfdf5' : '#f8fafc'" :stroke="checkKeys ? '#10b981' : '#cbd5e1'" stroke-width="1.5" />
            <text x="14" y="27" font-size="20">🔑</text>
            <text x="48" y="26" font-size="14" font-weight="bold" fill="#1e293b">House Keys</text>
            <circle cx="195" cy="21" r="12" :fill="checkKeys ? '#10b981' : '#e2e8f0'" />
            <text v-if="checkKeys" x="195" y="26" text-anchor="middle" font-size="14" fill="white" font-weight="bold">✓</text>
          </g>

          <!-- Item 2: Cards / ID -->
          <g class="interactive-element" transform="translate(25, 127)" @click="checkCard = !checkCard">
            <rect x="0" y="0" width="220" height="42" rx="10" :fill="checkCard ? '#ecfdf5' : '#f8fafc'" :stroke="checkCard ? '#10b981' : '#cbd5e1'" stroke-width="1.5" />
            <text x="14" y="27" font-size="20">💳</text>
            <text x="48" y="26" font-size="14" font-weight="bold" fill="#1e293b">Travel Card / ID</text>
            <circle cx="195" cy="21" r="12" :fill="checkCard ? '#10b981' : '#e2e8f0'" />
            <text v-if="checkCard" x="195" y="26" text-anchor="middle" font-size="14" fill="white" font-weight="bold">✓</text>
          </g>

          <!-- Item 3: Water Bottle -->
          <g class="interactive-element" transform="translate(25, 179)" @click="checkWater = !checkWater">
            <rect x="0" y="0" width="220" height="42" rx="10" :fill="checkWater ? '#ecfdf5' : '#f8fafc'" :stroke="checkWater ? '#10b981' : '#cbd5e1'" stroke-width="1.5" />
            <text x="14" y="27" font-size="20">💧</text>
            <text x="48" y="26" font-size="14" font-weight="bold" fill="#1e293b">Water Bottle</text>
            <circle cx="195" cy="21" r="12" :fill="checkWater ? '#10b981' : '#e2e8f0'" />
            <text v-if="checkWater" x="195" y="26" text-anchor="middle" font-size="14" fill="white" font-weight="bold">✓</text>
          </g>

          <!-- Item 4: Phone -->
          <g class="interactive-element" transform="translate(25, 231)" @click="checkPhone = !checkPhone">
            <rect x="0" y="0" width="220" height="42" rx="10" :fill="checkPhone ? '#ecfdf5' : '#f8fafc'" :stroke="checkPhone ? '#10b981' : '#cbd5e1'" stroke-width="1.5" />
            <text x="14" y="27" font-size="20">📱</text>
            <text x="48" y="26" font-size="14" font-weight="bold" fill="#1e293b">Phone Charged</text>
            <circle cx="195" cy="21" r="12" :fill="checkPhone ? '#10b981' : '#e2e8f0'" />
            <text v-if="checkPhone" x="195" y="26" text-anchor="middle" font-size="14" fill="white" font-weight="bold">✓</text>
          </g>

          <!-- Status badge -->
          <g transform="translate(25, 285)">
            <rect x="0" y="0" width="220" height="34" rx="8" :fill="checkKeys && checkCard && pocketCardCompiled ? '#175d52' : '#dc2626'" />
            <text x="110" y="22" text-anchor="middle" font-size="12" fill="white" font-weight="bold">
              {{ checkKeys && checkCard && pocketCardCompiled ? 'READY FOR SAFE OUTING ✨' : '⚠️ ITEMS MISSING & UNPREPARED' }}
            </text>
          </g>
        </g>

        <!-- PRINTED POCKET SUPPORT CARD (FEATURE 2) -->
        <g class="pocket-card-showcase interactive-element" transform="translate(780, 280)" @click="pocketCardCompiled = !pocketCardCompiled">
          <!-- Folded card with yellow fold guide lines -->
          <rect x="0" y="0" width="240" height="150" rx="12" fill="#ffffff" stroke="#f59e0b" stroke-width="3" filter="url(#scene-shadow)" />
          <!-- Yellow fold line -->
          <line x1="120" y1="0" x2="120" y2="150" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4 4" />

          <!-- Panel 1: Route Landmarks -->
          <g transform="translate(15, 18)">
            <text x="0" y="14" font-size="11" font-weight="bold" fill="#175d52">📇 POCKET SUPPORT CARD</text>
            <text x="0" y="34" font-size="10" fill="#334155">1. 🚶 Walk straight 200m</text>
            <text x="0" y="52" font-size="10" fill="#334155">2. 🏪 Clocktower landmark</text>
            <text x="0" y="70" font-size="10" fill="#334155">3. 🪑 Shady rest bench</text>
            <text x="0" y="90" font-size="10" font-weight="bold" fill="#047857">✓ Calm Low Sensory Route</text>
          </g>

          <!-- Panel 2: Emergency Contact & Support Badges -->
          <g transform="translate(135, 18)">
            <rect x="0" y="0" width="90" height="42" rx="6" fill="#fef2f2" stroke="#ef4444" stroke-width="1.5" />
            <text x="8" y="18" font-size="11" fill="#dc2626" font-weight="bold">🚨 ICE CONTACT</text>
            <text x="8" y="34" font-size="10" fill="#991b1b">📞 0400 123 456</text>

            <rect x="0" y="52" width="90" height="32" rx="6" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.5" />
            <text x="6" y="72" font-size="10" fill="#1d4ed8" font-weight="bold">🗣️ Speak Slowly</text>
            
            <circle cx="45" cy="106" r="14" fill="#10b981" />
            <text x="45" y="111" text-anchor="middle" font-size="12" fill="white" font-weight="bold">✓</text>
          </g>
        </g>
      </g>

      <!-- ======================================================== -->
      <!-- SCENE 3: SAFE OUTING PREPARATION: STRAIGHT PATH, CANOPY, BENCH -->
      <!-- ======================================================== -->
      <g v-else class="scene-walk">
        <!-- Sky & Clouds -->
        <rect x="-300" y="-200" width="1800" height="600" fill="url(#sky-gradient)" />
        <ellipse cx="250" cy="120" rx="90" ry="35" fill="white" opacity="0.8" />
        <ellipse cx="780" cy="90" rx="120" ry="40" fill="white" opacity="0.85" />
        <circle cx="1020" cy="80" r="45" fill="#fef08a" opacity="0.8" filter="url(#item-glow)" />

        <!-- Distant Town Landmarks & Trees -->
        <rect x="750" y="240" width="80" height="140" fill="#cbd5e1" opacity="0.7" />
        <polygon points="790,200 750,240 830,240" fill="#94a3b8" opacity="0.7" />
        <circle cx="790" cy="250" r="12" fill="white" />
        <!-- Clock hands -->
        <line x1="790" y1="250" x2="790" y2="242" stroke="#334155" stroke-width="2" />
        <line x1="790" y1="250" x2="796" y2="250" stroke="#334155" stroke-width="2" />

        <!-- Green Lawn / Park -->
        <rect x="-300" y="380" width="1800" height="500" fill="url(#grass-gradient)" />

        <!-- FEATURE: STRAIGHT PREDICTABLE WALKING PATH (No confusing splits) -->
        <g class="interactive-element" @click="straightPathActive = !straightPathActive">
          <polygon points="400,380 900,380 1100,750 300,750" fill="#f1f5f9" stroke="#cbd5e1" stroke-width="2" />
          <line x1="650" y1="380" x2="700" y2="750" stroke="#175d52" stroke-width="4" stroke-dasharray="16 12" />
          <g transform="translate(620, 680)">
            <rect x="0" y="0" width="160" height="28" rx="14" fill="#175d52" opacity="0.95" />
            <text x="80" y="19" text-anchor="middle" font-size="12" fill="white" font-weight="bold">🛣️ STRAIGHT SAFE PATH</text>
          </g>
        </g>

        <!-- FEATURE: TREE CANOPY (SHADE & GLARE PROTECTION) -->
        <g class="interactive-element" @click="canopyActive = !canopyActive">
          <!-- Tree Trunk 1 -->
          <rect x="180" y="220" width="36" height="200" fill="#78350f" rx="6" />
          <!-- Big Lush Canopy providing dappled shade -->
          <ellipse cx="200" cy="180" rx="140" ry="90" fill="url(#canopy-gradient)" filter="url(#scene-shadow)" />
          <ellipse cx="280" cy="140" rx="90" ry="70" fill="#2d6a4f" opacity="0.85" />
          
          <!-- Tree Trunk 2 (Right) -->
          <rect x="980" y="200" width="40" height="220" fill="#78350f" rx="6" />
          <ellipse cx="1000" cy="160" rx="160" ry="100" fill="url(#canopy-gradient)" filter="url(#scene-shadow)" />

          <!-- Dappled pleasant shade on the path -->
          <ellipse v-if="canopyActive" cx="480" cy="460" rx="140" ry="40" fill="#0f172a" opacity="0.12" />
          
          <g transform="translate(240, 150)">
            <rect x="-95" y="-14" width="190" height="28" rx="14" :fill="canopyActive ? '#0f766e' : '#dc2626'" opacity="0.95" />
            <text x="0" y="5" text-anchor="middle" font-size="12" fill="white" font-weight="bold">
              {{ canopyActive ? '🌳 SHADY TREE CANOPY' : '☀️ HARSH GLARE / NO SHADE' }}
            </text>
          </g>
        </g>

        <!-- FEATURE: PARK RESTING BENCH -->
        <g class="interactive-element" @click="benchPresent = !benchPresent" transform="translate(780, 420)">
          <template v-if="benchPresent">
            <!-- Wood slats & cast iron frame -->
            <rect x="0" y="25" width="160" height="12" rx="4" fill="#b45309" filter="url(#scene-shadow)" />
            <rect x="0" y="42" width="160" height="10" rx="3" fill="#92400e" />
            <rect x="0" y="56" width="160" height="10" rx="3" fill="#78350f" />
            <!-- Legs -->
            <rect x="15" y="66" width="10" height="40" fill="#1e293b" rx="2" />
            <rect x="135" y="66" width="10" height="40" fill="#1e293b" rx="2" />
            <rect x="5" y="20" width="10" height="70" fill="#1e293b" rx="2" />
            <rect x="145" y="20" width="10" height="70" fill="#1e293b" rx="2" />

            <!-- Rest badge -->
            <g transform="translate(15, -15)">
              <rect x="0" y="0" width="130" height="26" rx="13" fill="#175d52" />
              <text x="65" y="18" text-anchor="middle" font-size="11" fill="white" font-weight="bold">🪑 REST BENCH (90m)</text>
            </g>
          </template>
          <template v-else>
            <rect x="0" y="25" width="160" height="50" rx="8" fill="#fee2e2" stroke="#ef4444" stroke-width="2" stroke-dasharray="6 4" opacity="0.9" />
            <text x="80" y="55" text-anchor="middle" font-size="12" fill="#b91c1c" font-weight="bold">⚠️ NO REST BENCHES</text>
          </template>
        </g>
      </g>

      <!-- ======================================================== -->
      <!-- THE SENIOR CHARACTER (MOVES & ADAPTS PER SCENE) -->
      <!-- ======================================================== -->
      <g 
        class="character-entity transition-smooth" 
        :transform="currentScene === 'walk' ? 'translate(80, 20)' : (currentScene === 'checklist' ? 'translate(-40, 10)' : 'translate(0, 0)')"
      >
        <!-- Ground Shadow -->
        <ellipse cx="360" cy="620" rx="55" ry="16" fill="#94a3b8" opacity="0.3" />

        <!-- Legs & Shoes -->
        <rect x="332" y="510" width="22" height="105" rx="10" fill="#1e293b" />
        <rect x="366" y="510" width="22" height="105" rx="10" fill="#1e293b" />
        <ellipse cx="340" cy="615" rx="16" ry="9" fill="#78350f" />
        <ellipse cx="378" cy="615" rx="16" ry="9" fill="#78350f" />

        <!-- Cardigan & Sweater -->
        <rect x="310" y="350" width="100" height="170" rx="28" fill="#175d52" />
        <path d="M 342 350 L 360 420 L 378 350 Z" fill="#d97706" />
        <line x1="360" y1="420" x2="360" y2="520" stroke="#0f3d36" stroke-width="3" />

        <!-- Pocket with Folded Pocket Card peaking out! -->
        <g transform="translate(378, 435)">
          <path d="M 0 0 L 22 0 L 22 18 Q 11 24 0 18 Z" fill="#134e44" stroke="#0f3d36" stroke-width="1.5" />
          <!-- White card with yellow edge inside pocket -->
          <rect x="4" y="-8" width="14" height="10" rx="2" fill="#ffffff" stroke="#f59e0b" stroke-width="1.5" />
        </g>

        <!-- Arms & Gestures: Clenched Fists (Angry) vs Thumbs-Up (Happy) -->
        <g v-if="!isCharacterHappy" class="hands-angry">
          <path d="M 314 370 Q 272 385 288 430" fill="none" stroke="#175d52" stroke-width="18" stroke-linecap="round" />
          <circle cx="288" cy="430" r="14" fill="#fbcfe8" />
          <line x1="281" y1="424" x2="295" y2="424" stroke="#d97706" stroke-width="2.5" />
          
          <path d="M 406 370 Q 448 385 432 430" fill="none" stroke="#175d52" stroke-width="18" stroke-linecap="round" />
          <circle cx="432" cy="430" r="14" fill="#fbcfe8" />
          <line x1="425" y1="424" x2="439" y2="424" stroke="#d97706" stroke-width="2.5" />
        </g>
        <g v-else class="hands-happy">
          <path d="M 314 370 Q 295 435 328 465" fill="none" stroke="#175d52" stroke-width="18" stroke-linecap="round" />
          <circle cx="328" cy="465" r="12" fill="#fbcfe8" />
          <path d="M 406 370 Q 460 370 485 360" fill="none" stroke="#175d52" stroke-width="18" stroke-linecap="round" />
          <circle cx="488" cy="358" r="13" fill="#fbcfe8" />
          <text x="498" y="360" font-size="26">👍</text>
        </g>

        <!-- Neck & Head -->
        <rect x="350" y="325" width="20" height="30" fill="#fbcfe8" />
        <circle cx="360" cy="285" r="44" fill="#fbcfe8" />
        <ellipse cx="360" cy="255" rx="52" ry="28" fill="#cbd5e1" />
        <circle cx="318" cy="270" r="20" fill="#cbd5e1" />
        <circle cx="402" cy="270" r="20" fill="#cbd5e1" />
        <circle cx="360" cy="242" r="22" fill="#cbd5e1" />

        <!-- Glasses -->
        <circle cx="346" cy="285" r="14" fill="none" stroke="#475569" stroke-width="3.5" />
        <circle cx="374" cy="285" r="14" fill="none" stroke="#475569" stroke-width="3.5" />
        <line x1="360" y1="285" x2="360" y2="285" stroke="#475569" stroke-width="3.5" />

        <!-- Expression: ANGRY & UNHAPPY vs JOYFUL & RELIEVED -->
        <g v-if="!isCharacterHappy" class="face-angry">
          <!-- Steeply angled angry eyebrows \ / -->
          <path d="M 333 262 L 355 274" stroke="#991b1b" stroke-width="5" stroke-linecap="round" />
          <path d="M 387 262 L 365 274" stroke="#991b1b" stroke-width="5" stroke-linecap="round" />
          <!-- Furrowed brow wrinkle lines -->
          <line x1="358" y1="266" x2="358" y2="274" stroke="#b91c1c" stroke-width="2" />
          <line x1="362" y1="266" x2="362" y2="274" stroke="#b91c1c" stroke-width="2" />

          <!-- Tense frustrated squint eyes -->
          <path d="M 338 284 L 354 286" stroke="#0f172a" stroke-width="4" stroke-linecap="round" />
          <path d="M 382 284 L 366 286" stroke="#0f172a" stroke-width="4" stroke-linecap="round" />
          <circle cx="346" cy="287" r="3" fill="#dc2626" />
          <circle cx="374" cy="287" r="3" fill="#dc2626" />

          <!-- Angry clenched frown -->
          <path d="M 346 316 Q 360 304 374 316" fill="none" stroke="#991b1b" stroke-width="4.5" stroke-linecap="round" />
          <line x1="353" y1="312" x2="353" y2="318" stroke="#991b1b" stroke-width="2" />
          <line x1="360" y1="310" x2="360" y2="317" stroke="#991b1b" stroke-width="2" />
          <line x1="367" y1="312" x2="367" y2="318" stroke="#991b1b" stroke-width="2" />

          <!-- Flushed anger cheeks -->
          <circle cx="331" cy="298" r="9" fill="#ef4444" opacity="0.6" />
          <circle cx="389" cy="298" r="9" fill="#ef4444" opacity="0.6" />

          <!-- Sweat drop & anime anger vein 💢 -->
          <path d="M 314 274 Q 308 288 314 298 Q 320 298 320 288 Z" fill="#38bdf8" class="sweat-drop" />
          <g transform="translate(390, 230)" class="anger-vein-pulse">
            <text x="0" y="0" font-size="26">💢</text>
          </g>
        </g>
        <g v-else class="face-joyful">
          <path d="M 338 288 Q 346 279 354 288" fill="none" stroke="#0f172a" stroke-width="4.5" stroke-linecap="round" />
          <path d="M 366 288 Q 374 279 382 288" fill="none" stroke="#0f172a" stroke-width="4.5" stroke-linecap="round" />
          <path d="M 336 266 Q 346 262 356 266" fill="none" stroke="#64748b" stroke-width="3" />
          <path d="M 364 266 Q 374 262 384 266" fill="none" stroke="#64748b" stroke-width="3" />
          <circle cx="333" cy="298" r="8" fill="#f43f5e" opacity="0.45" />
          <circle cx="387" cy="298" r="8" fill="#f43f5e" opacity="0.45" />
          <path d="M 347 305 Q 360 324 373 305 Z" fill="#b91c1c" />
          <path d="M 347 305 Q 360 324 373 305" fill="none" stroke="#1e293b" stroke-width="3" stroke-linecap="round" />
        </g>

        <!-- Overhead Mood: ANGRY & OVERWHELMED vs HAPPY & CALM -->
        <g v-if="!isCharacterHappy" class="overhead-chaos">
          <!-- Storm cloud with lightning -->
          <path d="M 332 178 Q 320 162 338 154 Q 355 142 372 156 Q 390 150 398 168 Q 405 184 385 192 Q 332 196 332 178 Z" fill="#334155" opacity="0.95" />
          <path d="M 362 192 L 354 208 L 366 206 L 358 224" fill="none" stroke="#f59e0b" stroke-width="3" stroke-linecap="round" class="lightning-flash" />
          
          <text x="300" y="210" font-size="28" class="float-q1">❓</text>
          <text x="395" y="200" font-size="28" class="float-q2">❓</text>
          <text x="282" y="238" font-size="20">💨</text>
          <text x="415" y="238" font-size="20">💨</text>

        </g>
        <g v-else class="overhead-zen">
          <text x="295" y="200" font-size="32" class="sparkle-1">✨</text>
          <text x="405" y="210" font-size="32" class="sparkle-2">✨</text>
          <text x="350" y="180" font-size="36" class="lightbulb-glow">💡</text>
          <text x="385" y="170" font-size="28" class="heart-pulse">💚</text>
          <circle cx="360" cy="285" r="75" fill="none" stroke="#10b981" stroke-width="2.5" opacity="0.45" class="zen-halo" />
        </g>
      </g>
    </svg>

    <!-- Floating HUD controls within the 65% Animation Column -->
    <div class="hud-top-bar">
      <!-- Left: Cognitive Load Gauge -->
      <div class="hud-left-group">
        <div 
          class="hud-cognitive-gauge"
          :class="{
            'load-critical': cognitiveLoad > 60,
            'load-moderate': cognitiveLoad >= 30 && cognitiveLoad <= 60,
            'load-optimal': cognitiveLoad < 30
          }"
        >
          <span class="hud-brain-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
              <path d="M12 2C9.5 2 7.4 3.6 6.7 5.8C5.1 6.2 3.8 7.5 3.3 9.2C2.5 11 2.9 13.1 4.2 14.5C3.8 15.6 3.9 16.9 4.6 17.9C5.4 19.1 6.8 19.8 8.2 19.8H12V22H13V19.8H15.8C17.2 19.8 18.6 19.1 19.4 17.9C20.1 16.9 20.2 15.6 19.8 14.5C21.1 13.1 21.5 11 20.7 9.2C20.2 7.5 18.9 6.2 17.3 5.8C16.6 3.6 14.5 2 12 2ZM11 4C12.8 4 14.3 5.2 14.8 6.9C14.1 7.2 13.6 7.8 13.3 8.5C12.9 8.2 12.5 8 12 8C11 8 10 9 10 10C9 10 8 11 8 12C7.4 12 7 12.4 7 13C6.4 13 6 13.4 6 14C5.2 13.2 4.9 11.9 5.3 10.8C5.6 9.8 6.5 9 7.6 8.8C7.9 8.7 8.2 8.5 8.3 8.2C8.6 7.4 9.2 6.7 10 6.3V4.1C10.3 4 10.7 4 11 4Z"/>
            </svg>
          </span>
          <div class="hud-track">
            <div class="hud-fill" :style="{ width: `${cognitiveLoad}%` }"></div>
          </div>
          <span class="hud-load-icon">{{ cognitiveLoad > 60 ? '⚡' : cognitiveLoad > 25 ? '💡' : '🌿' }}</span>
          <span class="hud-percent">{{ cognitiveLoad }}%</span>
        </div>
      </div>

    </div>

    <!-- Bottom Floating Tools Strip within 65% area -->
    <footer class="hud-bottom-bar">
      <div class="hud-tools-strip">
        <!-- Scene 1 Tools -->
        <template v-if="currentScene === 'indoor'">
          <button type="button" class="hud-tool-chip" @click="triggerCameraScan" title="Scan Room Photo">
            <span>📸 Scan Room</span>
          </button>
          <button type="button" class="hud-tool-chip" :class="{ active: toiletContrastOn }" @click="toiletContrastOn = !toiletContrastOn" title="Toilet Contrast Seat">
            <span>🎨 Contrast Seat</span>
            <span class="chip-status">{{ toiletContrastOn ? '✓' : '+' }}</span>
          </button>
          <button type="button" class="hud-tool-chip" :class="{ active: rugRemoved }" @click="rugRemoved = !rugRemoved" title="Remove Floor Abyss Rug">
            <span>🚫🕳️ Safe Floor</span>
            <span class="chip-status">{{ rugRemoved ? '✓' : '+' }}</span>
          </button>
        </template>

        <!-- Scene 2 Tools -->
        <template v-else-if="currentScene === 'checklist'">
          <button type="button" class="hud-tool-chip" :class="{ active: checkKeys }" @click="checkKeys = !checkKeys">
            <span>🔑 Keys</span>
            <span class="chip-status">{{ checkKeys ? '✓' : '+' }}</span>
          </button>
          <button type="button" class="hud-tool-chip" :class="{ active: checkCard }" @click="checkCard = !checkCard">
            <span>💳 Card</span>
            <span class="chip-status">{{ checkCard ? '✓' : '+' }}</span>
          </button>
          <button type="button" class="hud-tool-chip" :class="{ active: pocketCardCompiled }" @click="pocketCardCompiled = !pocketCardCompiled">
            <span>📇 Pocket Card</span>
            <span class="chip-status">{{ pocketCardCompiled ? '✓' : '+' }}</span>
          </button>
        </template>

        <!-- Scene 3 Tools -->
        <template v-else>
          <button type="button" class="hud-tool-chip" :class="{ active: canopyActive }" @click="canopyActive = !canopyActive">
            <span>🌳 Tree Canopy</span>
            <span class="chip-status">{{ canopyActive ? '✓' : '+' }}</span>
          </button>
          <button type="button" class="hud-tool-chip" :class="{ active: benchPresent }" @click="benchPresent = !benchPresent">
            <span>🪑 Rest Benches</span>
            <span class="chip-status">{{ benchPresent ? '✓' : '+' }}</span>
          </button>
          <button type="button" class="hud-tool-chip" :class="{ active: straightPathActive }" @click="straightPathActive = !straightPathActive">
            <span>🛣️ Straight Path</span>
            <span class="chip-status">{{ straightPathActive ? '✓' : '+' }}</span>
          </button>
        </template>
      </div>
    </footer>
  </div> <!-- end .animation-column (65%) -->

  <!-- RIGHT 35%: MINIMALISTIC STORY PANEL -->
  <aside class="story-column" aria-label="About NeighbourlyMinds">
    <div class="story-minimal-card">
      <div class="story-header">
        <h2 class="story-heading">How Everyday Adjustments Help</h2>
      </div>

      <!-- Typewriter Text in Few Simple Words -->
      <div class="story-typewriter-text" aria-live="polite">
        <p v-for="(line, idx) in displayedLines" :key="idx" class="story-line">
          {{ line }}
          <span v-if="isTyping && idx === displayedLines.length - 1" class="typing-cursor" aria-hidden="true">|</span>
        </p>
        <p v-if="displayedLines.length === 0 && isTyping" class="story-line">
          <span class="typing-cursor" aria-hidden="true">|</span>
        </p>
      </div>

      <!-- Subtle replay link if finished -->
      <div v-if="!isTyping" class="story-replay-wrap">
        <button type="button" class="story-replay-btn" @click="startTypewriter">
          ↺ Replay text
        </button>
      </div>
    </div>
  </aside>
</div> <!-- end .intro-split-layout -->
</template>

<style scoped>
/* Split Layout (65% Horizontal SVG, 35% Story Panel) */
.intro-split-layout {
  position: relative;
  width: 100%;
  height: 620px;
  overflow: hidden;
  background: #f8fafc;
  display: flex;
  flex-direction: row;
  border-top: 1px solid var(--border-color, #d1ddd7);
  border-bottom: 1px solid var(--border-color, #d1ddd7);
}

/* 65% Width SVG Animation Column */
.animation-column {
  flex: 0 0 65%;
  width: 65%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background: #eef2f6;
  border-right: 1px solid var(--border-color, #d1ddd7);
  display: flex;
  flex-direction: column;
}

.stage-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  z-index: 1;
}

/* 35% Width Story Panel */
.story-column {
  flex: 0 0 35%;
  width: 35%;
  height: 100%;
  overflow-y: auto;
  background: #ffffff;
  padding: 3rem 2.25rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  box-sizing: border-box;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.05);
  scrollbar-width: thin;
}

.story-minimal-card {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
  max-width: 440px;
  width: 100%;
  margin: 0 auto;
}

.story-header {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}


.story-heading {
  margin: 0;
  font-size: 1.85rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.25;
  letter-spacing: -0.5px;
}

/* Typewriter Story Text */
.story-typewriter-text {
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
  min-height: 120px;
}

.story-line {
  margin: 0;
  font-size: 1.12rem;
  line-height: 1.7;
  color: #334155;
  font-weight: 450;
  letter-spacing: -0.1px;
}

.typing-cursor {
  display: inline-block;
  font-weight: 700;
  color: var(--color-primary, #175d52);
  margin-left: 2px;
  animation: cursorBlink 0.8s infinite;
}

@keyframes cursorBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.story-replay-wrap {
  margin-top: -0.5rem;
}

.story-replay-btn {
  background: transparent;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 0.35rem 0.85rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.2s ease;
}

.story-replay-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #1e293b;
}

/* Responsive adjustments */
@media (max-width: 900px) {
  .intro-split-layout {
    flex-direction: column;
    height: auto;
    min-height: auto;
  }
  .animation-column {
    flex: 0 0 420px;
    width: 100%;
    height: 420px;
    border-right: none;
    border-bottom: 1px solid var(--border-color, #d1ddd7);
  }
  .story-column {
    flex: 1 1 auto;
    width: 100%;
    height: auto;
    padding: 2.25rem 1.5rem;
  }
}

.interactive-element {
  cursor: pointer;
}

.transition-smooth {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

/* --- HUD TOP BAR --- */
.hud-top-bar {
  position: relative;
  z-index: 10;
  width: 100%;
  padding: 0.85rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  pointer-events: none;
}

.hud-left-group, .hud-center-controls, .hud-right-group {
  pointer-events: auto;
}

.hud-left-group {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.hud-brand-title {
  font-size: 1.6rem;
  font-weight: 900;
  color: var(--color-primary, #175d52);
  letter-spacing: -0.5px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(16px);
  padding: 0.4rem 1rem;
  border-radius: 999px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.hud-cognitive-gauge {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 1.15rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(16px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  white-space: nowrap;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.hud-cognitive-gauge.load-critical {
  background: rgba(254, 242, 242, 0.95);
  color: #b91c1c;
  border: 1.5px solid #ef4444;
  animation: pulseCritical 1.4s infinite;
}

.hud-cognitive-gauge.load-moderate {
  background: rgba(255, 251, 235, 0.95);
  color: #b45309;
  border: 1.5px solid #f59e0b;
}

.hud-cognitive-gauge.load-optimal {
  background: rgba(236, 253, 245, 0.95);
  color: #047857;
  border: 1.5px solid #10b981;
}

.hud-track {
  width: 65px;
  height: 9px;
  background: rgba(0, 0, 0, 0.08);
  border-radius: 999px;
  overflow: hidden;
}

.hud-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.5s ease-out, background-color 0.5s ease;
}

.load-critical .hud-fill { background-color: #ef4444; }
.load-moderate .hud-fill { background-color: #f59e0b; }
.load-optimal .hud-fill { background-color: #10b981; }

.hud-percent {
  font-size: 0.92rem;
  font-weight: 800;
  font-family: inherit;
  white-space: nowrap;
}

/* Center Scene Tabs */
.hud-center-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(16px);
  padding: 4px 8px;
  border-radius: 999px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.hud-stages-pill {
  display: flex;
  align-items: center;
  gap: 4px;
}

.scene-tab-btn {
  background: transparent;
  border: none;
  border-radius: 999px;
  padding: 0.4rem 0.85rem;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: #475569;
  transition: all 0.2s ease;
}

.scene-tab-btn:hover {
  background: rgba(23, 93, 82, 0.08);
  color: #175d52;
}

.scene-tab-btn.active {
  background: white;
  color: #175d52;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.hud-playback-buttons {
  display: flex;
  align-items: center;
  gap: 3px;
  border-left: 1px solid #e2e8f0;
  padding-left: 5px;
}

.hud-icon-btn {
  background: transparent;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  cursor: pointer;
  color: #334155;
  transition: all 0.2s ease;
}

.hud-icon-btn:hover {
  background: var(--color-primary, #175d52);
  color: white;
}

/* Right Button */
.hud-enter-home-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.75rem 1.65rem;
  border-radius: 999px;
  background: var(--color-primary, #175d52);
  color: white;
  border: none;
  font-size: 1.05rem;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 6px 20px rgba(23, 93, 82, 0.28);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.hud-enter-home-btn:hover {
  background: #124b42;
  transform: translateY(-2px) scale(1.03);
  box-shadow: 0 8px 24px rgba(23, 93, 82, 0.38);
}

/* FLOATING WELCOME MESSAGE (USER REQUESTED) */
.hud-welcome-message {
  position: absolute;
  top: 4.5rem;
  left: 2rem;
  z-index: 20;
  max-width: 440px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 18px;
  padding: 1rem 1.25rem;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(23, 93, 82, 0.06);
  border: 1.5px solid rgba(255, 255, 255, 0.85);
  animation: welcomeSlideIn 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  pointer-events: auto;
}

.welcome-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
}

.welcome-tag {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.welcome-wave-icon {
  font-size: 1.35rem;
  display: inline-block;
  animation: waveAnimation 2s infinite ease-in-out;
  transform-origin: 70% 70%;
}

.welcome-main-text {
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--color-primary, #175d52);
  letter-spacing: -0.3px;
}

.welcome-close-btn {
  background: transparent;
  border: none;
  font-size: 0.9rem;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  cursor: pointer;
  color: #94a3b8;
  transition: all 0.2s ease;
}

.welcome-close-btn:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.welcome-desc {
  font-size: 0.88rem;
  color: var(--color-text-muted, #475569);
  line-height: 1.5;
  margin: 0;
}

/* HUD BOTTOM BAR */
.hud-bottom-bar {
  position: absolute;
  bottom: 1.5rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.25rem;
  pointer-events: auto;
  max-width: 95vw;
}

.hud-tools-strip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(16px);
  padding: 6px 12px;
  border-radius: 999px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.1);
}

.hud-tool-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.85rem;
  background: #f1f5f9;
  border: 1.5px solid #cbd5e1;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.95rem;
  font-weight: 700;
  color: #334155;
}

.hud-tool-chip:hover {
  background: #e2e8f0;
  transform: translateY(-1px);
}

.hud-tool-chip.active {
  background: #ecfdf5;
  border-color: #10b981;
  color: #047857;
}

.chip-status {
  font-size: 0.75rem;
  font-weight: 800;
  padding: 1px 4px;
  border-radius: 4px;
  background: white;
}

.hud-tool-chip.active .chip-status {
  background: #10b981;
  color: white;
}

.hud-large-home-btn {
  display: none;
  align-items: center;
  padding: 0.7rem 1.25rem;
  border-radius: 999px;
  background: var(--color-primary, #175d52);
  color: white;
  border: none;
  font-size: 0.95rem;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(23, 93, 82, 0.3);
}

/* Animations */
@keyframes waveAnimation {
  0%, 100% { transform: rotate(0deg); }
  20%, 60% { transform: rotate(14deg); }
  40%, 80% { transform: rotate(-14deg); }
}

@keyframes welcomeSlideIn {
  from { opacity: 0; transform: translateY(-12px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.welcome-fade-enter-active, .welcome-fade-leave-active {
  transition: all 0.3s ease;
}
.welcome-fade-enter-from, .welcome-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@keyframes pulseCritical {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.03); }
}

.laser-scanner {
  animation: scanSweep 2s ease-in-out infinite alternate;
}

@keyframes scanSweep {
  0% { transform: translateY(0); opacity: 0.8; }
  100% { transform: translateY(340px); opacity: 0.9; }
}

.safe-path-dash {
  animation: dashFollow 2s linear infinite;
}

@keyframes dashFollow {
  from { stroke-dashoffset: 40; }
  to { stroke-dashoffset: 0; }
}

.vortex-spinning {
  animation: spinHole 4s infinite linear;
  transform-origin: 620px 580px;
}

@keyframes spinHole {
  0% { transform: scale(0.96) rotate(0deg); }
  50% { transform: scale(1.04) rotate(180deg); }
  100% { transform: scale(0.96) rotate(360deg); }
}

.seat-glow-ring {
  animation: glowSpin 6s linear infinite;
  transform-origin: 832px 362px;
}

@keyframes glowSpin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.float-q1 { animation: floatQ 2s infinite ease-in-out; }
.float-q2 { animation: floatQ 2s 0.3s infinite ease-in-out; }
.float-q3 { animation: floatQ 2s 0.6s infinite ease-in-out; }

@keyframes floatQ {
  0%, 100% { transform: translateY(0); opacity: 0.8; }
  50% { transform: translateY(-10px); opacity: 1; }
}

.sweat-drop {
  animation: dripFall 1.5s infinite ease-in;
}

@keyframes dripFall {
  0% { transform: translateY(0); opacity: 0; }
  30% { opacity: 1; }
  100% { transform: translateY(14px); opacity: 0; }
}

.scribble-vibration {
  animation: vibrate 0.35s infinite alternate;
}

@keyframes vibrate {
  0% { transform: translate(-1.5px, -1.5px); }
  100% { transform: translate(1.5px, 1.5px); }
}

.sparkle-1 { animation: sparkle 1.8s infinite ease-in-out; }
.sparkle-2 { animation: sparkle 1.8s 0.5s infinite ease-in-out; }
.lightbulb-glow { animation: bulb 2s infinite alternate ease-in-out; }
.heart-pulse { animation: heart 1.4s infinite ease-in-out; }

@keyframes sparkle {
  0%, 100% { transform: scale(0.9) rotate(-10deg); opacity: 0.7; }
  50% { transform: scale(1.2) rotate(10deg); opacity: 1; }
}

@keyframes bulb {
  0% { transform: translateY(0); opacity: 0.8; }
  100% { transform: translateY(-6px); opacity: 1; filter: drop-shadow(0 0 6px #f59e0b); }
}

@keyframes heart {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.28); }
}

.zen-halo {
  animation: haloPulse 3s infinite ease-out;
  transform-origin: 360px 285px;
}

@keyframes haloPulse {
  0% { transform: scale(0.9); opacity: 0.6; }
  100% { transform: scale(1.25); opacity: 0; }
}

/* Angry & Frustrated Reactions Animations */
.hands-angry {
  animation: shakeFists 0.3s infinite alternate ease-in-out;
  transform-origin: 360px 400px;
}

@keyframes shakeFists {
  0% { transform: translateY(0) rotate(-1.5deg); }
  100% { transform: translateY(-4px) rotate(1.5deg); }
}

.anger-vein-pulse {
  animation: angerPulse 0.5s infinite alternate ease-in-out;
  transform-origin: 390px 230px;
}

@keyframes angerPulse {
  0% { transform: scale(0.85); }
  100% { transform: scale(1.25); }
}

.lightning-flash {
  animation: flashLightning 0.8s infinite ease-in-out;
}

@keyframes flashLightning {
  0%, 100% { opacity: 0.2; }
  50% { opacity: 1; filter: drop-shadow(0 0 8px #f59e0b); }
}

.mood-badge-angry {
  animation: floatBadgeAngry 1.2s infinite alternate ease-in-out;
}

@keyframes floatBadgeAngry {
  0% { transform: translateY(0); }
  100% { transform: translateY(-5px); }
}

.mood-badge-happy {
  animation: floatBadgeHappy 2s infinite alternate ease-in-out;
}

@keyframes floatBadgeHappy {
  0% { transform: translateY(0); }
  100% { transform: translateY(-4px); }
}

@media (max-width: 900px) {
  .hud-top-bar {
    padding: 0.75rem 1rem;
    flex-wrap: wrap;
  }
  .hud-welcome-message {
    left: 1rem;
    right: 1rem;
    max-width: none;
    top: 4.5rem;
  }
  .hud-bottom-bar {
    bottom: 0.75rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
}

@media (max-width: 640px) {
  .tab-label {
    display: none;
  }
  .hud-large-home-btn {
    display: inline-flex;
  }
}
</style>
