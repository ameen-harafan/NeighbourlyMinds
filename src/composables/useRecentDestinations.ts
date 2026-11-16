import { ref } from 'vue'

const RECENT_KEY = 'neighborlyminds_recent_destinations'

export function useRecentDestinations() {
  const loadRecentDestinations = (): string[] => {
    try {
      const raw = localStorage.getItem(RECENT_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed.slice(0, 5)
        }
      }
    } catch (e) {
      console.warn('Could not read recent destinations', e)
    }
    return []
  }

  const recentDestinations = ref<string[]>(loadRecentDestinations())

  const saveRecentDestination = (dest: string) => {
    if (!dest || !dest.trim()) return
    try {
      const trimmed = dest.trim()
      const current = loadRecentDestinations()
      const updated = [trimmed, ...current.filter(d => d.toLowerCase() !== trimmed.toLowerCase())].slice(0, 5)
      localStorage.setItem(RECENT_KEY, JSON.stringify(updated))
      recentDestinations.value = updated
    } catch (e) {
      console.warn('Could not save recent destination', e)
    }
  }

  return {
    recentDestinations,
    saveRecentDestination,
    loadRecentDestinations
  }
}
