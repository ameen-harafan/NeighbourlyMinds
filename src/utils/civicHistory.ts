/**
 * Accessibility Audit & Feedback History Service
 * Tracks, manages, and displays history logs of accessibility assessments and action plans.
 */

export interface CivicReportItem {
  id: number
  reference_id: string
  space_type?: 'private' | 'public'
  council_name: string
  council_email: string
  sender_name: string
  sender_email: string
  location_name: string
  facility_type?: string
  barrier_summary: any[]
  barrier_count: number
  email_subject: string
  email_body: string
  status: 'SENT' | 'ACKNOWLEDGED' | 'UNDER_REVIEW' | 'SAVED'
  created_at: string
}

const LOCAL_STORAGE_KEY = 'neighborlyminds_civic_reports'

/**
 * Fetches accessibility reports from backend with offline localStorage fallback.
 */
export async function fetchCivicReports(statusFilter = 'ALL', searchQuery = ''): Promise<CivicReportItem[]> {
  try {
    const params = new URLSearchParams()
    if (statusFilter && statusFilter !== 'ALL') {
      params.append('status', statusFilter)
    }
    if (searchQuery && searchQuery.trim()) {
      params.append('search', searchQuery.trim())
    }

    const res = await fetch(`/api/councils/reports?${params.toString()}`)
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data)) {
        let merged: CivicReportItem[] = [...data]
        try {
          const cached = localStorage.getItem(LOCAL_STORAGE_KEY)
          if (cached) {
            const localList: CivicReportItem[] = JSON.parse(cached)
            localList.forEach(localItem => {
              if (!merged.some(m => m.reference_id === localItem.reference_id)) {
                merged.unshift(localItem)
              }
            })
          }
          localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(merged))
        } catch (e) {
          // ignore storage quota
        }
        return merged
      }
    }
  } catch (err) {
    console.warn('[CivicHistory] Backend unavailable, falling back to local storage:', err)
  }

  // Fallback to local storage
  try {
    const cached = localStorage.getItem(LOCAL_STORAGE_KEY)
    if (cached) {
      let items: CivicReportItem[] = JSON.parse(cached)
      if (statusFilter !== 'ALL') {
        items = items.filter(i => (i.status || 'SAVED').toUpperCase() === statusFilter.toUpperCase())
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim()
        items = items.filter(i =>
          i.reference_id.toLowerCase().includes(q) ||
          i.council_name.toLowerCase().includes(q) ||
          i.location_name.toLowerCase().includes(q)
        )
      }
      return items
    }
  } catch (e) {
    // ignore
  }

  return []
}

/**
 * Saves a report or home plan to localStorage backup immediately.
 */
export function saveReportToLocalHistory(report: any): void {
  try {
    const existing = localStorage.getItem(LOCAL_STORAGE_KEY)
    const list: CivicReportItem[] = existing ? JSON.parse(existing) : []
    const formatted: CivicReportItem = {
      id: report.id || Date.now(),
      reference_id: report.reference_id || `AUDIT-${Date.now().toString(36).toUpperCase()}`,
      space_type: report.space_type || 'public',
      council_name: report.council_name || (report.space_type === 'private' ? 'Private Residence' : 'Victorian Municipal Council'),
      council_email: report.council_email || '',
      sender_name: report.sender_name || 'Resident',
      sender_email: report.sender_email || '',
      location_name: report.location_name || 'Room / Facility Space',
      facility_type: report.facility_type || (report.space_type === 'private' ? 'Home Room' : 'Public Space'),
      barrier_summary: Array.isArray(report.barrier_summary) ? report.barrier_summary : [],
      barrier_count: Array.isArray(report.barrier_summary) ? report.barrier_summary.length : 1,
      email_subject: report.email_subject || 'Accessibility Assessment Report',
      email_body: report.email_body || '',
      status: report.status || 'SAVED',
      created_at: report.created_at || new Date().toISOString()
    }

    const filtered = list.filter(r => r.reference_id !== formatted.reference_id)
    filtered.unshift(formatted)
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(filtered.slice(0, 50)))
  } catch (err) {
    console.warn('[CivicHistory] Failed to save local report backup:', err)
  }
}

/**
 * Simulates or updates a submission status (e.g. ACKNOWLEDGED).
 */
export async function updateReportStatus(refId: string, status: string): Promise<boolean> {
  try {
    const res = await fetch(`/api/councils/reports/${refId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    })
    return res.ok
  } catch (e) {
    return false
  }
}

/**
 * Formats ISO timestamp for clear dementia-friendly display (e.g. "05 Oct 2026, 2:30 PM").
 */
export function formatReportDate(isoString: string): string {
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return 'Recently'
    return d.toLocaleDateString('en-AU', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (e) {
    return isoString
  }
}
