import { reactive } from 'vue'

export interface LayoutState {
  id: string;
  name: string;
  timestamp: string;
  room: 'kitchen' | 'bathroom';
  states: Record<number, { contrast: number; color: string }>;
}

export const bathroomStore = reactive({
  hasSavedChanges: false,
  savedStates: {
    1: { contrast: 0, color: '#1d443b' },
    2: { contrast: 0, color: '#1d443b' },
    3: { contrast: 0, color: '#1d443b' },
    4: { contrast: 0, color: '#688c83' },
    5: { contrast: 0, color: '#aabcb6' }
  },
  savedLayouts: [] as LayoutState[]
})

export const kitchenStore = reactive({
  hasSavedChanges: false,
  savedStates: {
    1: { contrast: 0, color: '#3b5a51' },
    2: { contrast: 0, color: '#94c0b4' },
    3: { contrast: 0, color: '#ff5555' },
    4: { contrast: 0, color: '#4a6b8c' },
    5: { contrast: 0, color: '#d9a05b' },
    6: { contrast: 0, color: '#7b9eb0' }
  },
  savedLayouts: [] as LayoutState[]
})

export const outingScheduleStore = reactive({
  destination: '',
  destinationCoords: null as { lat: number; lon: number } | null,
  selectedDay: 'Tuesday',
  selectedHour: 10,
  recommendedWindow: '10:00–11:00 AM',
  noiseLevel: 'Low',
  crowdLevel: 'Light',
  decibels: 53.4,
  pedestrianCount: 416,
  isPrepared: false
})
