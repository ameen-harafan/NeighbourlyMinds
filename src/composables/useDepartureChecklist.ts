import { ref, computed, type Ref, type ComputedRef } from 'vue'
import type { DestinationAnchor } from '../utils/activityData'

export interface ChecklistItem {
  id: string
  icon: string
  title: string
  hint?: string
  isCustom?: boolean
}

export const CORE_CHECKLIST_ITEMS: ChecklistItem[] = [
  {
    id: 'shoes',
    icon: '👟',
    title: 'Comfortable flat footwear & weather protection',
    hint: 'Supportive walking shoes; check if you need a warm layer, hat, or umbrella.',
    isCustom: false
  },
  {
    id: 'water',
    icon: '💧',
    title: 'Bottle of water & scheduled medication',
    hint: 'Staying hydrated keeps energy steady; bring any midday tablets.',
    isCustom: false
  },
  {
    id: 'keys',
    icon: '🔑',
    title: 'House keys, wallet & myki / concession card',
    hint: 'Keep them in your usual familiar pocket or bag compartment.',
    isCustom: false
  },
  {
    id: 'phone',
    icon: '📱',
    title: 'Charged mobile phone with emergency contact',
    hint: 'Ensure family or support contact numbers are easily accessible.',
    isCustom: false
  }
]

export function getSuggestedDestinationItem(destName: string, anchor?: DestinationAnchor): ChecklistItem {
  const lower = (destName || '').toLowerCase()
  if (lower.includes('library')) {
    return {
      id: 'custom_dest',
      icon: '📚',
      title: 'Library card & books to return',
      hint: 'Ready for borrowing and comfortable reading in quiet corners.',
      isCustom: true
    }
  } else if (
    lower.includes('bayside') ||
    lower.includes('supermarket') ||
    lower.includes('shop') ||
    lower.includes('centre') ||
    lower.includes('coles') ||
    lower.includes('woolworths')
  ) {
    return {
      id: 'custom_dest',
      icon: '🛒',
      title: 'Written shopping list & reusable sturdy bags',
      hint: 'A written list avoids memory fatigue while navigating aisles.',
      isCustom: true
    }
  } else if (lower.includes('chemist') || lower.includes('pharmacy')) {
    return {
      id: 'custom_dest',
      icon: '💊',
      title: 'Prescriptions & Medicare / concession card',
      hint: 'Have your repeat forms and concession cards ready for the dispensary.',
      isCustom: true
    }
  } else if (lower.includes('clinic') || lower.includes('medical') || lower.includes('doctor')) {
    return {
      id: 'custom_dest',
      icon: '🩺',
      title: 'Appointment details & Medicare card',
      hint: 'Assists your clinic visit without delay.',
      isCustom: true
    }
  } else if (lower.includes('park') || lower.includes('garden')) {
    return {
      id: 'custom_dest',
      icon: '🌳',
      title: 'Sun protection (hat & sunglasses)',
      hint: 'Essential protection for relaxing on lakeside and shaded benches.',
      isCustom: true
    }
  }
  return {
    id: 'custom_dest',
    icon: '🎯',
    title: 'Special item for this outing',
    hint: anchor?.essentials || 'Tap edit to specify what you want to bring (e.g. walking stick, parcel, glasses).',
    isCustom: true
  }
}

export function useDepartureChecklist(
  _destination?: Ref<string>,
  _currentAnchor?: Ref<DestinationAnchor | undefined> | ComputedRef<DestinationAnchor | undefined>
) {
  const checkedItems = ref<Record<string, boolean>>({
    shoes: false,
    water: false,
    keys: false,
    phone: false
  })

  const customItems = ref<ChecklistItem[]>([])

  const departureChecklist = computed<ChecklistItem[]>(() => [
    ...CORE_CHECKLIST_ITEMS,
    ...customItems.value
  ])

  const toggleChecklistItem = (id: string) => {
    checkedItems.value[id] = !checkedItems.value[id]
  }

  const addCustomItem = (title: string, icon = '🎯', hint = 'Personal item for today') => {
    if (!title.trim()) return
    const newId = `custom_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
    customItems.value.push({
      id: newId,
      icon: icon || '🎯',
      title: title.trim(),
      hint: hint ? hint.trim() : 'Personal item for today',
      isCustom: true
    })
    checkedItems.value[newId] = false
  }

  const editCustomItem = (id: string, newTitle: string) => {
    if (!newTitle.trim()) return
    const item = customItems.value.find(i => i.id === id)
    if (item) {
      item.title = newTitle.trim()
    }
  }

  const deleteCustomItem = (id: string) => {
    customItems.value = customItems.value.filter(i => i.id !== id)
    delete checkedItems.value[id]
  }

  const checkedCount = computed(() => {
    return departureChecklist.value.filter(item => checkedItems.value[item.id]).length
  })

  const allChecked = computed(() => {
    return departureChecklist.value.length > 0 && checkedCount.value === departureChecklist.value.length
  })

  const resetChecklist = () => {
    for (const item of departureChecklist.value) {
      checkedItems.value[item.id] = false
    }
  }

  return {
    checkedItems,
    customItems,
    departureChecklist,
    toggleChecklistItem,
    addCustomItem,
    editCustomItem,
    deleteCustomItem,
    checkedCount,
    allChecked,
    resetChecklist
  }
}

