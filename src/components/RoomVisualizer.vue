<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import bathroomSvg from '../assets/bathroom_template.svg?raw'

const props = defineProps({
  itemStates: {
    type: Object as () => Record<number, { contrast: number; color: string }>,
    default: () => ({
      1: { contrast: 0, color: '#1d443b' },
      2: { contrast: 0, color: '#1d443b' },
      3: { contrast: 0, color: '#1d443b' },
      4: { contrast: 0, color: '#688c83' },
      5: { contrast: 0, color: '#aabcb6' }
    })
  },
  lightingLevel: {
    type: Number,
    default: 0
  },
  activeMarker: {
    type: Number,
    default: undefined
  },
  hideMarkers: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['selectMarker'])
const room = ref<HTMLElement | null>(null)
const containerRef = ref<HTMLElement | null>(null)
const mousePos = ref({ x: 50, y: 50 })
const isHovering = ref(false)

const handleMouseMove = (e: MouseEvent) => {
  if (!containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  mousePos.value.x = ((e.clientX - rect.left) / rect.width) * 100
  mousePos.value.y = ((e.clientY - rect.top) / rect.height) * 100
}

function interpolateChannel(start: number, end: number, amount: number) {
  return Math.round(start + (end - start) * amount)
}

function hexToRgb(hex: string) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result && result[1] && result[2] && result[3] ? [
    parseInt(result[1], 16),
    parseInt(result[2], 16),
    parseInt(result[3], 16)
  ] : [29, 68, 59];
}

function colourForLevel(level: number, start: number[], endHexOrRgb: string | number[]) {
  const amount = level / 100
  const end = typeof endHexOrRgb === 'string' ? hexToRgb(endHexOrRgb) : endHexOrRgb
  const channels = start.map((channel, index) => interpolateChannel(channel, end[index]!, amount))
  return `#${channels.map((channel) => channel.toString(16).padStart(2, '0')).join('').toUpperCase()}`
}

function applySvgColours() {
  if (!room.value) return

  const doors = room.value.querySelectorAll<SVGElement>('.contrast-door')
  const vanities = room.value.querySelectorAll<SVGElement>('.contrast-vanity')
  const floors = room.value.querySelectorAll<SVGElement>('.contrast-floor')
  const toilets = room.value.querySelectorAll<SVGElement>('.contrast-toilet')
  const showers = room.value.querySelectorAll<SVGElement>('.contrast-shower')

  const s1 = props.itemStates[1] || { contrast: 0, color: '#1d443b' }
  const s2 = props.itemStates[2] || { contrast: 0, color: '#1d443b' }
  const s3 = props.itemStates[3] || { contrast: 0, color: '#1d443b' }
  const s4 = props.itemStates[4] || { contrast: 0, color: '#688c83' }
  const s5 = props.itemStates[5] || { contrast: 0, color: '#aabcb6' }

  const doorFill = s1.contrast > 0 ? colourForLevel(s1.contrast, [255, 255, 255], s1.color) : ''
  const doorStroke = s1.contrast > 0 ? colourForLevel(s1.contrast, [26, 26, 26], s1.color) : ''
  const vanityFill = s2.contrast > 0 ? colourForLevel(s2.contrast, [248, 248, 248], s2.color) : ''
  const vanityStroke = s2.contrast > 0 ? colourForLevel(s2.contrast, [26, 26, 26], s2.color) : ''
  const floorFill = s3.contrast > 0 ? colourForLevel(s3.contrast, [230, 222, 203], s3.color) : ''
  
  const toiletFill = s4.contrast > 0 ? colourForLevel(s4.contrast, [255, 255, 255], s4.color) : ''
  const toiletStroke = s4.contrast > 0 ? colourForLevel(s4.contrast, [26, 26, 26], s4.color) : ''
  const showerStroke = s5.contrast > 0 ? colourForLevel(s5.contrast, [26, 26, 26], s5.color) : ''

  doors.forEach(el => {
    el.style.fill = doorFill
    el.style.stroke = doorStroke
  })

  vanities.forEach(el => {
    el.style.fill = vanityFill
    el.style.stroke = vanityStroke
  })

  floors.forEach(el => {
    el.style.fill = floorFill
  })

  toilets.forEach(el => {
    el.style.fill = toiletFill
    el.style.stroke = toiletStroke
  })

  showers.forEach(el => {
    el.style.stroke = showerStroke
  })
}

watch(() => props.itemStates, () => {
  nextTick(applySvgColours)
}, { deep: true })

onMounted(() => {
  applySvgColours()
})
</script>

<template>
  <div class="room-visualizer">
    <div 
      class="room-container"
      ref="containerRef"
      @mousemove="handleMouseMove"
      @mouseenter="isHovering = true"
      @mouseleave="isHovering = false"
      role="region"
      aria-label="Interactive bathroom layout visualizer"
    >
      <div 
        class="zoom-wrapper"
        :style="{
          transform: isHovering ? 'scale(1.5)' : 'scale(1)',
          transformOrigin: `${mousePos.x}% ${mousePos.y}%`
        }"
      >
        <div 
          ref="room" 
          class="bathroom-svg-container" 
          :style="{ filter: `brightness(${100 + (lightingLevel * 0.4)}%)` }"
          v-html="bathroomSvg"
        ></div>
        
        <!-- Interactive Markers -->
        <template v-if="!hideMarkers">
          <button 
            type="button"
            :class="['marker marker-1', { active: activeMarker === 1 }]"
            @click="emit('selectMarker', 1)"
            aria-label="Marker 1: Door frame"
            :aria-pressed="activeMarker === 1"
          >1</button>
          
          <button 
            type="button"
            :class="['marker marker-2', { active: activeMarker === 2 }]"
            @click="emit('selectMarker', 2)"
            aria-label="Marker 2: Vanity and Basin"
            :aria-pressed="activeMarker === 2"
          >2</button>
          
          <button 
            type="button"
            :class="['marker marker-3', { active: activeMarker === 3 }]"
            @click="emit('selectMarker', 3)"
            aria-label="Marker 3: Floor contrast"
            :aria-pressed="activeMarker === 3"
          >3</button>
          <button 
            type="button"
            :class="['marker marker-4', { active: activeMarker === 4 }]"
            @click="emit('selectMarker', 4)"
            aria-label="Marker 4: Toilet"
            :aria-pressed="activeMarker === 4"
          >4</button>
          <button 
            type="button"
            :class="['marker marker-5', { active: activeMarker === 5 }]"
            @click="emit('selectMarker', 5)"
            aria-label="Marker 5: Shower"
            :aria-pressed="activeMarker === 5"
          >5</button>
        </template>
        
        <slot></slot>
      </div>
    </div>
    
    <div v-if="!hideMarkers" class="visualizer-caption">
      Click the numbered markers or use the element buttons to review specific areas of this room.
    </div>
  </div>
</template>

<style scoped>
.room-visualizer {
  background: var(--color-bg-sage, #f7f9f7);
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 2rem;
}

.room-container {
  position: relative;
  width: 100%;
  aspect-ratio: 1200 / 650; /* Match the SVG 1200x650 */
  background: #f4f3f1;
  border-radius: 12px;
  overflow: hidden;
  cursor: zoom-in;
}

.zoom-wrapper {
  width: 100%;
  height: 100%;
  transition: transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  will-change: transform;
}

.bathroom-svg-container {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
}

.bathroom-svg-container :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}

.bathroom-svg-container :deep(.contrast-door), 
.bathroom-svg-container :deep(.contrast-vanity), 
.bathroom-svg-container :deep(.contrast-floor), 
.bathroom-svg-container :deep(.contrast-toilet), 
.bathroom-svg-container :deep(.contrast-shower) {
  transition: fill 0.3s ease, stroke 0.3s ease;
}

/* Markers */
.marker {
  position: absolute;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: white;
  border: 2px solid #55877f;
  color: #55877f;
  font-weight: 800;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 5px rgba(0,0,0,0.15);
  transition: all 0.2s ease;
  z-index: 10;
}

.marker:hover {
  transform: scale(1.1);
}

.marker:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 2px;
  z-index: 20;
}

.marker.active {
  background: #55877f;
  color: white;
  transform: scale(1.15);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

/* Position markers based on SVG coordinates (0-1200, 0-650) */
/* Marker 1: Doorway distinction (approx door handle x=50, y=350 -> 4%, 54%) */
.marker-1 {
  left: 4%;
  top: 54%;
}

/* Marker 2: Sink visibility (approx sink x=620, y=350 -> 52%, 54%) */
.marker-2 {
  left: 52%;
  top: 54%;
}

/* Marker 3: Floor (x=600, y=550 -> 50%, 78%) */
.marker-3 {
  left: 50%;
  top: 78%;
}

/* Marker 4: Toilet */
.marker-4 {
  left: 33%;
  top: 65%;
}

/* Marker 5: Shower */
.marker-5 {
  left: 75%;
  top: 45%;
}

.visualizer-caption {
  padding: 1rem;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  background: #faf8f5;
  border: 1px solid #e5e0d8;
  border-top: none;
  border-radius: 0 0 12px 12px;
}

@media (prefers-reduced-motion: reduce) {
  .zoom-wrapper {
    transition: none !important;
    transform: none !important;
  }
  .marker {
    transition: none !important;
  }
}
</style>
