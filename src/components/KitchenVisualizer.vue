<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import kitchenSvg from '../assets/kitchen_template.svg?raw'

const props = defineProps({
  contrastLevel: {
    type: Number,
    default: 0
  },
  itemStates: {
    type: Object as () => Record<number, { contrast: number; color: string }>,
    default: () => ({
      1: { contrast: 0, color: '#3b5a51' },
      2: { contrast: 0, color: '#94c0b4' },
      3: { contrast: 0, color: '#ff5555' },
      4: { contrast: 0, color: '#4a6b8c' },
      5: { contrast: 0, color: '#d9a05b' },
      6: { contrast: 0, color: '#7b9eb0' }
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
  ] : [59, 90, 81];
}

function colourForLevel(level: number, start: number[], endHexOrRgb: string | number[]) {
  const amount = level / 100
  const end = typeof endHexOrRgb === 'string' ? hexToRgb(endHexOrRgb) : endHexOrRgb
  const channels = start.map((channel, index) => interpolateChannel(channel, end[index]!, amount))
  return `#${channels.map((channel) => channel.toString(16).padStart(2, '0')).join('').toUpperCase()}`
}

function applySvgColours() {
  if (!room.value) return

  const cabinets = room.value.querySelectorAll<SVGElement>('.contrast-cabinet')
  const counter = room.value.querySelectorAll<SVGElement>('.contrast-counter')
  const stove = room.value.querySelectorAll<SVGElement>('.contrast-stove-burner')
  const fridges = room.value.querySelectorAll<SVGElement>('.contrast-fridge')
  const ovens = room.value.querySelectorAll<SVGElement>('.contrast-oven')
  const sinks = room.value.querySelectorAll<SVGElement>('.contrast-sink')

  const s1 = props.itemStates[1] || { contrast: 0, color: '#3b5a51' }
  const s2 = props.itemStates[2] || { contrast: 0, color: '#94c0b4' }
  const s3 = props.itemStates[3] || { contrast: 0, color: '#ff5555' }
  const s4 = props.itemStates[4] || { contrast: 0, color: '#4a6b8c' }
  const s5 = props.itemStates[5] || { contrast: 0, color: '#d9a05b' }
  const s6 = props.itemStates[6] || { contrast: 0, color: '#7b9eb0' }

  const cabinetFill = s1.contrast > 0 ? colourForLevel(s1.contrast, [251, 251, 251], s1.color) : ''
  const cabinetStroke = s1.contrast > 0 ? colourForLevel(s1.contrast, [119, 119, 119], s1.color) : ''
  const counterFill = s2.contrast > 0 ? colourForLevel(s2.contrast, [230, 230, 230], s2.color) : ''
  const stoveStroke = s3.contrast > 0 ? colourForLevel(s3.contrast, [119, 119, 119], s3.color) : ''
  const fridgeFill = s4.contrast > 0 ? colourForLevel(s4.contrast, [251, 251, 251], s4.color) : ''
  const fridgeStroke = s4.contrast > 0 ? colourForLevel(s4.contrast, [136, 136, 136], s4.color) : ''
  const ovenFill = s5.contrast > 0 ? colourForLevel(s5.contrast, [119, 119, 119], s5.color) : ''
  const sinkStroke = s6.contrast > 0 ? colourForLevel(s6.contrast, [119, 119, 119], s6.color) : ''

  cabinets.forEach(el => {
    el.style.fill = cabinetFill
    el.style.stroke = cabinetStroke 
  })

  counter.forEach(el => {
    el.style.fill = counterFill
  })

  stove.forEach(el => {
    if (!el.classList.contains('active') || s3.contrast > 0) {
       el.style.stroke = stoveStroke
       el.style.strokeWidth = s3.contrast > 0 ? (1 + (2 * (s3.contrast / 100))) + 'px' : ''
    }
  })

  fridges.forEach(el => {
    el.style.fill = fridgeFill
    el.style.stroke = fridgeStroke
  })

  ovens.forEach(el => {
    el.style.fill = ovenFill
  })

  sinks.forEach(el => {
    el.style.stroke = sinkStroke
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
      aria-label="Interactive kitchen layout visualizer"
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
          class="kitchen-svg-container" 
          :style="{ filter: `brightness(${100 + (lightingLevel * 0.4)}%)` }"
          v-html="kitchenSvg"
        ></div>
        
        <!-- Interactive Markers -->
        <template v-if="!hideMarkers">
          <button 
            type="button"
            :class="['marker marker-1', { active: activeMarker === 1 }]"
            @click="emit('selectMarker', 1)"
            aria-label="Marker 1: Cabinets"
            :aria-pressed="activeMarker === 1"
          >1</button>
          
          <button 
            type="button"
            :class="['marker marker-2', { active: activeMarker === 2 }]"
            @click="emit('selectMarker', 2)"
            aria-label="Marker 2: Countertop"
            :aria-pressed="activeMarker === 2"
          >2</button>
          
          <button 
            type="button"
            :class="['marker marker-3', { active: activeMarker === 3 }]"
            @click="emit('selectMarker', 3)"
            aria-label="Marker 3: Stove"
            :aria-pressed="activeMarker === 3"
          >3</button>

          <button 
            type="button"
            :class="['marker marker-4', { active: activeMarker === 4 }]"
            @click="emit('selectMarker', 4)"
            aria-label="Marker 4: Fridge"
            :aria-pressed="activeMarker === 4"
          >4</button>

          <button 
            type="button"
            :class="['marker marker-5', { active: activeMarker === 5 }]"
            @click="emit('selectMarker', 5)"
            aria-label="Marker 5: Oven"
            :aria-pressed="activeMarker === 5"
          >5</button>

          <button 
            type="button"
            :class="['marker marker-6', { active: activeMarker === 6 }]"
            @click="emit('selectMarker', 6)"
            aria-label="Marker 6: Sink"
            :aria-pressed="activeMarker === 6"
          >6</button>
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
  aspect-ratio: 2 / 1; /* Match the SVG 1400x700 */
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

.kitchen-svg-container {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
}

.kitchen-svg-container :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}

.kitchen-svg-container :deep(.contrast-cabinet), 
.kitchen-svg-container :deep(.contrast-counter), 
.kitchen-svg-container :deep(.contrast-stove-burner) {
  transition: fill 0.3s ease, stroke 0.3s ease, stroke-width 0.3s ease;
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

/* Position markers based on SVG coordinates (0-1400, 0-700) */
/* Marker 1: Cabinets (approx center of lower cabinets x=586, y=500 -> 42%, 71%) */
.marker-1 {
  left: 42%;
  top: 71%;
}

/* Marker 2: Countertop (x=900, y=380 -> 64%, 54%) */
.marker-2 {
  left: 64%;
  top: 54%;
}

/* Marker 3: Stove elements (x=1110, y=378 -> 79%, 54%) */
.marker-3 {
  left: 79%;
  top: 54%;
}

/* Marker 4: Fridge */
.marker-4 {
  left: 10%;
  top: 45%;
}

/* Marker 5: Oven */
.marker-5 {
  left: 81%;
  top: 75%;
}

/* Marker 6: Sink */
.marker-6 {
  left: 61%;
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
