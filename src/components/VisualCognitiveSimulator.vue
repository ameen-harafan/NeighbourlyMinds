<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";

type Phase = 0 | 1 | 2 | 3;

const currentPhase = ref<Phase>(1); // Start at phase 1 (the barrier) or cycle through
const isPlaying = ref(true);
const autoPlayTimer = ref<number | null>(null);

// Direct Interactive Fix Toggles (allows the user to click tools directly)
const toiletContrastOn = ref(false);
const rugRemoved = ref(false);
const grabBarContrastOn = ref(false);
const glareReduced = ref(false);

// Drag comparison slider position (0 to 100)
const sliderMode = ref(false);
const sliderPosition = ref(50); // 0 = 100% barrier, 100 = 100% solved

// Phase timings in milliseconds
const PHASE_DURATIONS: Record<Phase, number> = {
  0: 3200, // Normal sight
  1: 4200, // Dementia barrier & confusion
  2: 3800, // App fixing items
  3: 4500, // Joyful, solved, low load
};

// Cognitive load computed based on phase and manual fixes
const cognitiveLoad = computed(() => {
  if (sliderMode.value) {
    // Slider 0 -> 95% load, Slider 100 -> 15% load
    return Math.round(95 - (sliderPosition.value / 100) * 80);
  }

  if (currentPhase.value === 0) return 25;
  if (currentPhase.value === 1) {
    // Deduct load for each manual fix applied
    let load = 95;
    if (toiletContrastOn.value) load -= 28;
    if (rugRemoved.value) load -= 30;
    if (grabBarContrastOn.value) load -= 22;
    return Math.max(15, load);
  }
  if (currentPhase.value === 2) return 50;
  // Phase 3: Solved
  return 15;
});

// Visual state helper computed properties
const isHighContrastSeat = computed(() => {
  if (sliderMode.value) return sliderPosition.value > 40;
  return (
    currentPhase.value === 2 ||
    currentPhase.value === 3 ||
    toiletContrastOn.value
  );
});

const isDarkHoleRugActive = computed(() => {
  if (sliderMode.value) return sliderPosition.value < 60;
  if (currentPhase.value === 0) return false; // Normal mat
  if (currentPhase.value === 2 || currentPhase.value === 3) return false; // Fixed
  return !rugRemoved.value; // Active in barrier phase unless removed
});

const isRugPresentAtAll = computed(() => {
  if (sliderMode.value) return sliderPosition.value < 70;
  if (currentPhase.value === 0) return true;
  if (currentPhase.value === 1) return !rugRemoved.value;
  return false;
});

const isHighContrastBar = computed(() => {
  if (sliderMode.value) return sliderPosition.value > 50;
  return (
    currentPhase.value === 2 ||
    currentPhase.value === 3 ||
    grabBarContrastOn.value
  );
});

const isLowContrastWall = computed(() => {
  if (sliderMode.value) return sliderPosition.value < 45;
  return currentPhase.value === 1 && !toiletContrastOn.value;
});

const isGlareActive = computed(() => {
  if (sliderMode.value) return sliderPosition.value < 50;
  return currentPhase.value === 1 && !glareReduced.value;
});

// Character mood: 'normal' | 'stressed' | 'surprised' | 'happy'
const characterMood = computed(() => {
  if (sliderMode.value) {
    if (sliderPosition.value < 35) return "stressed";
    if (sliderPosition.value < 70) return "surprised";
    return "happy";
  }
  if (currentPhase.value === 0) return "normal";
  if (currentPhase.value === 1) {
    return cognitiveLoad.value > 45 ? "stressed" : "happy";
  }
  if (currentPhase.value === 2) return "surprised";
  return "happy";
});

// Auto-play loop
const scheduleNextPhase = () => {
  if (!isPlaying.value) return;
  if (autoPlayTimer.value) clearTimeout(autoPlayTimer.value);

  const currentDuration = PHASE_DURATIONS[currentPhase.value];
  autoPlayTimer.value = window.setTimeout(() => {
    if (!isPlaying.value) return;
    const nextPhase = ((currentPhase.value + 1) % 4) as Phase;
    setPhase(nextPhase, false);
    scheduleNextPhase();
  }, currentDuration);
};

const setPhase = (phase: Phase, manualClick = true) => {
  currentPhase.value = phase;
  sliderMode.value = false;

  // Reset or configure manual toggles according to phase
  if (phase === 0) {
    toiletContrastOn.value = false;
    rugRemoved.value = false;
    grabBarContrastOn.value = false;
    glareReduced.value = false;
  } else if (phase === 1) {
    toiletContrastOn.value = false;
    rugRemoved.value = false;
    grabBarContrastOn.value = false;
    glareReduced.value = false;
  } else if (phase === 2 || phase === 3) {
    toiletContrastOn.value = true;
    rugRemoved.value = true;
    grabBarContrastOn.value = true;
    glareReduced.value = true;
  }

  if (manualClick) {
    // If user explicitly clicked a phase, pause auto-play for 8 seconds
    if (autoPlayTimer.value) clearTimeout(autoPlayTimer.value);
    scheduleNextPhase();
  }
};

const togglePlayPause = () => {
  isPlaying.value = !isPlaying.value;
  if (isPlaying.value) {
    scheduleNextPhase();
  } else if (autoPlayTimer.value) {
    clearTimeout(autoPlayTimer.value);
  }
};

const toggleToiletFix = () => {
  toiletContrastOn.value = !toiletContrastOn.value;
  sliderMode.value = false;
};

const toggleRugFix = () => {
  rugRemoved.value = !rugRemoved.value;
  sliderMode.value = false;
};

const toggleBarFix = () => {
  grabBarContrastOn.value = !grabBarContrastOn.value;
  sliderMode.value = false;
};

const restartStory = () => {
  isPlaying.value = true;
  setPhase(0, true);
};

onMounted(() => {
  // Start directly on phase 1 (the barrier) so visitor immediately sees the concept, then cycles
  currentPhase.value = 1;
  scheduleNextPhase();
});

onUnmounted(() => {
  if (autoPlayTimer.value) clearTimeout(autoPlayTimer.value);
});
</script>

<template>
  <div
    class="visual-story-card"
    role="region"
    aria-label="Visual demonstration of dementia perception and environmental adjustments"
  >
    <!-- Top HUD: Pure Visual Cognitive Load Meter & Stage Navigation -->
    <header class="story-hud">
      <!-- Cognitive Load Gauge (Universal Visual Brain + Meter) -->
      <div
        class="cognitive-gauge-badge"
        :class="{
          'load-critical': cognitiveLoad > 70,
          'load-moderate': cognitiveLoad >= 40 && cognitiveLoad <= 70,
          'load-optimal': cognitiveLoad < 40,
        }"
        aria-live="polite"
      >
        <span class="brain-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
            <path
              d="M12 2C9.5 2 7.4 3.6 6.7 5.8C5.1 6.2 3.8 7.5 3.3 9.2C2.5 11 2.9 13.1 4.2 14.5C3.8 15.6 3.9 16.9 4.6 17.9C5.4 19.1 6.8 19.8 8.2 19.8H12V22H13V19.8H15.8C17.2 19.8 18.6 19.1 19.4 17.9C20.1 16.9 20.2 15.6 19.8 14.5C21.1 13.1 21.5 11 20.7 9.2C20.2 7.5 18.9 6.2 17.3 5.8C16.6 3.6 14.5 2 12 2ZM11 4C12.8 4 14.3 5.2 14.8 6.9C14.1 7.2 13.6 7.8 13.3 8.5C12.9 8.2 12.5 8 12 8C11 8 10 9 10 10C9 10 8 11 8 12C7.4 12 7 12.4 7 13C6.4 13 6 13.4 6 14C5.2 13.2 4.9 11.9 5.3 10.8C5.6 9.8 6.5 9 7.6 8.8C7.9 8.7 8.2 8.5 8.3 8.2C8.6 7.4 9.2 6.7 10 6.3V4.1C10.3 4 10.7 4 11 4Z"
            />
          </svg>
        </span>
        <div class="meter-track">
          <div class="meter-fill" :style="{ width: `${cognitiveLoad}%` }"></div>
        </div>
        <span class="load-icon" aria-hidden="true">
          {{ cognitiveLoad > 70 ? "⚡" : cognitiveLoad > 35 ? "💡" : "🌿" }}
        </span>
        <span class="load-percent">{{ cognitiveLoad }}%</span>
      </div>

      <!-- Pure Visual Stage Switcher (4 iconic phases) -->
      <div class="stage-nav" role="tablist">
        <button
          type="button"
          class="stage-btn"
          :class="{ active: currentPhase === 0 && !sliderMode }"
          @click="setPhase(0)"
          aria-label="Standard View"
          title="Standard View"
        >
          <span class="btn-icon">👁️</span>
        </button>
        <button
          type="button"
          class="stage-btn"
          :class="{ active: currentPhase === 1 && !sliderMode }"
          @click="setPhase(1)"
          aria-label="Dementia Perception & Cognitive Barrier"
          title="Dementia Barrier"
        >
          <span class="btn-icon">🌫️❓</span>
        </button>
        <button
          type="button"
          class="stage-btn"
          :class="{ active: currentPhase === 2 && !sliderMode }"
          @click="setPhase(2)"
          aria-label="App Adjustment in Action"
          title="App Adjustment"
        >
          <span class="btn-icon">🪄🎨</span>
        </button>
        <button
          type="button"
          class="stage-btn"
          :class="{ active: currentPhase === 3 && !sliderMode }"
          @click="setPhase(3)"
          aria-label="Reduced Cognitive Load and Joy"
          title="Independence & Joy"
        >
          <span class="btn-icon">😊✨</span>
        </button>
      </div>

      <!-- Playback Controls -->
      <div class="playback-controls">
        <button
          type="button"
          class="icon-control-btn"
          @click="togglePlayPause"
          :aria-label="
            isPlaying ? 'Pause animation loop' : 'Play animation loop'
          "
          :title="isPlaying ? 'Pause' : 'Play'"
        >
          {{ isPlaying ? "⏸" : "▶" }}
        </button>
        <button
          type="button"
          class="icon-control-btn"
          @click="restartStory"
          aria-label="Replay visual story from start"
          title="Replay"
        >
          ↺
        </button>
      </div>
    </header>

    <!-- Main SVG Animation Stage -->
    <div class="svg-stage-container">
      <svg
        class="story-svg"
        viewBox="0 0 600 440"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Animated illustration of room contrast and senior character"
      >
        <defs>
          <!-- Soft Drop Shadow -->
          <filter
            id="story-shadow"
            x="-20%"
            y="-20%"
            width="140%"
            height="140%"
          >
            <feDropShadow
              dx="0"
              dy="6"
              stdDeviation="8"
              flood-opacity="0.12"
              flood-color="#0f172a"
            />
          </filter>

          <!-- Contrast Glow -->
          <filter id="gold-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <!-- Black Hole Abyss Vortex Gradient -->
          <radialGradient id="black-hole-gradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#000000" stop-opacity="1" />
            <stop offset="60%" stop-color="#111827" stop-opacity="0.95" />
            <stop offset="85%" stop-color="#374151" stop-opacity="0.8" />
            <stop offset="100%" stop-color="#4b5563" stop-opacity="0" />
          </radialGradient>

          <!-- Soft Floor Glare Gradient -->
          <radialGradient id="glare-gradient" cx="50%" cy="40%" r="50%">
            <stop offset="0%" stop-color="#ffffff" stop-opacity="0.65" />
            <stop offset="50%" stop-color="#ffffff" stop-opacity="0.2" />
            <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
          </radialGradient>

          <!-- High-Contrast Path Guide Gradient -->
          <linearGradient
            id="safe-path-gradient"
            x1="0%"
            y1="0%"
            x2="100%"
            y2="0%"
          >
            <stop offset="0%" stop-color="#175d52" stop-opacity="0.1" />
            <stop offset="50%" stop-color="#175d52" stop-opacity="0.35" />
            <stop offset="100%" stop-color="#175d52" stop-opacity="0.6" />
          </linearGradient>

          <!-- Wall Tile Pattern -->
          <pattern
            id="wall-tiles"
            width="40"
            height="40"
            patternUnits="userSpaceOnUse"
          >
            <rect width="40" height="40" fill="#f8fafc" />
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              :stroke="isLowContrastWall ? '#f1f5f9' : '#e2e8f0'"
              stroke-width="1.2"
            />
          </pattern>
        </defs>

        <!-- 1. Background Wall & Tiles -->
        <rect x="0" y="0" width="600" height="300" fill="url(#wall-tiles)" />

        <!-- 2. Floor Area -->
        <rect
          x="0"
          y="300"
          width="600"
          height="140"
          :fill="isLowContrastWall ? '#f1f5f9' : '#e8edea'"
          class="floor-base"
        />

        <!-- Baseboard / Skirting Board: High Contrast vs Blended -->
        <rect
          x="0"
          y="294"
          width="600"
          height="8"
          :fill="isLowContrastWall ? '#e2e8f0' : '#175d52'"
          :opacity="isLowContrastWall ? 0.35 : 0.9"
          class="transition-all"
        />

        <!-- Disorienting Glare on Floor (Dementia Barrier) -->
        <ellipse
          v-if="isGlareActive"
          cx="330"
          cy="340"
          rx="110"
          ry="30"
          fill="url(#glare-gradient)"
          class="glare-pulse"
        />

        <!-- Safe High-Contrast Directional Line (After Fix) -->
        <path
          v-if="!isDarkHoleRugActive && currentPhase >= 2"
          d="M 230 380 Q 330 365 420 355"
          fill="none"
          stroke="#175d52"
          stroke-width="5"
          stroke-dasharray="8 6"
          class="safe-guide-path"
        />

        <!-- 3. Confusing Dark Rug vs Terrifying Floor Abyss (The Dementia Hole Illusion) -->
        <g
          v-if="isRugPresentAtAll"
          class="interactive-hotspot rug-group"
          @click="toggleRugFix"
          role="button"
          tabindex="0"
          aria-label="Click to remove deceptive floor barrier"
        >
          <!-- Normal View: Just a dark mat -->
          <ellipse
            v-if="!isDarkHoleRugActive"
            cx="330"
            cy="370"
            rx="65"
            ry="24"
            fill="#334155"
            stroke="#1e293b"
            stroke-width="2"
          />

          <!-- Dementia Perception: Looks like a bottomless void / black hole! -->
          <g v-else class="black-hole-illusion">
            <!-- Pulsing Void Vortex -->
            <ellipse
              cx="330"
              cy="370"
              rx="80"
              ry="32"
              fill="url(#black-hole-gradient)"
              class="hole-vortex"
            />
            <ellipse cx="330" cy="370" rx="60" ry="22" fill="#000000" />
            <ellipse
              cx="330"
              cy="370"
              rx="42"
              ry="14"
              fill="#050505"
              stroke="#dc2626"
              stroke-width="1.5"
              stroke-dasharray="4 4"
              class="hazard-border"
            />
            <!-- Visual Warning Indicator -->
            <text
              x="330"
              y="375"
              text-anchor="middle"
              font-size="16"
              fill="#ef4444"
              class="hazard-icon"
            >
              ⚠️
            </text>
            <!-- Ripple Wave -->
            <ellipse
              cx="330"
              cy="370"
              rx="90"
              ry="36"
              fill="none"
              stroke="#ef4444"
              stroke-width="1"
              opacity="0.4"
              class="hazard-ring"
            />
          </g>

          <!-- Interactive Tooltip Pulse -->
          <circle
            cx="395"
            cy="355"
            r="9"
            fill="#175d52"
            opacity="0.85"
            class="action-pulse"
          />
          <text
            x="395"
            y="359"
            text-anchor="middle"
            font-size="10"
            fill="#ffffff"
            font-weight="bold"
          >
            ✕
          </text>
        </g>

        <!-- 4. Support Rail / Grab Bar -->
        <g
          class="interactive-hotspot bar-group"
          @click="toggleBarFix"
          role="button"
          tabindex="0"
          aria-label="Click to toggle high contrast grab bar"
        >
          <!-- Wall mount brackets -->
          <rect
            x="408"
            y="160"
            width="8"
            height="12"
            rx="2"
            :fill="isHighContrastBar ? '#175d52' : '#94a3b8'"
          />
          <rect
            x="408"
            y="240"
            width="8"
            height="12"
            rx="2"
            :fill="isHighContrastBar ? '#175d52' : '#94a3b8'"
          />

          <!-- Grab Bar Shaft: Invisible/Silver vs Vibrant Amber/Teal Glow -->
          <rect
            x="410"
            y="160"
            width="8"
            height="90"
            rx="4"
            :fill="
              isHighContrastBar
                ? '#f59e0b'
                : isLowContrastWall
                  ? '#f1f5f9'
                  : '#94a3b8'
            "
            :stroke="
              isHighContrastBar
                ? '#b45309'
                : isLowContrastWall
                  ? '#e2e8f0'
                  : '#64748b'
            "
            stroke-width="2"
            :filter="isHighContrastBar ? 'url(#gold-glow)' : 'none'"
            class="transition-all"
          />

          <!-- Textured grip rings on contrast bar -->
          <g v-if="isHighContrastBar">
            <line
              x1="410"
              y1="185"
              x2="418"
              y2="185"
              stroke="#78350f"
              stroke-width="2"
            />
            <line
              x1="410"
              y1="205"
              x2="418"
              y2="205"
              stroke="#78350f"
              stroke-width="2"
            />
            <line
              x1="410"
              y1="225"
              x2="418"
              y2="225"
              stroke="#78350f"
              stroke-width="2"
            />
          </g>

          <!-- Interactive Action Badge -->
          <circle
            cx="428"
            cy="205"
            r="9"
            fill="#175d52"
            opacity="0.85"
            class="action-pulse"
          />
          <text
            x="428"
            y="209"
            text-anchor="middle"
            font-size="10"
            fill="#ffffff"
            font-weight="bold"
          >
            ⚡
          </text>
        </g>

        <!-- 5. The Toilet (White Ceramic Bowl + Camouflaged vs High-Contrast Seat) -->
        <g
          class="interactive-hotspot toilet-group"
          @click="toggleToiletFix"
          role="button"
          tabindex="0"
          aria-label="Click to toggle high contrast toilet seat"
        >
          <!-- Water Cistern Tank -->
          <rect
            x="455"
            y="140"
            width="60"
            height="110"
            rx="8"
            fill="#ffffff"
            :stroke="isLowContrastWall ? '#f1f5f9' : '#cbd5e1'"
            stroke-width="2"
            filter="url(#story-shadow)"
          />
          <!-- Cistern Lid -->
          <rect
            x="452"
            y="134"
            width="66"
            height="10"
            rx="4"
            fill="#ffffff"
            :stroke="isLowContrastWall ? '#f1f5f9' : '#cbd5e1'"
            stroke-width="2"
          />
          <!-- Flush Button -->
          <circle cx="485" cy="139" r="4" fill="#94a3b8" />

          <!-- Toilet Bowl Base -->
          <path
            d="M 458 240 Q 440 280 450 340 L 495 340 Q 515 280 500 240 Z"
            fill="#ffffff"
            :stroke="isLowContrastWall ? '#f1f5f9' : '#cbd5e1'"
            stroke-width="2"
          />
          <!-- Floor seal -->
          <ellipse cx="474" cy="340" rx="26" ry="6" fill="#e2e8f0" />

          <!-- Toilet Rim -->
          <ellipse
            cx="460"
            cy="242"
            rx="36"
            ry="20"
            fill="#ffffff"
            :stroke="isLowContrastWall ? '#f8fafc' : '#cbd5e1'"
            stroke-width="2"
          />

          <!-- THE TOILET SEAT: Invisible / Camouflaged vs High-Contrast Vivid Navy/Blue -->
          <!-- State A: Camouflaged Low Contrast (blends invisibly into white bowl) -->
          <g v-if="!isHighContrastSeat" class="seat-camouflaged">
            <ellipse
              cx="458"
              cy="240"
              rx="38"
              ry="21"
              fill="#ffffff"
              :stroke="isLowContrastWall ? '#f8fafc' : '#e2e8f0'"
              stroke-width="1"
              :opacity="isLowContrastWall ? 0.35 : 0.8"
            />
            <!-- Inside hole -->
            <ellipse
              cx="458"
              cy="240"
              rx="24"
              ry="13"
              fill="#f8fafc"
              stroke="#f1f5f9"
              stroke-width="1"
            />
            <!-- Floating Question Marks on Camouflaged Seat -->
            <g v-if="currentPhase === 1" class="float-quest">
              <text
                x="458"
                y="246"
                text-anchor="middle"
                font-size="16"
                fill="#94a3b8"
                opacity="0.8"
              >
                ❓
              </text>
            </g>
          </g>

          <!-- State B: High-Contrast Bold Seat (100% visible, >7:1 contrast ratio!) -->
          <g v-else class="seat-high-contrast" filter="url(#story-shadow)">
            <!-- Vivid Royal Blue / Deep Contrast Navy Seat -->
            <ellipse
              cx="458"
              cy="240"
              rx="39"
              ry="22"
              fill="#1d4ed8"
              stroke="#1e3a8a"
              stroke-width="3"
            />
            <!-- Inside Hole -->
            <ellipse
              cx="458"
              cy="240"
              rx="24"
              ry="13"
              fill="#ffffff"
              stroke="#172554"
              stroke-width="2"
            />
            <!-- Subtle Highlight on Edge -->
            <path
              d="M 425 240 Q 458 260 490 240"
              fill="none"
              stroke="#60a5fa"
              stroke-width="2"
              opacity="0.8"
            />

            <!-- Contrast Success Indicator Glow -->
            <circle
              cx="458"
              cy="240"
              r="42"
              fill="none"
              stroke="#38bdf8"
              stroke-width="1.5"
              stroke-dasharray="4 4"
              class="glow-ring"
            />
          </g>

          <!-- Interactive Action Badge -->
          <circle
            cx="505"
            cy="225"
            r="9"
            fill="#175d52"
            opacity="0.85"
            class="action-pulse"
          />
          <text
            x="505"
            y="229"
            text-anchor="middle"
            font-size="10"
            fill="#ffffff"
            font-weight="bold"
          >
            🎨
          </text>
        </g>

        <!-- 6. Animated Web App Tool / Magic Wand (Active in Phase 2) -->
        <g v-if="currentPhase === 2" class="magic-wand-tool">
          <path
            d="M 380 180 L 435 225"
            stroke="#f59e0b"
            stroke-width="5"
            stroke-linecap="round"
          />
          <circle
            cx="435"
            cy="225"
            r="8"
            fill="#fbbf24"
            filter="url(#gold-glow)"
          />
          <text x="445" y="215" font-size="18">✨</text>
          <text x="365" y="175" font-size="18">🎨</text>
        </g>

        <!-- 7. The Expressive Character (Older Adult) -->
        <g
          class="character-figure transition-all"
          :transform="
            characterMood === 'happy' ? 'translate(60, 0)' : 'translate(0, 0)'
          "
        >
          <!-- Shadow Under Person -->
          <ellipse
            cx="180"
            cy="395"
            rx="36"
            ry="10"
            fill="#94a3b8"
            opacity="0.3"
          />

          <!-- Body / Clothes (Sage Green Cardigan & Navy Pants) -->
          <!-- Legs / Shoes -->
          <rect x="162" y="325" width="14" height="65" rx="7" fill="#1e293b" />
          <rect x="184" y="325" width="14" height="65" rx="7" fill="#1e293b" />
          <!-- Shoes -->
          <ellipse cx="168" cy="390" rx="11" ry="6" fill="#78350f" />
          <ellipse cx="192" cy="390" rx="11" ry="6" fill="#78350f" />

          <!-- Torso / Cardigan -->
          <rect
            x="150"
            y="225"
            width="60"
            height="105"
            rx="18"
            fill="#175d52"
          />
          <!-- Inner warm ochre knit sweater -->
          <path d="M 170 225 L 180 270 L 190 225 Z" fill="#d97706" />
          <line
            x1="180"
            y1="270"
            x2="180"
            y2="330"
            stroke="#0f3d36"
            stroke-width="2"
          />
          <!-- Buttons -->
          <circle cx="180" cy="285" r="2.5" fill="#fef3c7" />
          <circle cx="180" cy="305" r="2.5" fill="#fef3c7" />

          <!-- Arms & Hands (Animated based on Mood!) -->
          <!-- Normal / Content Posture -->
          <g v-if="characterMood === 'normal'">
            <path
              d="M 152 240 Q 140 280 162 295"
              fill="none"
              stroke="#175d52"
              stroke-width="12"
              stroke-linecap="round"
            />
            <path
              d="M 208 240 Q 220 280 198 295"
              fill="none"
              stroke="#175d52"
              stroke-width="12"
              stroke-linecap="round"
            />
            <circle cx="180" cy="295" r="8" fill="#fbcfe8" />
          </g>

          <!-- Stressed / Hesitant Posture (Dementia Barrier: trembling raised hands & hesitation) -->
          <g v-else-if="characterMood === 'stressed'" class="hands-stressed">
            <path
              d="M 152 240 Q 130 255 145 280"
              fill="none"
              stroke="#175d52"
              stroke-width="12"
              stroke-linecap="round"
            />
            <circle cx="145" cy="280" r="7" fill="#fbcfe8" />
            <path
              d="M 208 240 Q 230 255 215 280"
              fill="none"
              stroke="#175d52"
              stroke-width="12"
              stroke-linecap="round"
            />
            <circle cx="215" cy="280" r="7" fill="#fbcfe8" />
          </g>

          <!-- Surprised / Relieved Posture (Phase 2) -->
          <g v-else-if="characterMood === 'surprised'">
            <path
              d="M 152 240 Q 145 265 160 285"
              fill="none"
              stroke="#175d52"
              stroke-width="12"
              stroke-linecap="round"
            />
            <circle cx="160" cy="285" r="7" fill="#fbcfe8" />
            <path
              d="M 208 240 Q 235 250 240 270"
              fill="none"
              stroke="#175d52"
              stroke-width="12"
              stroke-linecap="round"
            />
            <circle cx="240" cy="270" r="7" fill="#fbcfe8" />
          </g>

          <!-- Happy & Confident Posture (Phase 3: Thumbs Up / Reaching safely) -->
          <g v-else class="hands-happy">
            <path
              d="M 152 240 Q 142 275 160 295"
              fill="none"
              stroke="#175d52"
              stroke-width="12"
              stroke-linecap="round"
            />
            <circle cx="160" cy="295" r="7" fill="#fbcfe8" />
            <!-- Right arm reaching forward confidently with thumbs-up! -->
            <path
              d="M 208 240 Q 240 240 255 235"
              fill="none"
              stroke="#175d52"
              stroke-width="12"
              stroke-linecap="round"
            />
            <!-- Hand / Thumbs up -->
            <circle cx="258" cy="233" r="8" fill="#fbcfe8" />
            <text x="264" y="235" font-size="16">👍</text>
          </g>

          <!-- Neck -->
          <rect x="174" y="208" width="12" height="20" fill="#fbcfe8" />

          <!-- Head -->
          <g class="character-head">
            <!-- Face -->
            <circle cx="180" cy="180" r="28" fill="#fbcfe8" />

            <!-- Hair (Cozy silver curls) -->
            <ellipse cx="180" cy="162" rx="32" ry="18" fill="#cbd5e1" />
            <circle cx="154" cy="172" r="12" fill="#cbd5e1" />
            <circle cx="206" cy="172" r="12" fill="#cbd5e1" />
            <circle cx="180" cy="154" r="14" fill="#cbd5e1" />

            <!-- Glasses (Round frames) -->
            <circle
              cx="171"
              cy="180"
              r="9"
              fill="none"
              stroke="#475569"
              stroke-width="2.5"
            />
            <circle
              cx="189"
              cy="180"
              r="9"
              fill="none"
              stroke="#475569"
              stroke-width="2.5"
            />
            <line
              x1="180"
              y1="180"
              x2="180"
              y2="180"
              stroke="#475569"
              stroke-width="2.5"
            />

            <!-- Expression Eyes & Eyebrows based on Mood -->
            <!-- 1. Normal View (Neutral, content) -->
            <g v-if="characterMood === 'normal'">
              <circle cx="171" cy="180" r="2.5" fill="#1e293b" />
              <circle cx="189" cy="180" r="2.5" fill="#1e293b" />
              <!-- Relaxed Eyebrows -->
              <path
                d="M 165 170 Q 171 168 177 170"
                fill="none"
                stroke="#64748b"
                stroke-width="2"
              />
              <path
                d="M 183 170 Q 189 168 195 170"
                fill="none"
                stroke="#64748b"
                stroke-width="2"
              />
              <!-- Gentle Smile -->
              <path
                d="M 174 195 Q 180 199 186 195"
                fill="none"
                stroke="#1e293b"
                stroke-width="2"
                stroke-linecap="round"
              />
            </g>

            <!-- 2. Stressed / Dementia Confusion (Worried brows, anxious eyes, sweat drop) -->
            <g v-else-if="characterMood === 'stressed'" class="face-stressed">
              <!-- Slanted Worried Eyebrows \  / -->
              <path
                d="M 164 167 L 176 172"
                stroke="#dc2626"
                stroke-width="2.5"
                stroke-linecap="round"
              />
              <path
                d="M 196 167 L 184 172"
                stroke="#dc2626"
                stroke-width="2.5"
                stroke-linecap="round"
              />
              <!-- Wide anxious pupils -->
              <circle cx="171" cy="180" r="3.2" fill="#1e293b" />
              <circle cx="189" cy="180" r="3.2" fill="#1e293b" />
              <!-- Trembling / wavy worried mouth -->
              <path
                d="M 173 198 Q 177 194 180 197 Q 183 200 187 196"
                fill="none"
                stroke="#991b1b"
                stroke-width="2.5"
                stroke-linecap="round"
              />
              <!-- Sweat Drop 💧 -->
              <path
                d="M 152 175 Q 149 183 152 188 Q 155 188 155 183 Z"
                fill="#38bdf8"
                class="sweat-drop"
              />
            </g>

            <!-- 3. Surprised & Delighted (Phase 2) -->
            <g v-else-if="characterMood === 'surprised'">
              <!-- Raised Eyebrows -->
              <path
                d="M 165 166 Q 171 163 177 166"
                fill="none"
                stroke="#475569"
                stroke-width="2"
              />
              <path
                d="M 183 166 Q 189 163 195 166"
                fill="none"
                stroke="#475569"
                stroke-width="2"
              />
              <!-- Wide Eyes -->
              <circle cx="171" cy="180" r="3.5" fill="#1e293b" />
              <circle cx="189" cy="180" r="3.5" fill="#1e293b" />
              <!-- "O" Mouth -->
              <circle
                cx="180"
                cy="196"
                r="4"
                fill="none"
                stroke="#1e293b"
                stroke-width="2"
              />
            </g>

            <!-- 4. Solved / Happy & Joyful (Phase 3: Beaming crescent eyes, rosy cheeks, broad smile) -->
            <g v-else class="face-happy">
              <!-- Happy Arched Crescents ^ ^ -->
              <path
                d="M 166 182 Q 171 176 176 182"
                fill="none"
                stroke="#0f172a"
                stroke-width="3"
                stroke-linecap="round"
              />
              <path
                d="M 184 182 Q 189 176 194 182"
                fill="none"
                stroke="#0f172a"
                stroke-width="3"
                stroke-linecap="round"
              />
              <!-- Cheerful relaxed brows -->
              <path
                d="M 165 168 Q 171 165 177 168"
                fill="none"
                stroke="#64748b"
                stroke-width="2"
              />
              <path
                d="M 183 168 Q 189 165 195 168"
                fill="none"
                stroke="#64748b"
                stroke-width="2"
              />
              <!-- Rosy Cheeks -->
              <circle cx="163" cy="188" r="5" fill="#f43f5e" opacity="0.45" />
              <circle cx="197" cy="188" r="5" fill="#f43f5e" opacity="0.45" />
              <!-- Big Warm Radiant Smile ∪ -->
              <path d="M 172 193 Q 180 205 188 193 Z" fill="#b91c1c" />
              <path
                d="M 172 193 Q 180 205 188 193"
                fill="none"
                stroke="#1e293b"
                stroke-width="2"
                stroke-linecap="round"
              />
            </g>
          </g>

          <!-- Floating Overhead Mental State Indicators (No wording, pure visual icons!) -->
          <!-- A. Stressed State: Floating ? ? ? and Red Electric Brain Lightning -->
          <g v-if="characterMood === 'stressed'" class="mental-chaos">
            <text x="145" y="145" font-size="20" class="float-q1">❓</text>
            <text x="195" y="135" font-size="22" class="float-q2">❓</text>
            <text x="175" y="125" font-size="18" class="float-q3">❓</text>
            <!-- Chaotic scribble brain cloud -->
            <path
              d="M 160 115 Q 170 105 180 112 Q 195 105 200 118 Q 205 130 190 132 Q 175 136 165 128 Z"
              fill="#fee2e2"
              stroke="#ef4444"
              stroke-width="1.5"
              opacity="0.85"
            />
            <!-- Chaotic red zigzag ⚡ inside cloud -->
            <path
              d="M 170 120 L 177 114 L 182 124 L 190 116"
              fill="none"
              stroke="#dc2626"
              stroke-width="2"
              class="scribble-anim"
            />
          </g>

          <!-- B. Happy / Solved State: Floating Sparkles ✨, Heart 💚, Lightbulb 💡 -->
          <g v-if="characterMood === 'happy'" class="mental-zen">
            <text x="140" y="130" font-size="20" class="float-sparkle1">
              ✨
            </text>
            <text x="205" y="135" font-size="20" class="float-sparkle2">
              ✨
            </text>
            <text x="175" y="115" font-size="22" class="float-bulb">💡</text>
            <text x="195" y="110" font-size="18" class="float-heart">💚</text>
            <!-- Calm green aura ring -->
            <circle
              cx="180"
              cy="180"
              r="48"
              fill="none"
              stroke="#10b981"
              stroke-width="1.5"
              opacity="0.4"
              class="zen-pulse"
            />
          </g>
        </g>
      </svg>
    </div>

    <!-- Bottom Visual Action Bar (Pure Visual Icon Toggles & Interactive Slider) -->
    <footer class="story-footer">
      <!-- Quick Hands-on Fix Icons (Allows instant clicking to see the fix) -->
      <div class="interactive-tools-bar">
        <button
          type="button"
          class="tool-btn"
          :class="{ active: isHighContrastSeat }"
          @click="toggleToiletFix"
          aria-label="Toggle Toilet Contrast Seat"
          title="Contrast Seat"
        >
          <span class="tool-icon">🎨</span>
          <span class="tool-status">{{ isHighContrastSeat ? "✓" : "+" }}</span>
        </button>

        <button
          type="button"
          class="tool-btn"
          :class="{ active: !isDarkHoleRugActive }"
          @click="toggleRugFix"
          aria-label="Toggle Remove Floor Hazard Rug"
          title="Safe Floor"
        >
          <span class="tool-icon">🚫🕳️</span>
          <span class="tool-status">{{
            !isDarkHoleRugActive ? "✓" : "+"
          }}</span>
        </button>

        <button
          type="button"
          class="tool-btn"
          :class="{ active: isHighContrastBar }"
          @click="toggleBarFix"
          aria-label="Toggle High-Contrast Grab Bar"
          title="Contrast Rail"
        >
          <span class="tool-icon">🟡🖐️</span>
          <span class="tool-status">{{ isHighContrastBar ? "✓" : "+" }}</span>
        </button>
      </div>

      <!-- Live Perception Slider (Interactive Lens) -->
      <div class="lens-slider-container">
        <span class="slider-end-icon" aria-hidden="true" title="Barrier"
          >🌫️❓</span
        >
        <input
          type="range"
          min="0"
          max="100"
          v-model.number="sliderPosition"
          @input="sliderMode = true"
          class="perception-range"
          aria-label="Interactive perception comparison slider"
        />
        <span class="slider-end-icon" aria-hidden="true" title="Clarity"
          >✨😊</span
        >
      </div>
    </footer>
  </div>
</template>

<style scoped>
.visual-story-card {
  width: 100%;
  height: 100%;
  min-height: 380px;
  max-height: 460px;
  background: #ffffff;
  border-radius: 24px;
  border: 1.5px solid var(--color-border, #e2e8f0);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  transition: all 0.3s ease;
}

.visual-story-card:hover {
  box-shadow: 0 16px 44px rgba(23, 93, 82, 0.12);
}

/* --- Top HUD --- */
.story-hud {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.25rem;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  gap: 0.75rem;
  flex-wrap: wrap;
}

/* Cognitive Load Gauge Badge */
.cognitive-gauge-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.85rem;
  border-radius: 999px;
  background: white;
  border: 1.5px solid #e2e8f0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.cognitive-gauge-badge.load-critical {
  border-color: #ef4444;
  background: #fef2f2;
  color: #b91c1c;
  animation: pulseWarning 1.5s infinite;
}

.cognitive-gauge-badge.load-moderate {
  border-color: #f59e0b;
  background: #fffbeb;
  color: #b45309;
}

.cognitive-gauge-badge.load-optimal {
  border-color: #10b981;
  background: #ecfdf5;
  color: #047857;
}

.brain-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.meter-track {
  width: 56px;
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.meter-fill {
  height: 100%;
  border-radius: 999px;
  transition:
    width 0.5s ease-out,
    background-color 0.5s ease;
}

.load-critical .meter-fill {
  background-color: #ef4444;
}

.load-moderate .meter-fill {
  background-color: #f59e0b;
}

.load-optimal .meter-fill {
  background-color: #10b981;
}

.load-percent {
  font-size: 0.82rem;
  font-weight: 800;
  font-family: monospace;
}

/* Stage Switcher Pills */
.stage-nav {
  display: flex;
  align-items: center;
  background: #edf2f7;
  padding: 3px;
  border-radius: 999px;
  gap: 2px;
}

.stage-btn {
  background: transparent;
  border: none;
  border-radius: 999px;
  padding: 0.35rem 0.65rem;
  font-size: 1.05rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  line-height: 1;
}

.stage-btn:hover {
  background: rgba(255, 255, 255, 0.6);
  transform: scale(1.08);
}

.stage-btn.active {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  transform: scale(1.05);
}

/* Playback Controls */
.playback-controls {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.icon-control-btn {
  background: white;
  border: 1px solid #cbd5e1;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  cursor: pointer;
  color: #334155;
  transition: all 0.2s ease;
}

.icon-control-btn:hover {
  background: var(--color-primary, #175d52);
  color: white;
  border-color: var(--color-primary, #175d52);
}

/* --- SVG Stage --- */
.svg-stage-container {
  flex: 1;
  width: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
}

.story-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.interactive-hotspot {
  cursor: pointer;
}

.interactive-hotspot:hover .action-pulse {
  transform: scale(1.3);
  opacity: 1;
}

.action-pulse {
  transform-origin: center;
  transition: transform 0.2s ease;
}

/* --- Animations & Keyframes --- */
@keyframes pulseWarning {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.03);
  }
}

/* Glare pulse on floor */
.glare-pulse {
  animation: shimmerGlare 2.5s infinite alternate ease-in-out;
}

@keyframes shimmerGlare {
  0% {
    opacity: 0.3;
    transform: scaleX(0.9);
  }
  100% {
    opacity: 0.8;
    transform: scaleX(1.1);
  }
}

/* Black Hole Vortex */
.hole-vortex {
  animation: vortexSpin 4s infinite linear;
  transform-origin: 330px 370px;
}

@keyframes vortexSpin {
  0% {
    transform: scale(0.96) rotate(0deg);
  }
  50% {
    transform: scale(1.04) rotate(180deg);
  }
  100% {
    transform: scale(0.96) rotate(360deg);
  }
}

.hazard-ring {
  animation: hazardExpand 2s infinite ease-out;
  transform-origin: 330px 370px;
}

@keyframes hazardExpand {
  0% {
    transform: scale(0.85);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.2);
    opacity: 0;
  }
}

.hazard-icon {
  animation: hopWarning 1.2s infinite ease-in-out;
}

@keyframes hopWarning {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

/* Safe guide path */
.safe-guide-path {
  animation: dashFlow 2s linear infinite;
}

@keyframes dashFlow {
  from {
    stroke-dashoffset: 28;
  }
  to {
    stroke-dashoffset: 0;
  }
}

/* Glowing ring for contrast seat */
.glow-ring {
  animation: rotateGlow 6s linear infinite;
  transform-origin: 458px 240px;
}

@keyframes rotateGlow {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* Magic tool wand */
.magic-wand-tool {
  animation: floatWand 1.5s infinite alternate ease-in-out;
}

@keyframes floatWand {
  0% {
    transform: translate(0, 0);
  }
  100% {
    transform: translate(6px, -8px);
  }
}

/* Floating questions */
.float-q1 {
  animation: floatQ 2s infinite ease-in-out;
}
.float-q2 {
  animation: floatQ 2s 0.3s infinite ease-in-out;
}
.float-q3 {
  animation: floatQ 2s 0.6s infinite ease-in-out;
}

@keyframes floatQ {
  0%,
  100% {
    transform: translateY(0) scale(1);
    opacity: 0.8;
  }
  50% {
    transform: translateY(-8px) scale(1.15);
    opacity: 1;
  }
}

/* Sweat drop */
.sweat-drop {
  animation: drip 1.5s infinite ease-in;
}

@keyframes drip {
  0% {
    transform: translateY(0);
    opacity: 0;
  }
  30% {
    opacity: 1;
  }
  100% {
    transform: translateY(12px);
    opacity: 0;
  }
}

/* Scribble brain */
.scribble-anim {
  animation: scribbleShake 0.4s infinite alternate;
}

@keyframes scribbleShake {
  0% {
    transform: translate(-1px, -1px);
  }
  100% {
    transform: translate(1px, 1px);
  }
}

/* Zen items */
.float-sparkle1 {
  animation: sparklePop 1.8s infinite ease-in-out;
}
.float-sparkle2 {
  animation: sparklePop 1.8s 0.5s infinite ease-in-out;
}
.float-bulb {
  animation: bulbGlow 2s infinite alternate ease-in-out;
}
.float-heart {
  animation: heartThrob 1.4s infinite ease-in-out;
}

@keyframes sparklePop {
  0%,
  100% {
    transform: scale(0.9) rotate(-10deg);
    opacity: 0.7;
  }
  50% {
    transform: scale(1.2) rotate(10deg);
    opacity: 1;
  }
}

@keyframes bulbGlow {
  0% {
    transform: translateY(0);
    opacity: 0.8;
  }
  100% {
    transform: translateY(-5px);
    opacity: 1;
    filter: drop-shadow(0 0 4px #f59e0b);
  }
}

@keyframes heartThrob {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.25);
  }
}

.zen-pulse {
  animation: zenRing 3s infinite ease-out;
  transform-origin: 180px 180px;
}

@keyframes zenRing {
  0% {
    transform: scale(0.9);
    opacity: 0.6;
  }
  100% {
    transform: scale(1.25);
    opacity: 0;
  }
}

/* Character mood transitions */
.transition-all {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

/* --- Bottom Footer Controls --- */
.story-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
  gap: 1rem;
  flex-wrap: wrap;
}

/* Interactive Quick Fix Icons */
.interactive-tools-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.65rem;
  background: #f1f5f9;
  border: 1.5px solid #cbd5e1;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.95rem;
  line-height: 1;
}

.tool-btn:hover {
  background: #e2e8f0;
  transform: translateY(-1px);
}

.tool-btn.active {
  background: #ecfdf5;
  border-color: #10b981;
  color: #047857;
}

.tool-status {
  font-size: 0.75rem;
  font-weight: 800;
  padding: 1px 4px;
  border-radius: 4px;
  background: white;
}

.tool-btn.active .tool-status {
  background: #10b981;
  color: white;
}

/* Lens Drag Slider */
.lens-slider-container {
  flex: 1;
  min-width: 140px;
  max-width: 220px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.slider-end-icon {
  font-size: 1.05rem;
  line-height: 1;
  user-select: none;
}

.perception-range {
  flex: 1;
  height: 6px;
  accent-color: var(--color-primary, #175d52);
  cursor: pointer;
}

@media (max-width: 640px) {
  .story-hud {
    padding: 0.6rem 0.85rem;
    gap: 0.5rem;
  }
  .stage-btn {
    padding: 0.3rem 0.5rem;
    font-size: 0.95rem;
  }
  .story-footer {
    padding: 0.6rem 0.85rem;
    flex-direction: column;
    align-items: stretch;
  }
  .lens-slider-container {
    max-width: 100%;
  }
}
</style>
