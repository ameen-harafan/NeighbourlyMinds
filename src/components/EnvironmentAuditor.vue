<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  extractBarrierStatistics,
  generateCouncilEmailDraft,
  generateHomeRenovationPlan,
  SPATIAL_HAZARD_TAXONOMY,
  type BarrierStatistic,
  type CouncilContact,
  type StandardHazardCategory
} from '@/utils/councilAdvocacy'
import {
  extractExifGpsFromBlob,
  VICTORIAN_PUBLIC_LOCATION_PRESETS,
  type ExifGpsCoordinates
} from '@/utils/exifParser'
import {
  fetchCivicReports,
  saveReportToLocalHistory,
  formatReportDate,
  updateReportStatus,
  type CivicReportItem
} from '@/utils/civicHistory'

const fileInput = ref<HTMLInputElement | null>(null)
const isLoading = ref(false)
const isError = ref(false)
const errorMessage = ref('')
const auditResult = ref<any>(null)

const previewImageUrl = ref<string | null>(null)
const loadingText = ref('Initializing scan...')
const currentTip = ref('')
const elapsedSeconds = ref(0)
const estimatedSeconds = ref(0)
let timerInterval: number

const loadingPhrases = [
  "Scanning room geometry and objects...",
  "Calculating Light Reflectance Values (LRV)...",
  "Analyzing floor-to-wall contrast boundaries...",
  "Checking for harsh window glare...",
  "Mapping shadow patterns and edge linings...",
  "Evaluating furniture visibility and contrast...",
  "Detecting spatial clutter and trip hazards...",
  "Searching for abstract or illegible signage..."
]

const educationalTips = [
  "Did you know? High-contrast patterns on rugs can look like moving snakes or deep holes to someone with dementia.",
  "Tip: Simply changing a black toilet seat to a bright color can drastically improve bathroom independence.",
  "Did you know? Clear glass tables are one of the leading causes of collision injuries because they become invisible when depth perception fades.",
  "Tip: Ensure all pathways are well-lit and free of dark shadows, as shadows can be mistaken for physical barriers.",
  "Did you know? Abstract signs like 'Facilities' are confusing. Use literal words like 'Toilet' with a clear picture.",
  "Tip: Keep flooring colors consistent between rooms. A sudden change from a light floor to a dark floor can look like a step down, causing falls.",
  "Did you know? Mirrors can be terrifying for late-stage dementia patients because they no longer recognize their own reflection, believing a stranger is in the room.",
  "Tip: Furniture should contrast sharply with the floor (at least 30 points of Light Reflectance Value) so it is easily seen.",
  "Did you know? Translucent curtains are better than heavy blinds, because harsh striped shadows from blinds can trigger 'gait freezing'.",
  "Tip: Adding a brightly colored baseboard helps visually anchor the wall to the floor, preventing spatial disorientation.",
  "Did you know? Aging eyes with dementia need up to three times more light to see clearly compared to a healthy 20-year-old.",
  "Tip: Use open shelving or glass-front cabinets in the kitchen. 'Out of sight, out of mind' is a literal truth in memory care.",
  "Did you know? Reflections on shiny, polished floors can look like spilled water, causing people with dementia to slip or refuse to walk.",
  "Tip: Place a highly visible, contrasting mat directly in front of the toilet to naturally guide the person and prevent falls.",
  "Did you know? Dementia narrows the visual field, creating 'binocular vision.' Important items must be placed directly in their line of sight to be seen.",
  "Tip: Remove or cover highly patterned wallpaper. Complex patterns can cause visual hallucinations and severe anxiety.",
  "Did you know? Blue and green colors become harder to distinguish as we age. Warm colors like red, orange, and yellow remain highly visible.",
  "Tip: Paint the bedroom door a unique, bright color (like red or yellow) so it easily stands out from all other doors in the hallway.",
  "Did you know? Sharp, dark shadows cast by furniture can look like solid objects or holes on the floor, leading to tripping.",
  "Tip: Disguise exit doors that shouldn't be used by painting them the exact same color as the surrounding walls to reduce wandering.",
  "Did you know? 'Gait freezing' occurs when a person suddenly feels stuck to the floor. It is often triggered by sudden changes in flooring color.",
  "Tip: Serve meals on a solid-colored plate (like red or blue) that contrasts sharply with the food. It has been proven to increase eating by 25%!",
  "Did you know? 3D-looking floor designs, like checkerboard tiles, can appear as actual steps or varying elevations, drastically increasing fall risk.",
  "Tip: Reduce background noise. Hard floors and bare walls bounce sound around, causing auditory confusion. Add soft furnishings to absorb noise.",
  "Did you know? A simple black doormat is often avoided by people with dementia because their brain interprets it as a bottomless pit.",
  "Tip: Ensure light switches contrast strongly against the wall. A white switch on a white wall becomes completely invisible.",
  "Did you know? Sundowning (increased confusion in the late afternoon) can be significantly reduced by turning on bright indoor lights before the sun sets.",
  "Tip: Use matte paint finishes instead of gloss. Glossy walls and shiny surfaces create glare that can be physically painful for aging eyes.",
  "Did you know? People with dementia often walk with a shuffling gait and their heads tilted downward. Keep paths clear and consider low-level lighting.",
  "Tip: Avoid throw rugs altogether. Even low-profile rugs are extreme trip hazards for individuals who shuffle their feet when walking."
]

let phraseInterval: number
let tipInterval: number

const startLoadingAnimation = () => {
  let phraseIndex = 0
  let tipIndex = Math.floor(Math.random() * educationalTips.length)
  currentTip.value = educationalTips[tipIndex] || ''
  loadingText.value = loadingPhrases[phraseIndex] || ''

  phraseInterval = window.setInterval(() => {
    phraseIndex = (phraseIndex + 1) % loadingPhrases.length
    loadingText.value = loadingPhrases[phraseIndex] || ''
  }, 3000)

  tipInterval = window.setInterval(() => {
    tipIndex = (tipIndex + 1) % educationalTips.length
    currentTip.value = educationalTips[tipIndex] || ''
  }, 5000)
}

const stopLoadingAnimation = () => {
  clearInterval(phraseInterval)
  clearInterval(tipInterval)
  clearInterval(timerInterval)
}

// UI State
const videoRef = ref<HTMLVideoElement | null>(null)
const imageRef = ref<HTMLImageElement | null>(null)
const isCameraActive = ref(false)
let mediaStream: MediaStream | null = null

const selectedHazardId = ref<string | null>(null)

const triggerUpload = () => {
  // Programmatically click the hidden file input when the styled "Upload" box is clicked
  fileInput.value?.click()
}

// Client-side image pre-processing: decodes and resizes images to max 1024px before upload.
// Uses hardware-accelerated createImageBitmap where available (which decodes HEIC natively in modern Safari/iOS)
// with an Image() canvas fallback, always outputting a clean baseline JPEG.
const resizeImageForAudit = async (file: File, maxDim = 1024, quality = 0.88): Promise<File> => {
  const isImageCandidate = file.type.startsWith('image/') || 
    /\.(jpe?g|png|webp|heic|heif|bmp)$/i.test(file.name) || 
    file.type === ''

  if (!isImageCandidate || file.type.includes('svg')) {
    return file
  }

  // 1. Try modern createImageBitmap first (hardware decoder, handles HEIC & EXIF rotation on Safari/iOS)
  if (typeof window !== 'undefined' && 'createImageBitmap' in window) {
    try {
      const bmp = await createImageBitmap(file)
      let { width, height } = bmp

      if (width > maxDim || height > maxDim) {
        if (width > height) {
          height = Math.round((height * maxDim) / width)
          width = maxDim
        } else {
          width = Math.round((width * maxDim) / height)
          height = maxDim
        }
      }

      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      if (ctx) {
        ctx.drawImage(bmp, 0, 0, width, height)
        bmp.close()
        const blob = await new Promise<Blob | null>(res => canvas.toBlob(res, 'image/jpeg', quality))
        if (blob) {
          const cleanName = (file.name || 'photo.jpg').replace(/\.[^/.]+$/, '') + '.jpg'
          try {
            return new File([blob], cleanName, { type: 'image/jpeg', lastModified: Date.now() })
          } catch {
            return Object.assign(blob, { name: cleanName }) as unknown as File
          }
        }
      }
    } catch {
      // Fallback to FileReader + Image if createImageBitmap is not supported or fails on raw format
    }
  }

  // 2. Resilient fallback using FileReader (reads data into memory, preventing iOS Safari sandbox disconnects)
  return new Promise((resolve) => {
    const cleanName = (file.name || 'photo.jpg').replace(/\.[^/.]+$/, '') + '.jpg'
    const reader = new FileReader()
    
    reader.onload = () => {
      const img = new Image()
      img.onload = () => {
        let { width, height } = img

        if (width > maxDim || height > maxDim) {
          if (width > height) {
            height = Math.round((height * maxDim) / width)
            width = maxDim
          } else {
            width = Math.round((width * maxDim) / height)
            height = maxDim
          }
        }

        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          resolve(file)
          return
        }

        ctx.drawImage(img, 0, 0, width, height)
        canvas.toBlob((blob) => {
          if (!blob) {
            resolve(file)
            return
          }
          try {
            const processedFile = new File([blob], cleanName, {
              type: 'image/jpeg',
              lastModified: Date.now()
            })
            resolve(processedFile)
          } catch {
            resolve(Object.assign(blob, { name: cleanName }) as unknown as File)
          }
        }, 'image/jpeg', quality)
      }

      img.onerror = () => {
        resolve(file)
      }

      img.src = reader.result as string
    }

    reader.onerror = () => {
      resolve(file)
    }

    reader.readAsDataURL(file)
  })
}

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const rawFile = target?.files?.[0]
  if (!rawFile) return
  
  // Extract EXIF GPS coordinates from photo if present
  extractExifGpsFromBlob(rawFile).then(gps => {
    if (gps && gps.hasGps) {
      resolveLocationByCoords(gps.latitude, gps.longitude, 'exif')
    }
  }).catch(() => {})

  // Create a local object URL so we can instantly show the user their photo as the background
  // of the loading screen while the backend processes it.
  if (previewImageUrl.value) URL.revokeObjectURL(previewImageUrl.value)
  previewImageUrl.value = URL.createObjectURL(rawFile)

  isLoading.value = true
  isError.value = false
  errorMessage.value = ''
  auditResult.value = null
  selectedHazardId.value = null
  
  // Optimize image to prevent server CPU timeouts and "Load failed" network drops
  loadingText.value = 'Preparing image for AI scan...'
  const file = await resizeImageForAudit(rawFile)
  const uploadFileName = (file.name || 'audit_image.jpg').replace(/\.[^/.]+$/, '') + '.jpg'
  
  // Realistic estimated time for optimized scan (~35s on 8 vCPU instance)
  estimatedSeconds.value = 35
  elapsedSeconds.value = 0
  
  // Start the ticking timer
  if (timerInterval) clearInterval(timerInterval)
  timerInterval = window.setInterval(() => {
    elapsedSeconds.value++
  }, 1000)

  startLoadingAnimation()
  
  try {
    let res: Response | null = null
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        const payload = new FormData()
        payload.append('image', file, uploadFileName)
        res = await fetch('/api/audit', {
          method: 'POST',
          body: payload
        })
        break
      } catch (networkErr: any) {
        const isSafariDrop = networkErr?.name === 'TypeError' || 
          networkErr?.message === 'Load failed' || 
          networkErr?.message === 'Failed to fetch' ||
          (networkErr?.message && networkErr.message.includes('network connection was lost'))
        
        if (attempt < 2 && isSafariDrop) {
          loadingText.value = 'Reconnecting to AI vision server...'
          await new Promise(r => setTimeout(r, 1200))
          continue
        }
        throw networkErr
      }
    }
    
    if (!res) {
      throw new Error('Network connection failed. Please check your internet connection and try again.')
    }
    
    if (!res.ok) {
      let serverError = ''
      try {
        const err = await res.json()
        serverError = err.error || err.message || ''
      } catch {
        // Response was not JSON (e.g. 504 HTML timeout or 502 bad gateway)
      }

      if (res.status === 504 || res.status === 408) {
        throw new Error('Analysis timed out. The server took too long to process this photo. Please try a clearer or smaller photo.')
      } else if (res.status === 413) {
        throw new Error('Image file is too large. Please upload an image under 10MB.')
      } else if (res.status === 502 || res.status === 503) {
        throw new Error('The AI vision service is temporarily busy. Please try again in a moment.')
      }
      throw new Error(serverError || `Failed to analyze image (Status ${res.status})`)
    }
    
    const postData = await res.json()
    let data: any = null

    if (postData.is_valid_indoor !== undefined) {
      // Synchronous response mode
      data = postData
    } else if (postData.jobId) {
      // Asynchronous polling mode — finishes POST in <200ms, completely immune to Safari 60s socket drops
      const jobId = postData.jobId
      const maxWaitMs = 180 * 1000 // 3 minutes timeout limit
      const startTime = Date.now()

      while (true) {
        if (Date.now() - startTime > maxWaitMs) {
          throw new Error('Analysis timed out. The server took too long to process this photo. Please try a clearer or smaller photo.')
        }

        await new Promise(r => setTimeout(r, 2000))

        const elapsed = Math.round((Date.now() - startTime) / 1000)
        if (elapsed > 45) {
          loadingText.value = 'Finalizing dementia-friendly contrast & safety suggestions...'
        } else if (elapsed > 25) {
          loadingText.value = 'Evaluating contrast, visual camouflage, and pathway boundaries...'
        } else if (elapsed > 10) {
          loadingText.value = 'Detecting structural elements, doorways, and obstacles...'
        }

        try {
          const pollRes = await fetch(`/api/audit/status/${jobId}`)
          if (!pollRes.ok) {
            continue
          }
          const pollData = await pollRes.json()
          if (pollData.status === 'completed') {
            data = pollData.data
            break
          } else if (pollData.status === 'error') {
            throw new Error(pollData.error || 'The photo check failed. Please try again.')
          }
        } catch (pollErr: any) {
          if (pollErr.message && (pollErr.message.includes('photo check failed') || pollErr.message.includes('timed out'))) {
            throw pollErr
          }
          continue
        }
      }
    } else {
      throw new Error(postData.error || 'Failed to start image analysis.')
    }
    
    if (!data.is_valid_indoor) {
      isError.value = true
      errorMessage.value = "The provided image is not a valid indoor space. NeighbourlyMinds is designed for indoor spaces."
      isLoading.value = false
      stopLoadingAnimation()
      return
    }
    
    auditResult.value = data
    
  } catch (err: any) {
    isError.value = true
    if (err.message === 'Load failed' || err.message === 'Failed to fetch') {
      errorMessage.value = 'Network connection dropped or timed out while analyzing the image. Please try again with a clear photo.'
    } else {
      errorMessage.value = err.message || 'An unexpected error occurred during analysis.'
    }
  } finally {
    isLoading.value = false
    stopLoadingAnimation()
  }
}

const startCamera = async () => {
    try {
        isCameraActive.value = true
        mediaStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        if (videoRef.value) {
            videoRef.value.srcObject = mediaStream
        }
    } catch (err: any) {
        isError.value = true
        errorMessage.value = "Unable to access the camera: " + err.message
        isCameraActive.value = false
    }
}

const stopCamera = () => {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop())
        mediaStream = null
    }
    isCameraActive.value = false
}

const takePhoto = () => {
    if (!videoRef.value) return
    const canvas = document.createElement('canvas')
    const vW = videoRef.value.videoWidth || 1280
    const vH = videoRef.value.videoHeight || 720
    const maxDim = 1024
    let targetW = vW
    let targetH = vH
    if (targetW > maxDim || targetH > maxDim) {
        if (targetW > targetH) {
            targetH = Math.round((targetH * maxDim) / targetW)
            targetW = maxDim
        } else {
            targetW = Math.round((targetW * maxDim) / targetH)
            targetH = maxDim
        }
    }
    canvas.width = targetW
    canvas.height = targetH
    const ctx = canvas.getContext('2d')
    if (ctx) {
        ctx.drawImage(videoRef.value, 0, 0, targetW, targetH)
        canvas.toBlob((blob) => {
            if (blob) {
                stopCamera()
                const file = new File([blob], "camera_capture.jpg", { type: "image/jpeg" })
                const event = { target: { files: [file] } } as unknown as Event
                handleFileUpload(event)
            }
        }, 'image/jpeg', 0.88)
    }
}



// Image Coordinate Mapping State
// To accurately place the pulsing hazard pins over the image, we must track the natural dimensions
// of the uploaded image. We map the AI's bounding box coordinates (which are based on the natural dimensions)
// to percentages so the pins perfectly align no matter what size the CSS scales the image down to.
const imgWidth = ref(1)
const imgHeight = ref(1)

const onImageLoad = () => {
    // Triggered when the annotated result image finishes loading in the DOM
    if (imageRef.value) {
        imgWidth.value = imageRef.value.naturalWidth || 1
        imgHeight.value = imageRef.value.naturalHeight || 1
    }
}

// Manages the state of the interactive hotspots. Only one hazard tooltip is shown at a time.
const toggleHazard = (id: string) => {
    selectedHazardId.value = selectedHazardId.value === id ? null : id
}

// ═══════════════════════════════════════════════════════════════
// ACCESSIBILITY AUDIT & ADVOCACY STATE
// ═══════════════════════════════════════════════════════════════

// Auditor Navigation Tab State
const activeHubTab = ref<'auditor' | 'history'>('auditor')

// Space Type: Private Home Room vs Public Community Space
const spaceType = ref<'private' | 'public'>('private')

// Private Room Specific State
const privateRoomType = ref<string>('Living Room')
const privateRoomName = ref<string>('Main Living Room')
const residentName = ref<string>('')
const residentEmail = ref<string>('')
const privateResidentNotes = ref<string>('')

// Home Renovation & Caregiver Plan Modal State
const showHomeRenovationModal = ref(false)
const renovationSubject = ref('')
const renovationSummary = ref('')
const renovationText = ref('')
const copyRenovationSuccess = ref(false)
const isSavingHomePlan = ref(false)
const homePlanSaved = ref(false)

const councilList = ref<CouncilContact[]>([])
const selectedCouncilName = ref('Melbourne City Council')

// Municipal Geocoder & EXIF State (for Public Spaces)
const geocodedLgaName = ref<string>('City of Melbourne')
const geocodedMethod = ref<'exif' | 'geolocation' | 'preset' | 'default'>('default')
const geocodedCoords = ref<{ lat: number; lng: number } | null>({ lat: -37.8180, lng: 144.9671 })
const isGeocoding = ref(false)
const showLocationPresets = ref(false)
const geocodeBannerMessage = ref('📍 Victorian Municipal LGA: City of Melbourne (Melbourne City Council)')

const fallbackCouncil: CouncilContact = {
  council_name: 'Melbourne City Council',
  ceo_name: 'Dr Alison Leighton',
  mayor_name: 'Cr Nicholas Reece',
  deputy_mayor_name: 'Cr Roshena Campbell',
  telephone: '9658 9658',
  email: 'enquiries@melbourne.vic.gov.au',
  website: 'https://www.melbourne.vic.gov.au',
  postal_address: 'GPO Box 1603',
  postal_suburb: 'MELBOURNE',
  postcode: '3001'
}

const selectedCouncil = computed<CouncilContact>(() => {
  if (councilList.value.length === 0) return fallbackCouncil
  const found = councilList.value.find(
    c => c.council_name.toLowerCase() === selectedCouncilName.value.toLowerCase()
  )
  return found || councilList.value[0] || fallbackCouncil
})

const fetchCouncils = async () => {
  try {
    const res = await fetch('/api/councils/contacts')
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) {
        councilList.value = data
      }
    }
  } catch (e) {
    console.warn('Using offline council fallback directory')
  }
}

/**
 * Resolves Victorian LGA boundary and council contacts by coordinates (PostGIS point-in-polygon)
 */
const resolveLocationByCoords = async (lat: number, lng: number, source: 'exif' | 'geolocation' | 'preset' | 'default') => {
  isGeocoding.value = true
  geocodedCoords.value = { lat, lng }
  geocodedMethod.value = source

  try {
    const res = await fetch(`/api/councils/geocode?lat=${lat}&lng=${lng}`)
    if (res.ok) {
      const data = await res.json()
      if (data && data.council && data.council.council_name) {
        selectedCouncilName.value = data.council.council_name
        geocodedLgaName.value = data.lgaName || data.council.council_name
        
        if (source === 'exif') {
          geocodeBannerMessage.value = `📷 Photo EXIF GPS Resolved: ${data.lgaName} (${lat.toFixed(4)}, ${lng.toFixed(4)})`
        } else if (source === 'geolocation') {
          geocodeBannerMessage.value = `📍 Device GPS Location: ${data.lgaName} (${lat.toFixed(4)}, ${lng.toFixed(4)})`
        } else if (source === 'preset') {
          geocodeBannerMessage.value = `🏛️ Victorian Public Corridor: ${data.lgaName}`
        } else {
          geocodeBannerMessage.value = `📍 Victorian Municipal LGA: ${data.lgaName}`
        }

        // If council contact was matched, ensure it is selected
        if (data.council && !councilList.value.some(c => c.council_name === data.council.council_name)) {
          councilList.value.push(data.council)
        }
        updateEmailDraft()
        return
      }
    }
  } catch (err) {
    console.warn('[Geocoder] Point-in-polygon API unavailable:', err)
  } finally {
    isGeocoding.value = false
  }
}

/**
 * Browser Geolocation trigger
 */
const useCurrentDeviceGps = () => {
  if (!navigator.geolocation) {
    alert('Geolocation is not supported by your browser')
    return
  }
  isGeocoding.value = true
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      resolveLocationByCoords(pos.coords.latitude, pos.coords.longitude, 'geolocation')
    },
    (err) => {
      isGeocoding.value = false
      alert('Unable to retrieve current location: ' + err.message)
    },
    { enableHighAccuracy: true, timeout: 8000 }
  )
}

/**
 * Select from known Victorian public corridor presets
 */
const applyLocationPreset = (preset: (typeof VICTORIAN_PUBLIC_LOCATION_PRESETS)[0]) => {
  locationNameInput.value = preset.name
  facilityTypeInput.value = preset.facilityType
  showLocationPresets.value = false
  resolveLocationByCoords(preset.lat, preset.lng, 'preset')
}

// ═══════════════════════════════════════════════════════════════
// PUBLIC SPATIAL HAZARD TAXONOMY ENGINE
// ═══════════════════════════════════════════════════════════════
const selectedTaxonomyFilter = ref<string>('ALL')

// Barrier statistics computed from audit results
const barrierStats = computed<BarrierStatistic[]>(() => {
  if (!auditResult.value || !auditResult.value.suggestions) return []
  return extractBarrierStatistics(auditResult.value.suggestions)
})

// Unique taxonomy categories present in the current scan
const availableTaxonomyCategories = computed(() => {
  const map = new Map<string, { category: StandardHazardCategory; count: number; icon: string; code: string }>()
  barrierStats.value.forEach(b => {
    const cat = b.category as StandardHazardCategory
    const def = SPATIAL_HAZARD_TAXONOMY[cat] || SPATIAL_HAZARD_TAXONOMY['Low-Contrast Entrance Frame']
    const existing = map.get(cat)
    if (existing) {
      existing.count++
    } else {
      map.set(cat, {
        category: cat,
        count: 1,
        icon: def.icon,
        code: def.code
      })
    }
  })
  return Array.from(map.values())
})

// Two-way interactive hover state between image pins and issue list
const hoveredHazardId = ref<string | null>(null)

// Single active barrier selected for the side inspection card
const selectedBarrierStat = computed<BarrierStatistic | null>(() => {
  if (!selectedHazardId.value) return null
  return barrierStats.value.find(b => b.id === selectedHazardId.value) || null
})

const selectedBarrierIndex = computed(() => {
  if (!selectedHazardId.value) return -1
  return barrierStats.value.findIndex(b => b.id === selectedHazardId.value)
})

const selectNextBarrier = () => {
  if (barrierStats.value.length === 0) return
  const cur = selectedBarrierIndex.value
  const next = (cur + 1) % barrierStats.value.length
  const nextItem = barrierStats.value[next]
  if (nextItem) selectedHazardId.value = nextItem.id
}

const selectPrevBarrier = () => {
  if (barrierStats.value.length === 0) return
  const cur = selectedBarrierIndex.value
  const prev = (cur - 1 + barrierStats.value.length) % barrierStats.value.length
  const prevItem = barrierStats.value[prev]
  if (prevItem) selectedHazardId.value = prevItem.id
}

const selectBarrier = (id: string) => {
  selectedHazardId.value = id
}

const clearSelectedBarrier = () => {
  selectedHazardId.value = null
}

export interface PositionedPin {
  id: string
  index: number
  title: string
  category: string
  detectedLrv: number
  rawX: number
  rawY: number
  styleLeft: string
  styleTop: string
  boxLeft: string
  boxTop: string
  boxWidth: string
  boxHeight: string
  alignRight: boolean
  alignBottom: boolean
  isClustered: boolean
}

/**
 * Intelligent Pin De-overlapping & Spidering Algorithm with Boundary Awareness:
 * Detects pins whose centers collide within proximity threshold in percentage space.
 * Clustered pins are automatically distributed in a radial fan-out ring around their centroid,
 * ensuring each pin has its own clickable footprint, distinct number badge, and zero overlap.
 * Also computes smart boundary alignment flags (alignRight, alignBottom) so tags and tooltips
 * never cut off past the viewer boundaries.
 */
const positionedPins = computed<PositionedPin[]>(() => {
  if (!auditResult.value || !auditResult.value.suggestions) return []
  const sugs = auditResult.value.suggestions
  const w = imgWidth.value || 1
  const h = imgHeight.value || 1
  const stats = barrierStats.value

  const rawPins = sugs.map((sug: any, idx: number) => {
    const rawX = ((sug.location_box[0] + sug.location_box[2] / 2) / w) * 100
    const rawY = ((sug.location_box[1] + sug.location_box[3] / 2) / h) * 100
    const stat = stats[idx]

    // Safe clamped bounding box coordinates within [1%, 98%]
    const boxXPercent = Math.max(1, Math.min(96, (sug.location_box[0] / w) * 100))
    const boxYPercent = Math.max(1, Math.min(96, (sug.location_box[1] / h) * 100))
    const boxWPercent = Math.max(2, Math.min(99 - boxXPercent, (sug.location_box[2] / w) * 100))
    const boxHPercent = Math.max(2, Math.min(99 - boxYPercent, (sug.location_box[3] / h) * 100))

    // Determine smart boundary alignment:
    // If box right edge or center is in the right half of the image (> 55%), align tag to the right edge of the box
    // so it renders inwards to the left and never cuts off against the container border
    const alignRight = (boxXPercent + boxWPercent) > 55 || rawX > 52
    // If box top is near the top edge (< 10%), place tag below the box instead of above
    const alignBottom = boxYPercent < 10

    return {
      id: sug.id,
      index: idx,
      title: stat ? stat.title : (sug.title || `Issue #${idx + 1}`),
      category: stat ? stat.category : (sug.category || 'Environmental Barrier'),
      detectedLrv: stat ? stat.detectedLrv : Math.round(Number(sug.lrv_score || sug.lrv || 15)),
      rawX,
      rawY,
      boxLeft: boxXPercent.toFixed(2) + '%',
      boxTop: boxYPercent.toFixed(2) + '%',
      boxWidth: boxWPercent.toFixed(2) + '%',
      boxHeight: boxHPercent.toFixed(2) + '%',
      alignRight,
      alignBottom
    }
  })

  // Distance threshold for clustering (in image percentage space)
  const THRESHOLD = 5.5

  // Group pins into clusters using proximity graph
  const clusters: (typeof rawPins)[] = []
  const visited = new Set<number>()

  for (let i = 0; i < rawPins.length; i++) {
    if (visited.has(i)) continue
    const cluster = [rawPins[i]]
    visited.add(i)

    for (let j = i + 1; j < rawPins.length; j++) {
      if (visited.has(j)) continue
      const dx = rawPins[i].rawX - rawPins[j].rawX
      const dy = rawPins[i].rawY - rawPins[j].rawY
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < THRESHOLD) {
        cluster.push(rawPins[j])
        visited.add(j)
      }
    }
    clusters.push(cluster)
  }

  const finalPins: PositionedPin[] = []

  clusters.forEach(cluster => {
    const M = cluster.length
    const centroidX = cluster.reduce((sum: number, p: any) => sum + p.rawX, 0) / M
    const centroidY = cluster.reduce((sum: number, p: any) => sum + p.rawY, 0) / M

    if (M === 1) {
      finalPins.push({
        ...(cluster[0] as any),
        styleLeft: `clamp(34px, ${centroidX.toFixed(2)}%, calc(100% - 34px))`,
        styleTop: `clamp(24px, ${centroidY.toFixed(2)}%, calc(100% - 24px))`,
        isClustered: false
      })
    } else {
      // Fan out radially around centroid to prevent overlap
      const R = M === 2 ? 26 : (M <= 4 ? 32 : 38)
      cluster.forEach((p: any, k: number) => {
        const angle = (2 * Math.PI * k) / M - Math.PI / 2
        const offsetXPx = Math.round(R * Math.cos(angle))
        const offsetYPx = Math.round(R * Math.sin(angle))
        finalPins.push({
          ...p,
          styleLeft: `clamp(34px, calc(${centroidX.toFixed(2)}% + ${offsetXPx}px), calc(100% - 34px))`,
          styleTop: `clamp(24px, calc(${centroidY.toFixed(2)}% + ${offsetYPx}px), calc(100% - 24px))`,
          isClustered: true
        })
      })
    }
  })

  // Preserve original ordering so indices 1..N match the side list
  return finalPins.sort((a, b) => a.index - b.index)
})

// Pins filtered by active taxonomy category
const filteredPositionedPins = computed<PositionedPin[]>(() => {
  if (selectedTaxonomyFilter.value === 'ALL') {
    return positionedPins.value
  }
  return positionedPins.value.filter(p => p.category === selectedTaxonomyFilter.value)
})

// ═══════════════════════════════════════════════════════════════
// CIVIC FEEDBACK & ASSESSMENT HISTORY TRACKER STATE
// ═══════════════════════════════════════════════════════════════
const civicReportsList = ref<CivicReportItem[]>([])
const historyStatusFilter = ref<string>('ALL')
const historySearchQuery = ref<string>('')
const isLoadingHistory = ref<boolean>(false)
const selectedHistoryReport = ref<CivicReportItem | null>(null)
const showHistoryDetailModal = ref<boolean>(false)

const loadCivicReports = async () => {
  isLoadingHistory.value = true
  try {
    const list = await fetchCivicReports(historyStatusFilter.value, historySearchQuery.value)
    civicReportsList.value = list
  } finally {
    isLoadingHistory.value = false
  }
}

const viewSubmissionDetail = (report: CivicReportItem) => {
  selectedHistoryReport.value = report
  showHistoryDetailModal.value = true
}

const copyHistorySuccess = ref(false)

const copyHistoryDetail = async () => {
  if (!selectedHistoryReport.value) return
  try {
    await navigator.clipboard.writeText(selectedHistoryReport.value.email_body)
    copyHistorySuccess.value = true
    setTimeout(() => { copyHistorySuccess.value = false }, 2500)
  } catch (e) {
    // clipboard fallback
  }
}

const printHistoryDetail = () => {
  window.print()
}

const emailHistoryDetail = () => {
  if (!selectedHistoryReport.value) return
  const mailto = `mailto:${encodeURIComponent(selectedHistoryReport.value.council_email || '')}?subject=${encodeURIComponent(selectedHistoryReport.value.email_subject)}&body=${encodeURIComponent(selectedHistoryReport.value.email_body)}`
  window.open(mailto, '_blank')
}

const simulateCouncilAcknowledge = async (refId: string) => {
  await updateReportStatus(refId, 'ACKNOWLEDGED')
  const item = civicReportsList.value.find(r => r.reference_id === refId)
  if (item) item.status = 'ACKNOWLEDGED'
  if (selectedHistoryReport.value && selectedHistoryReport.value.reference_id === refId) {
    selectedHistoryReport.value.status = 'ACKNOWLEDGED'
  }
}

// Public Space Details & Advocacy Inputs
const locationNameInput = ref('City Public Library')
const facilityTypeInput = ref('Public Hallway & Main Entrance')
const senderNameInput = ref('')
const senderEmailInput = ref('')
const customNotesInput = ref('')
const emailSubject = ref('')
const emailBody = ref('')
const copySuccess = ref(false)
const showEmailModal = ref(false)
const isSavingReport = ref(false)
const publicReportSaved = ref(false)

const updateEmailDraft = () => {
  const draft = generateCouncilEmailDraft({
    recipientCouncil: selectedCouncil.value,
    senderName: senderNameInput.value,
    senderEmail: senderEmailInput.value,
    locationName: locationNameInput.value,
    facilityType: facilityTypeInput.value,
    barriers: barrierStats.value,
    customNotes: customNotesInput.value
  })
  emailSubject.value = draft.subject
  emailBody.value = draft.body
}

const openAdvocacyModal = () => {
  publicReportSaved.value = false
  updateEmailDraft()
  showEmailModal.value = true
}

const onCouncilChange = () => {
  updateEmailDraft()
}

const openMailClient = () => {
  const mailtoUrl = `mailto:${encodeURIComponent(selectedCouncil.value.email || '')}?subject=${encodeURIComponent(emailSubject.value)}&body=${encodeURIComponent(emailBody.value)}`
  window.open(mailtoUrl, '_blank')
}

const copyEmailBody = async () => {
  try {
    const textToCopy = `To: ${selectedCouncil.value.council_name} <${selectedCouncil.value.email || 'enquiries@vic.gov.au'}>\nSubject: ${emailSubject.value}\n\n${emailBody.value}`
    await navigator.clipboard.writeText(textToCopy)
    copySuccess.value = true
    setTimeout(() => { copySuccess.value = false }, 2500)
  } catch (e) {
    // clipboard fallback
  }
}

const savePublicReportToHistory = async () => {
  isSavingReport.value = true
  try {
    const fallbackRef = `AUDIT-${Date.now().toString(36).toUpperCase()}`
    const newRecord: CivicReportItem = {
      id: Date.now(),
      reference_id: fallbackRef,
      space_type: 'public',
      council_name: selectedCouncil.value.council_name,
      council_email: selectedCouncil.value.email || 'enquiries@vic.gov.au',
      sender_name: senderNameInput.value || 'Community Member',
      sender_email: senderEmailInput.value || '',
      location_name: locationNameInput.value || 'Public Facility',
      facility_type: facilityTypeInput.value || 'Public Hallway',
      barrier_summary: barrierStats.value,
      barrier_count: barrierStats.value.length,
      email_subject: emailSubject.value,
      email_body: emailBody.value,
      status: 'SAVED',
      created_at: new Date().toISOString()
    }

    try {
      const res = await fetch('/api/councils/send-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          spaceType: 'public',
          councilName: newRecord.council_name,
          councilEmail: newRecord.council_email,
          senderName: newRecord.sender_name,
          senderEmail: newRecord.sender_email,
          locationName: newRecord.location_name,
          barrierSummary: newRecord.barrier_summary,
          emailSubject: newRecord.email_subject,
          emailBody: newRecord.email_body,
          status: 'SAVED'
        })
      })
      if (res.ok) {
        const data = await res.json()
        if (data && data.referenceId) {
          newRecord.reference_id = data.referenceId
        }
      }
    } catch (e) {
      // offline fallback
    }

    saveReportToLocalHistory(newRecord)
    await loadCivicReports()
    publicReportSaved.value = true
  } finally {
    isSavingReport.value = false
  }
}

// Home Renovation & Caregiver Plan Methods
const updateHomeRenovationPlan = () => {
  const plan = generateHomeRenovationPlan({
    roomName: privateRoomName.value || privateRoomType.value,
    roomType: privateRoomType.value,
    residentName: residentName.value,
    contactEmail: residentEmail.value,
    barriers: barrierStats.value,
    personalNotes: privateResidentNotes.value
  })
  renovationSubject.value = plan.subject
  renovationSummary.value = plan.summary
  renovationText.value = plan.text
}

const openHomeRenovationModal = () => {
  homePlanSaved.value = false
  updateHomeRenovationPlan()
  showHomeRenovationModal.value = true
}

const copyRenovationPlan = async () => {
  try {
    await navigator.clipboard.writeText(renovationText.value)
    copyRenovationSuccess.value = true
    setTimeout(() => { copyRenovationSuccess.value = false }, 2500)
  } catch (e) {
    // clipboard fallback
  }
}

const emailRenovationPlan = () => {
  const mailto = `mailto:?subject=${encodeURIComponent(renovationSubject.value)}&body=${encodeURIComponent(renovationText.value)}`
  window.open(mailto, '_blank')
}

const printRenovationPlan = () => {
  window.print()
}

const saveHomePlanToHistory = async () => {
  isSavingHomePlan.value = true
  try {
    const fallbackRef = `HOME-${Date.now().toString(36).toUpperCase()}`
    const newRecord: CivicReportItem = {
      id: Date.now(),
      reference_id: fallbackRef,
      space_type: 'private',
      council_name: 'Private Residence Assessment',
      council_email: '',
      sender_name: residentName.value || 'Resident / Family',
      sender_email: residentEmail.value || '',
      location_name: privateRoomName.value || privateRoomType.value,
      facility_type: privateRoomType.value,
      barrier_summary: barrierStats.value,
      barrier_count: barrierStats.value.length,
      email_subject: renovationSubject.value,
      email_body: renovationText.value,
      status: 'SAVED',
      created_at: new Date().toISOString()
    }

    try {
      const res = await fetch('/api/councils/send-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          spaceType: 'private',
          councilName: newRecord.council_name,
          councilEmail: '',
          senderName: newRecord.sender_name,
          senderEmail: newRecord.sender_email,
          locationName: newRecord.location_name,
          barrierSummary: newRecord.barrier_summary,
          emailSubject: newRecord.email_subject,
          emailBody: newRecord.email_body,
          status: 'SAVED'
        })
      })
      if (res.ok) {
        const data = await res.json()
        if (data && data.referenceId) {
          newRecord.reference_id = data.referenceId
        }
      }
    } catch (e) {
      // offline fallback
    }

    saveReportToLocalHistory(newRecord)
    await loadCivicReports()
    homePlanSaved.value = true
  } finally {
    isSavingHomePlan.value = false
  }
}

onMounted(() => {
  fetchCouncils()
  loadCivicReports()
  resolveLocationByCoords(-37.8180, 144.9671, 'default')
})

onUnmounted(() => {
    stopLoadingAnimation()
    stopCamera()
    if (previewImageUrl.value) {
        URL.revokeObjectURL(previewImageUrl.value)
    }
})
</script>

<template>
  <div class="auditor-page">
    <header class="page-header" :class="{ 'header-compact': auditResult }">
      <div v-if="!auditResult" class="header-badge-row">
        <span class="env-pill">🔍 Accessibility Environment Auditor</span>
        <span class="env-standards-pill">AS 1428.1 & Dementia Australia Standards</span>
      </div>
      <h1 class="page-title" :class="{ 'title-compact': auditResult }">Room & Space Accessibility Auditor</h1>
      <p v-if="!auditResult" class="page-subtitle">
        Evaluate indoor private home rooms or public community spaces for visual contrast, doorway visibility, and floor glare to create safer, dementia-friendly environments.
      </p>

      <!-- Hub Navigation Tabs -->
      <nav class="hub-tab-bar" aria-label="Auditor Sections">
        <button 
          class="hub-tab-btn" 
          :class="{ 'tab-active': activeHubTab === 'auditor' }" 
          @click="activeHubTab = 'auditor'"
        >
          <span class="tab-icon">🔍</span>
          <span>Accessibility Auditor</span>
          <span v-if="auditResult" class="tab-badge">{{ auditResult.barriers_found }} Hazards</span>
        </button>
        <button 
          class="hub-tab-btn" 
          :class="{ 'tab-active': activeHubTab === 'history' }" 
          @click="activeHubTab = 'history'"
        >
          <span class="tab-icon">📜</span>
          <span>Audit & Feedback History</span>
          <span class="tab-badge-counter" :class="{ 'badge-highlight': civicReportsList.length > 0 }">{{ civicReportsList.length }}</span>
        </button>
      </nav>
    </header>

    <!-- ═══════════════════════════════════════════════════════════════ -->
    <!-- TAB 1: ACCESSIBILITY AUDITOR WORKSPACE -->
    <!-- ═══════════════════════════════════════════════════════════════ -->
    <div v-if="activeHubTab === 'auditor'">
      
      <!-- Space Type Selector: Private Home vs Public Space (Pre-upload setup) -->
      <div v-if="!auditResult" class="space-type-container">
        <div class="space-type-selector" role="radiogroup" aria-label="Select space category">
          <button 
            type="button" 
            class="space-type-btn" 
            :class="{ 'btn-selected': spaceType === 'private' }" 
            @click="spaceType = 'private'"
            role="radio"
            :aria-checked="spaceType === 'private'"
          >
            <div class="space-btn-icon">🏠</div>
            <div class="space-btn-content">
              <span class="space-btn-title">Private Home Room</span>
              <span class="space-btn-desc">Personal residence: bedroom, living room, hallway, bathroom, kitchen</span>
            </div>
          </button>
          <button 
            type="button" 
            class="space-type-btn" 
            :class="{ 'btn-selected': spaceType === 'public' }" 
            @click="spaceType = 'public'"
            role="radio"
            :aria-checked="spaceType === 'public'"
          >
            <div class="space-btn-icon">🏛️</div>
            <div class="space-btn-content">
              <span class="space-btn-title">Public Community Space</span>
              <span class="space-btn-desc">Libraries, council venues, public hallways, community centres</span>
            </div>
          </button>
        </div>
      </div>

      <!-- Option A: Private Home Room Banner & Room Type Selector (Pre-upload setup) -->
      <section v-if="!auditResult && spaceType === 'private'" class="private-home-banner" aria-label="Home Assessment Configuration">
        <div class="home-banner-top">
          <div class="home-banner-title-group">
            <span class="home-icon">🏠</span>
            <div>
              <h3 class="home-headline">Private Residence Room Assessment</h3>
              <p class="home-subtext">Identifies contrast boundaries, specular reflections, and trip hazards to provide actionable adjustments for family caregivers, occupational therapists, and home renovation experts.</p>
            </div>
          </div>
        </div>
        <div class="home-room-selector-row">
          <label class="room-selector-label"><strong>Room Type:</strong></label>
          <div class="room-type-chips">
            <button 
              v-for="rt in ['Living Room', 'Hallway', 'Bedroom', 'Bathroom', 'Kitchen', 'Entrance']" 
              :key="rt"
              type="button"
              class="room-chip"
              :class="{ 'chip-active': privateRoomType === rt }"
              @click="privateRoomType = rt; if(!privateRoomName || privateRoomName === 'Living Room' || privateRoomName === 'Hallway' || privateRoomName === 'Bedroom' || privateRoomName === 'Bathroom' || privateRoomName === 'Kitchen' || privateRoomName === 'Entrance') privateRoomName = rt"
            >
              {{ rt }}
            </button>
          </div>
          <div class="room-custom-input-group">
            <input 
              v-model="privateRoomName" 
              class="form-control-sm" 
              placeholder="Custom room label (e.g. Master Bedroom)"
            />
          </div>
        </div>
      </section>

      <!-- Option B: Victorian Municipal Council Geocoder Banner (Public spaces only, pre-upload setup) -->
      <section v-else-if="!auditResult" class="municipal-geocoder-banner" aria-label="Municipal Council Resolver">
        <div class="geocoder-info">
          <div class="geocoder-badge-row">
            <span class="geo-shield-icon">🏛️</span>
            <span class="geo-banner-title">Victorian Municipal Council Directory</span>
            <span class="method-tag" :class="'method-' + geocodedMethod">
              {{ geocodedMethod === 'exif' ? '📷 Photo EXIF GPS Resolved' : geocodedMethod === 'geolocation' ? '📍 Device GPS Resolved' : geocodedMethod === 'preset' ? '🏛️ Public Corridor Preset' : '📍 Victorian LGA Boundary' }}
            </span>
          </div>

          <div class="geocoder-council-title">
            <h3 class="council-headline">{{ selectedCouncil.council_name }}</h3>
            <span class="lga-boundary-tag">LGA: {{ geocodedLgaName }}</span>
          </div>

          <div class="geocoder-contacts">
            <span class="contact-item">✉️ <strong>Email:</strong> {{ selectedCouncil.email || 'enquiries@vic.gov.au' }}</span>
            <span class="contact-item">📞 <strong>Phone:</strong> {{ selectedCouncil.telephone }}</span>
            <span class="contact-item">📍 <strong>Suburb:</strong> {{ selectedCouncil.postal_suburb }} ({{ selectedCouncil.postcode }})</span>
            <span v-if="selectedCouncil.mayor_name" class="contact-item">👑 <strong>Mayor:</strong> {{ selectedCouncil.mayor_name }}</span>
          </div>
        </div>

        <div class="geocoder-actions">
          <button class="btn-geo-action" :disabled="isGeocoding" @click="useCurrentDeviceGps" title="Detect your location via GPS">
            <span>🧭</span> {{ isGeocoding ? 'Resolving...' : 'Detect Device GPS' }}
          </button>
          <button class="btn-geo-action btn-geo-preset" @click="showLocationPresets = !showLocationPresets" title="Choose from Victorian public buildings">
            <span>🏛️</span> Public Presets ▾
          </button>
        </div>
      </section>

      <!-- Victorian Public Facility Presets Dropdown Panel (Public spaces only) -->
      <transition name="fade-fast">
        <div v-if="!auditResult && spaceType === 'public' && showLocationPresets" class="presets-dropdown-panel">
          <div class="presets-panel-header">
            <h4>Select Victorian Public Facility:</h4>
            <button class="btn-close-presets" @click="showLocationPresets = false">✕</button>
          </div>
          <div class="preset-chip-list">
            <button 
              v-for="preset in VICTORIAN_PUBLIC_LOCATION_PRESETS" 
              :key="preset.name" 
              class="preset-chip-btn"
              @click="applyLocationPreset(preset)"
            >
              <div class="preset-btn-top">
                <strong>{{ preset.name }}</strong>
                <span class="preset-suburb-tag">{{ preset.suburb }}</span>
              </div>
              <div class="preset-btn-bottom">
                <span>🏛️ {{ preset.council }}</span>
                <span>• {{ preset.facilityType }}</span>
              </div>
            </button>
          </div>
        </div>
      </transition>
      
      <!-- Upload State -->
      <div v-if="!auditResult && !isLoading" class="upload-container">
          
          <div class="pre-upload-tip">
              <span class="tip-icon">💡</span>
              <strong>For best results:</strong> Ensure the space is well-lit and <strong>empty of people</strong>. Take photos of doorway frames, floor-wall transitions, light switches, and high-glare surfaces where depth perception is most challenging!
          </div>
          
          <div v-if="isCameraActive" class="camera-container">
              <video ref="videoRef" autoplay playsinline class="video-preview"></video>
              <div class="camera-actions">
                  <button class="btn-primary" @click="takePhoto">Snap Photo</button>
                  <button class="btn-outline" @click="stopCamera">Cancel</button>
              </div>
          </div>

          <div v-else class="upload-box-wrapper">
              <input 
                  type="file" 
                  ref="fileInput" 
                  accept="image/*" 
                  @change="handleFileUpload" 
                  class="hidden-input"
              />
              <div class="upload-actions">
                  <div class="upload-box" @click="triggerUpload">
                      <div class="upload-icon">📁</div>
                      <h2>Upload a Photo</h2>
                      <p>Select a photo of your {{ spaceType === 'private' ? 'home room (living room, hallway, bedroom, bathroom, kitchen)' : 'public hallway or civic space' }} from your device files.</p>
                  </div>
                  <div class="upload-box" @click="startCamera">
                      <div class="upload-icon">📷</div>
                      <h2>Take a Picture</h2>
                      <p>Use your device camera to capture the room or hallway in real time.</p>
                  </div>
              </div>
          </div>
          
          <div v-if="isError" class="error-banner">
              {{ errorMessage }}
          </div>
      </div>
      
      <!-- Intelligent Loading Overlay -->
      <div v-if="isLoading" class="loading-overlay">
          <div class="loading-backdrop" :style="{ backgroundImage: `url(${previewImageUrl})` }"></div>
          <div class="loading-content">
              
              <div class="scanner-container">
                  <div class="scanner-image-wrapper">
                      <img :src="previewImageUrl || undefined" class="scanner-image" />
                      <div class="scanner-line"></div>
                  </div>
                  <h2 class="loading-text">{{ loadingText }}</h2>
                  
                  <div class="timer-display">
                      <p class="timer-text">
                          <strong>Time elapsed:</strong> {{ elapsedSeconds }}s / <strong>Estimated:</strong> ~{{ estimatedSeconds }}s
                      </p>
                      <p v-if="elapsedSeconds > estimatedSeconds + 15" class="timer-warning">
                          ⚠️ Deep neural network analysis is completing complex room calculations. 
                          Please bear with us, your report will be ready shortly!
                      </p>
                  </div>
              </div>
              
              <div class="tip-card">
                  <div class="tip-header">
                      <span class="tip-icon">💡</span> Tip of the Day
                  </div>
                  <p class="tip-content">{{ currentTip }}</p>
              </div>
              
          </div>
      </div>
      
      <!-- Result State -->
      <div v-if="auditResult" class="result-container">
          
          <div v-if="auditResult.barriers_found === 0" class="success-banner">
              <div class="success-icon">✨</div>
              <h3>Dementia-Friendly Environment!</h3>
              <p>Great job! We couldn't find any major contrast hazards or visual barriers in this photo. This space appears well-designed and accessible for someone with dementia.</p>
          </div>
          
          <div v-else class="hotspot-dashboard">
              <!-- Space Mode Indicator & Quick Switcher -->
              <div class="result-space-badge-row">
                <div class="result-badge-left">
                  <span class="space-mode-pill" :class="spaceType">
                    {{ spaceType === 'private' ? '🏠 Audited as: Private Home (' + (privateRoomName || privateRoomType) + ')' : '🏛️ Audited as: Public Community Space' }}
                  </span>
                  <button class="btn-switch-space" @click="spaceType = spaceType === 'private' ? 'public' : 'private'">
                    Switch to {{ spaceType === 'private' ? 'Public Space' : 'Private Home' }} Mode
                  </button>
                </div>
                <div class="result-badge-right">
                  <button class="btn-quick-history" @click="activeHubTab = 'history'" title="View saved audit records and plans">
                    <span>📜</span> View Audit History ({{ civicReportsList.length }})
                  </button>
                  <button class="btn-new-audit" @click="auditResult = null" title="Upload and analyze another photo">
                    <span>↺</span> Audit New Photo
                  </button>
                </div>
              </div>

              <div class="dashboard-header">
                  <div class="dashboard-header-top">
                      <div class="dashboard-title-group">
                          <h3 class="dashboard-title">{{ spaceType === 'private' ? 'Home Room Accessibility Inspection' : 'Public Space Barrier Inspection' }}</h3>
                          <div class="hazard-badge">
                              <span class="pulse-dot"></span>
                              {{ auditResult.barriers_found }} Hazards Detected
                          </div>
                      </div>
                      <p class="dashboard-subtitle">
                          {{ spaceType === 'private' 
                            ? 'Select any numbered pin on the photo to inspect detected contrast boundaries, specular reflections, and practical renovation recommendations.' 
                            : 'Select any numbered pin on the photo to view its environmental classification, standard compliance, and council advocacy recommendations.' }}
                      </p>
                  </div>

                  <!-- Public Spatial Hazard Taxonomy Filter Chips -->
                  <div class="taxonomy-filter-bar">
                    <span class="filter-label">🏷️ Filter Categories:</span>
                    <div class="filter-chips">
                      <button 
                        class="chip-btn" 
                        :class="{ 'chip-active': selectedTaxonomyFilter === 'ALL' }" 
                        @click="selectedTaxonomyFilter = 'ALL'"
                      >
                        All Hazards ({{ barrierStats.length }})
                      </button>
                      <button 
                        v-for="cat in availableTaxonomyCategories" 
                        :key="cat.category" 
                        class="chip-btn" 
                        :class="{ 'chip-active': selectedTaxonomyFilter === cat.category }" 
                        @click="selectedTaxonomyFilter = cat.category"
                      >
                        <span class="chip-icon">{{ cat.icon }}</span>
                        <span>{{ cat.category }}</span>
                        <span class="chip-count">({{ cat.count }})</span>
                      </button>
                    </div>
                  </div>
              </div>

              <!-- Side-by-side Master-Detail Inspection Layout -->
              <div class="audit-workspace-layout">
                  <!-- Left: Interactive Image Viewer -->
                  <div class="workspace-image-container">
                      <div class="interactive-viewer">
                          <img 
                              :src="auditResult.original_annotated_url" 
                              class="overlay-canvas" 
                              alt="Hazard Map" 
                              ref="imageRef"
                              @load="onImageLoad"
                          />
                          
                          <!-- Hotspot Pins (Filtered by Spatial Taxonomy) -->
                          <div v-for="pin in filteredPositionedPins" :key="pin.id">
                              <!-- Pulse effect around active or hovered pin -->
                              <div v-if="selectedHazardId === pin.id || hoveredHazardId === pin.id"
                                   class="hotspot-pulse"
                                   :style="{
                                       left: pin.styleLeft,
                                       top: pin.styleTop
                                   }">
                              </div>

                              <!-- Numbered warning pin button -->
                              <button class="hotspot-pin"
                                   :class="{
                                       'hotspot-active': selectedHazardId === pin.id,
                                       'hotspot-hovered': hoveredHazardId === pin.id
                                   }"
                                   :style="{
                                       left: pin.styleLeft,
                                       top: pin.styleTop,
                                       zIndex: selectedHazardId === pin.id ? 80 : (hoveredHazardId === pin.id ? 70 : (20 + pin.index))
                                   }"
                                   @click="selectBarrier(pin.id)"
                                   @mouseenter="hoveredHazardId = pin.id"
                                   @mouseleave="hoveredHazardId = null"
                                   :aria-label="`Issue #${pin.index + 1}: ${pin.title}`"
                              >
                                   <span class="pin-icon">⚠️</span>
                                   <span class="pin-number">{{ pin.index + 1 }}</span>
                              </button>
                              
                              <!-- Bounding box highlight only when active or hovered -->
                              <div v-if="selectedHazardId === pin.id || hoveredHazardId === pin.id" 
                                   class="dynamic-box" 
                                   :class="{
                                       'box-active': selectedHazardId === pin.id,
                                       'box-hovered': hoveredHazardId === pin.id && selectedHazardId !== pin.id
                                   }"
                                   :style="{
                                       left: pin.boxLeft,
                                       top: pin.boxTop,
                                       width: pin.boxWidth,
                                       height: pin.boxHeight
                                   }"></div>
                          </div>
                      </div>
                  </div>

                  <!-- Right Side: Inspection Detail & Advocacy Panel -->
                  <div class="workspace-side-panel">
                      <transition name="side-card-fade" mode="out-in">
                          <!-- Case A: A hazard/barrier is actively selected -->
                          <div v-if="selectedBarrierStat" :key="selectedBarrierStat.id" class="side-detail-card card-alert">
                              <!-- Top Navigation & Action Controls Bar -->
                              <div class="side-detail-header">
                                  <div class="side-nav-counter">
                                      <span class="barrier-index-pill">#{{ selectedBarrierIndex + 1 }} of {{ barrierStats.length }}</span>
                                  </div>
                                  <div class="side-header-actions">
                                      <div class="issue-nav-btn-group">
                                          <button class="btn-issue-nav" @click="selectPrevBarrier" title="Previous Issue" aria-label="Previous Issue">◀</button>
                                          <button class="btn-issue-nav" @click="selectNextBarrier" title="Next Issue" aria-label="Next Issue">▶</button>
                                      </div>
                                      <button class="btn-side-close" @click="clearSelectedBarrier" title="Close details" aria-label="Close details">✕</button>
                                  </div>
                              </div>

                              <!-- Category Badge Row -->
                              <div class="side-category-row">
                                  <span class="barrier-cat-pill">
                                      <span class="cat-pill-icon">{{ selectedBarrierStat.icon || '⚠️' }}</span>
                                      {{ selectedBarrierStat.category }}
                                  </span>
                              </div>

                              <h4 class="side-card-title">#{{ selectedBarrierIndex + 1 }}. {{ selectedBarrierStat.title }}</h4>

                              <!-- Scrollable Hazard Detail Body -->
                              <div class="side-card-body-scroll">
                                  <div class="lrv-meter-container">
                                      <div class="lrv-meter-header">
                                          <span class="lrv-val">Observed: <strong>{{ selectedBarrierStat.detectedLrv }}% LRV</strong></span>
                                          <span class="lrv-target">Standard: <strong>{{ selectedBarrierStat.targetLrv }}</strong></span>
                                      </div>
                                      <div class="lrv-meter-bar">
                                          <div class="lrv-meter-fill" :style="{ width: Math.min(selectedBarrierStat.detectedLrv, 100) + '%' }" :class="{'fill-danger': !selectedBarrierStat.isCompliant}"></div>
                                      </div>
                                  </div>

                                  <div class="side-card-body">
                                      <p class="barrier-solution">
                                          <strong>Cognitive Ramp Remedy:</strong> {{ selectedBarrierStat.recommendation }}
                                      </p>
                                  </div>

                                  <!-- Dementia Cognitive Ramification -->
                                  <div v-if="selectedBarrierStat.cognitiveRamification" class="cognitive-impact-card">
                                      <span class="cog-icon">🧠</span>
                                      <div class="cog-text">
                                          <strong>Cognitive Impact (Dementia):</strong>
                                          <span>{{ selectedBarrierStat.cognitiveRamification }}</span>
                                      </div>
                                  </div>

                                  <div class="barrier-citation">
                                      <span class="citation-icon">📜</span>
                                      <span>{{ selectedBarrierStat.citation }}</span>
                                  </div>
                              </div>

                              <div class="side-card-footer">
                                  <button v-if="spaceType === 'private'" class="btn-advocate-primary btn-side-action" @click="openHomeRenovationModal">
                                      <span>🛠️</span> Caregiver & Renovation Details
                                  </button>
                                  <button v-else class="btn-advocate-primary btn-side-action" @click="openAdvocacyModal">
                                      <span>🏛️</span> View Council Feedback Details
                                  </button>
                                  <button class="btn-side-secondary" @click="clearSelectedBarrier">
                                      View All Issues ({{ barrierStats.length }})
                                  </button>
                              </div>
                          </div>

                          <!-- Case B: No hazard selected yet -> Clean overview & issue picker -->
                          <div v-else key="overview" class="side-overview-card">
                              <div class="overview-header-group">
                                  <span class="overview-icon">📋</span>
                                  <div>
                                      <h4 class="overview-heading">Environmental Issues ({{ filteredPositionedPins.length }})</h4>
                                      <p class="overview-instructions">
                                          Click any numbered pin on the photo or select an issue below to inspect its contrast statistics:
                                      </p>
                                  </div>
                              </div>

                              <div class="side-issue-list">
                                  <button 
                                      v-for="b in filteredPositionedPins" 
                                      :key="b.id" 
                                      class="side-issue-item"
                                      :class="{
                                          'item-selected': selectedHazardId === b.id,
                                          'item-hovered': hoveredHazardId === b.id
                                      }"
                                      @click="selectBarrier(b.id)"
                                      @mouseenter="hoveredHazardId = b.id"
                                      @mouseleave="hoveredHazardId = null"
                                  >
                                      <div class="issue-item-left">
                                          <span class="issue-item-number" :class="{'num-selected': selectedHazardId === b.id}">#{{ b.index + 1 }}</span>
                                          <div class="issue-item-texts">
                                              <span class="issue-item-title">{{ b.title }}</span>
                                              <span class="issue-item-category">{{ b.category }}</span>
                                          </div>
                                      </div>
                                      <span class="issue-item-lrv">{{ b.detectedLrv }}% LRV</span>
                                  </button>
                              </div>

                              <div class="side-advocacy-cta">
                                  <div class="side-advocacy-info">
                                      <span class="advocacy-pill-sm">{{ spaceType === 'private' ? '🏠 Home Renovation Plan' : '🏛️ Community Advocacy Feedback' }}</span>
                                      <p class="side-advocacy-sub">
                                          {{ spaceType === 'private' 
                                            ? 'Actionable specifications ready to share with family caregivers, occupational therapists, or home renovation experts.' 
                                            : 'Review official council contacts and polite advocacy draft to send directly to ' + selectedCouncil.council_name + '.' }}
                                      </p>
                                  </div>
                                  <button v-if="spaceType === 'private'" class="btn-advocate-primary btn-full-width" @click="openHomeRenovationModal">
                                      <span>🛠️</span> View Caregiver & Renovation Details
                                  </button>
                                  <button v-else class="btn-advocate-primary btn-full-width" @click="openAdvocacyModal">
                                      <span>🏛️</span> View Council Feedback Details
                                  </button>
                              </div>
                          </div>
                      </transition>
                  </div>
              </div>
          </div>

          <div class="disclaimer-banner">
              <strong>Disclaimer:</strong> This AI analysis is an assistive tool and may not be 100% accurate. It may occasionally miss hazards or misidentify objects due to lighting or image quality. Always consult with a certified occupational therapist or healthcare professional for critical home modifications.
          </div>
          
          <div class="dashboard-footer">
              <button class="btn-premium reset-btn" @click="auditResult = null">
                  <span class="btn-icon">↺</span> Analyze Another Room
              </button>
          </div>
      </div>

      <!-- Home Renovation & Caregiver Modification Plan Modal (Private Rooms) -->
      <transition name="modal-fade">
        <div v-if="showHomeRenovationModal" class="modal-backdrop" @click.self="showHomeRenovationModal = false">
          <div class="advocacy-modal-dialog">
            <div class="modal-header">
              <div class="modal-title-group">
                <div class="modal-pill">🏠 Home Accessibility & Caregiver Hub</div>
                <h3 class="modal-title">Home Renovation & Caregiver Action Plan</h3>
                <p class="modal-desc">
                  Environmental modifications and luminance contrast specifications prepared for family caregivers, occupational therapists, and home renovation contractors.
                </p>
              </div>
              <button class="btn-modal-close" @click="showHomeRenovationModal = false" aria-label="Close modal">✕</button>
            </div>

            <div class="modal-body">
              <!-- Room & Resident inputs -->
              <div class="form-grid-two">
                <div class="form-group">
                  <label for="room-name-modal"><strong>Room / Space Assessed:</strong></label>
                  <input id="room-name-modal" v-model="privateRoomName" @input="updateHomeRenovationPlan" class="form-control" placeholder="e.g. Living Room, Main Hallway" />
                </div>
                <div class="form-group">
                  <label for="room-type-modal"><strong>Room Type:</strong></label>
                  <select id="room-type-modal" v-model="privateRoomType" @change="updateHomeRenovationPlan" class="form-control">
                    <option v-for="rt in ['Living Room', 'Hallway', 'Bedroom', 'Bathroom', 'Kitchen', 'Entrance', 'Dining Room', 'Other']" :key="rt" :value="rt">
                      {{ rt }}
                    </option>
                  </select>
                </div>
              </div>

              <div class="form-grid-two">
                <div class="form-group">
                  <label for="resident-name-modal"><strong>Resident / Homeowner Name:</strong></label>
                  <input id="resident-name-modal" v-model="residentName" @input="updateHomeRenovationPlan" class="form-control" placeholder="e.g. Resident Name (Optional)" />
                </div>
                <div class="form-group">
                  <label for="resident-email-modal"><strong>Contact Email:</strong></label>
                  <input id="resident-email-modal" v-model="residentEmail" @input="updateHomeRenovationPlan" class="form-control" placeholder="e.g. contact@example.com (Optional)" />
                </div>
              </div>

              <div class="form-group">
                <label for="resident-notes-modal"><strong>Personal Observations & Daily Difficulties:</strong></label>
                <input id="resident-notes-modal" v-model="privateResidentNotes" @input="updateHomeRenovationPlan" class="form-control" placeholder="e.g. Hesitates at the doorway threshold in evening light; struggles to locate light switch..." />
              </div>

              <!-- Plan Textarea Preview -->
              <div class="email-preview-box">
                <div class="email-preview-header">
                  <div>
                    <span class="preview-badge">Renovation & Caregiver Checklist</span>
                    <strong>Subject:</strong> {{ renovationSubject }}
                  </div>
                  <button class="btn-copy-sm" @click="copyRenovationPlan" title="Copy to clipboard">
                    {{ copyRenovationSuccess ? '✓ Copied Details!' : '📋 Copy Details' }}
                  </button>
                </div>
                <textarea v-model="renovationText" rows="12" class="email-textarea"></textarea>
              </div>

              <div class="guideline-callout">
                <span class="callout-icon">💡</span>
                <span>This plan provides specific luminance contrast (LRV) targets and glare elimination guidelines following the <strong>Dementia Australia Environmental Design Toolkit</strong> and <strong>AS 1428.1</strong>. Provide this to your builder, painter, or occupational therapist to make physical home modifications.</span>
              </div>

              <!-- Success Confirmation Banner with Direct Link to History -->
              <div v-if="homePlanSaved" class="saved-history-banner">
                <div class="saved-banner-text">
                  <span class="saved-banner-icon">✅</span>
                  <div>
                    <strong>Plan Saved to Audit History!</strong>
                    <span>This plan is stored in your <strong>Audit & Feedback History</strong> so you can view, print, or share it anytime.</span>
                  </div>
                </div>
                <button class="btn-goto-history" @click="showHomeRenovationModal = false; activeHubTab = 'history'">
                  Open in History Tab ➔
                </button>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-outline" @click="showHomeRenovationModal = false">Close</button>
              <button class="btn-secondary" @click="printRenovationPlan" title="Print plan or save as PDF">
                <span>🖨️</span> Print / PDF
              </button>
              <button class="btn-secondary" @click="emailRenovationPlan" title="Open in personal mail client">
                <span>✉️</span> Open in Mail App
              </button>
              <button v-if="!homePlanSaved" class="btn-primary" :disabled="isSavingHomePlan" @click="saveHomePlanToHistory">
                <span v-if="isSavingHomePlan">Saving...</span>
                <span v-else>💾 Save to Audit History</span>
              </button>
              <button v-else class="btn-primary btn-saved-history-link" @click="showHomeRenovationModal = false; activeHubTab = 'history'">
                <span>📜</span> View in History Tab ➔
              </button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Victorian Council Accessibility Email Generator Modal (Public Spaces) -->
      <transition name="modal-fade">
        <div v-if="showEmailModal" class="modal-backdrop" @click.self="showEmailModal = false">
          <div class="advocacy-modal-dialog">
            <div class="modal-header">
              <div class="modal-title-group">
                <div class="modal-pill">🏛️ Victorian Civic Hub</div>
                <h3 class="modal-title">Council Accessibility Feedback Details</h3>
                <p class="modal-desc">
                  Polite advocacy draft and council contact details citing AS 1428.1 & Victorian Dementia-Friendly Communities Policy.
                </p>
              </div>
              <button class="btn-modal-close" @click="showEmailModal = false" aria-label="Close modal">✕</button>
            </div>

            <div class="modal-body">
              <!-- Council Resolution Card -->
              <div class="council-selector-card">
                <div class="form-row">
                  <div class="form-group flex-2">
                    <label for="council-select"><strong>Local Municipal Council:</strong></label>
                    <select id="council-select" v-model="selectedCouncilName" @change="onCouncilChange" class="form-control">
                      <option v-for="c in councilList" :key="c.council_name" :value="c.council_name">
                        {{ c.council_name }} ({{ c.postal_suburb }}, {{ c.postcode }})
                      </option>
                      <option v-if="councilList.length === 0" value="Melbourne City Council">
                        Melbourne City Council (MELBOURNE, 3001)
                      </option>
                    </select>
                  </div>
                  <div class="form-group flex-1">
                    <label><strong>Official Email:</strong></label>
                    <div class="read-only-pill">{{ selectedCouncil.email || 'enquiries@vic.gov.au' }}</div>
                  </div>
                </div>

                <div class="council-meta-row">
                  <span><strong>CEO:</strong> {{ selectedCouncil.ceo_name || 'Municipal Officer' }}</span>
                  <span v-if="selectedCouncil.mayor_name"><strong>Mayor:</strong> {{ selectedCouncil.mayor_name }}</span>
                  <span><strong>Phone:</strong> {{ selectedCouncil.telephone }}</span>
                  <span><strong>Suburb:</strong> {{ selectedCouncil.postal_suburb }}</span>
                </div>
              </div>

              <!-- Location & Sender Inputs -->
              <div class="form-grid-two">
                <div class="form-group">
                  <label for="loc-name"><strong>Public Facility / Corridor Name:</strong></label>
                  <input id="loc-name" v-model="locationNameInput" @input="updateEmailDraft" class="form-control" placeholder="e.g. Carlton Library Public Hallway" />
                </div>
                <div class="form-group">
                  <label for="fac-type"><strong>Facility Type:</strong></label>
                  <input id="fac-type" v-model="facilityTypeInput" @input="updateEmailDraft" class="form-control" placeholder="e.g. Municipal Community Centre" />
                </div>
              </div>

              <div class="form-grid-two">
                <div class="form-group">
                  <label for="sender-name"><strong>Your Full Name:</strong></label>
                  <input id="sender-name" v-model="senderNameInput" @input="updateEmailDraft" class="form-control" placeholder="e.g. Your Name (Optional)" />
                </div>
                <div class="form-group">
                  <label for="sender-email"><strong>Your Contact Email:</strong></label>
                  <input id="sender-email" v-model="senderEmailInput" @input="updateEmailDraft" class="form-control" placeholder="e.g. your.email@example.com" />
                </div>
              </div>

              <div class="form-group">
                <label for="custom-notes"><strong>Personal Observations / Community Notes:</strong></label>
                <input id="custom-notes" v-model="customNotesInput" @input="updateEmailDraft" class="form-control" placeholder="Optional notes describing confusion or glare experienced..." />
              </div>

              <!-- Email Draft Preview -->
              <div class="email-preview-box">
                <div class="email-preview-header">
                  <div>
                    <span class="preview-badge">Polite Recommendation Draft</span>
                    <strong>Subject:</strong> {{ emailSubject }}
                  </div>
                  <button class="btn-copy-sm" @click="copyEmailBody" title="Copy to clipboard">
                    {{ copySuccess ? '✓ Copied Details!' : '📋 Copy Draft & Contacts' }}
                  </button>
                </div>
                <textarea v-model="emailBody" rows="12" class="email-textarea"></textarea>
              </div>

              <div class="guideline-callout">
                <span class="callout-icon">💡</span>
                <span><strong>You send this email directly:</strong> Copy the prepared draft above or click <strong>Open in Mail App</strong> to open your email client with the council's address and report text pre-filled.</span>
              </div>

              <!-- Success Confirmation Banner with Direct Link to History -->
              <div v-if="publicReportSaved" class="saved-history-banner">
                <div class="saved-banner-text">
                  <span class="saved-banner-icon">✅</span>
                  <div>
                    <strong>Draft Saved to Audit History!</strong>
                    <span>Your council advocacy draft is recorded in the <strong>Audit & Feedback History</strong> tab.</span>
                  </div>
                </div>
                <button class="btn-goto-history" @click="showEmailModal = false; activeHubTab = 'history'">
                  Open in History Tab ➔
                </button>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-outline" @click="showEmailModal = false">Close</button>
              <button class="btn-secondary" @click="openMailClient">
                <span>📬</span> Open in Mail App
              </button>
              <button v-if="!publicReportSaved" class="btn-primary" :disabled="isSavingReport" @click="savePublicReportToHistory">
                <span v-if="isSavingReport">Saving...</span>
                <span v-else>💾 Save to Audit History</span>
              </button>
              <button v-else class="btn-primary btn-saved-history-link" @click="showEmailModal = false; activeHubTab = 'history'">
                <span>📜</span> View in History Tab ➔
              </button>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════ -->
    <!-- TAB 2: AUDIT & FEEDBACK HISTORY TRACKER -->
    <!-- ═══════════════════════════════════════════════════════════════ -->
    <div v-else-if="activeHubTab === 'history'" class="civic-history-container">
      <div class="history-hero-header">
        <div class="history-badge">📜 Audit Records</div>
        <h2 class="history-title">Audit & Feedback History</h2>
        <p class="history-subtitle">
          Permanent log of room accessibility assessments, caregiver renovation plans, and council feedback drafts.
        </p>
      </div>

      <!-- Search and Status Filter Bar -->
      <div class="history-controls-card">
        <div class="history-search-box">
          <span class="search-icon">🔍</span>
          <input 
            v-model="historySearchQuery" 
            @input="loadCivicReports" 
            class="history-search-input" 
            placeholder="Search by Space, Council, or Reference ID..." 
          />
          <button v-if="historySearchQuery" class="clear-search-btn" @click="historySearchQuery = ''; loadCivicReports()">✕</button>
        </div>

        <div class="history-filter-pills">
          <button 
            class="hist-filter-pill" 
            :class="{ 'pill-active': historyStatusFilter === 'ALL' }" 
            @click="historyStatusFilter = 'ALL'; loadCivicReports()"
          >
            All Records ({{ civicReportsList.length }})
          </button>
          <button 
            class="hist-filter-pill" 
            :class="{ 'pill-active': historyStatusFilter === 'SAVED' }" 
            @click="historyStatusFilter = 'SAVED'; loadCivicReports()"
          >
            💾 Saved Plans
          </button>
          <button 
            class="hist-filter-pill" 
            :class="{ 'pill-active': historyStatusFilter === 'ACKNOWLEDGED' }" 
            @click="historyStatusFilter = 'ACKNOWLEDGED'; loadCivicReports()"
          >
            ✔️ Acknowledged
          </button>
          <button class="btn-refresh-history" @click="loadCivicReports" title="Refresh history list">
            🔄 Refresh
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="isLoadingHistory" class="history-loading-box">
        <div class="spinner"></div>
        <p>Loading assessment records...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="civicReportsList.length === 0" class="history-empty-card">
        <div class="empty-icon">📭</div>
        <h3>No Assessment Records Found</h3>
        <p v-if="historySearchQuery || historyStatusFilter !== 'ALL'">
          No saved reports match your search or filter. Try clearing the filter or search term.
        </p>
        <p v-else>
          No accessibility reports or renovation plans recorded yet. Audit a room to generate your first plan or feedback draft!
        </p>
        <button class="btn-primary" @click="activeHubTab = 'auditor'">
          🔍 Go to Accessibility Auditor
        </button>
      </div>

      <!-- Submissions Cards Grid -->
      <div v-else class="history-cards-grid">
        <div v-for="report in civicReportsList" :key="report.reference_id" class="history-report-card">
          <div class="report-card-top">
            <div class="ref-badge-group">
              <span class="ref-pill">{{ report.reference_id }}</span>
              <span class="space-type-tag" :class="report.space_type || 'public'">
                {{ report.space_type === 'private' ? '🏠 Private Home' : '🏛️ Public Space' }}
              </span>
              <span class="status-badge" :class="'status-' + (report.status || 'SAVED').toLowerCase()">
                {{ (report.status || 'SAVED').replace('_', ' ') }}
              </span>
            </div>
            <div class="report-timestamp">
              <span>📅 {{ formatReportDate(report.created_at) }}</span>
            </div>
          </div>

          <div class="report-card-main">
            <h3 class="report-council-name">
              {{ report.space_type === 'private' ? '🏠 ' + (report.location_name || 'Home Room') : '🏛️ ' + report.council_name }}
            </h3>
            <p v-if="report.space_type !== 'private' && report.council_email" class="report-email-to">
              Destination: <strong>{{ report.council_email }}</strong>
            </p>
            <p v-else class="report-email-to">
              Intended for: <strong>Caregiver / Home Renovation Expert</strong>
            </p>
            <p class="report-location">
              📍 <strong>{{ report.location_name }}</strong> 
              <span v-if="report.facility_type" class="facility-badge">{{ report.facility_type }}</span>
            </p>
            
            <div class="report-barriers-row">
              <span class="barrier-count-badge">⚠️ {{ report.barrier_count || (report.barrier_summary && report.barrier_summary.length) || 1 }} Hazards Identified</span>
              <div class="barrier-mini-pills">
                <span v-for="(b, idx) in (report.barrier_summary || []).slice(0, 3)" :key="idx" class="mini-cat-pill">
                  {{ b.category || b.title || 'Barrier' }}
                </span>
                <span v-if="(report.barrier_summary || []).length > 3" class="mini-cat-more">
                  +{{ report.barrier_summary.length - 3 }} more
                </span>
              </div>
            </div>
          </div>

          <div class="report-card-actions">
            <button class="btn-history-view" @click="viewSubmissionDetail(report)">
              <span>📄</span> View Full Plan / Letter
            </button>
            <button 
              v-if="report.status !== 'ACKNOWLEDGED'" 
              class="btn-history-ack" 
              @click="simulateCouncilAcknowledge(report.reference_id)"
              title="Mark this report as acknowledged"
            >
              <span>✔️</span> Mark Acknowledged
            </button>
          </div>
        </div>
      </div>

      <!-- Historical Record Detail Modal -->
      <transition name="modal-fade">
        <div v-if="showHistoryDetailModal && selectedHistoryReport" class="modal-backdrop" @click.self="showHistoryDetailModal = false">
          <div class="history-detail-dialog">
            <div class="modal-header">
              <div>
                <div class="modal-pill">{{ selectedHistoryReport.space_type === 'private' ? '🏠 Home Renovation Plan' : '🏛️ Council Feedback Record' }}</div>
                <h3 class="modal-title">{{ selectedHistoryReport.reference_id }}</h3>
                <p class="modal-desc">
                  Recorded on {{ formatReportDate(selectedHistoryReport.created_at) }}.
                </p>
              </div>
              <button class="btn-modal-close" @click="showHistoryDetailModal = false">✕</button>
            </div>

            <div class="modal-body">
              <div class="history-meta-banner">
                <div class="meta-item">
                  <strong>Type:</strong>
                  <span>{{ selectedHistoryReport.space_type === 'private' ? 'Private Home Room' : 'Public Community Space' }}</span>
                </div>
                <div v-if="selectedHistoryReport.space_type !== 'private'" class="meta-item">
                  <strong>Council:</strong>
                  <span>{{ selectedHistoryReport.council_name }} ({{ selectedHistoryReport.council_email }})</span>
                </div>
                <div class="meta-item">
                  <strong>Assessed Space:</strong>
                  <span>{{ selectedHistoryReport.location_name }}</span>
                </div>
                <div class="meta-item">
                  <strong>Status:</strong>
                  <span class="status-badge" :class="'status-' + (selectedHistoryReport.status || 'SAVED').toLowerCase()">
                    {{ (selectedHistoryReport.status || 'SAVED').replace('_', ' ') }}
                  </span>
                </div>
              </div>

              <div class="email-preview-box">
                <div class="email-preview-header">
                  <strong>Subject:</strong> {{ selectedHistoryReport.email_subject }}
                </div>
                <pre class="history-letter-body">{{ selectedHistoryReport.email_body }}</pre>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-outline" @click="showHistoryDetailModal = false">Close</button>
              <button class="btn-secondary" @click="printHistoryDetail" title="Print plan or save as PDF">
                <span>🖨️</span> Print / PDF
              </button>
              <button class="btn-secondary" @click="emailHistoryDetail" title="Open in personal mail client">
                <span>✉️</span> Open in Mail App
              </button>
              <button class="btn-primary" @click="copyHistoryDetail" title="Copy to clipboard">
                <span>{{ copyHistorySuccess ? '✓ Copied Details!' : '📋 Copy Details' }}</span>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </div>

  </div>
</template>

<style scoped>
.auditor-page {
  max-width: 1680px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem 2rem;
  font-family: inherit;
  box-sizing: border-box;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header.header-compact {
  margin-bottom: 0.75rem;
}

.page-title {
  font-size: 2.2rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin-bottom: 0.5rem;
}

.page-title.title-compact {
  font-size: 1.45rem;
  margin-bottom: 0.25rem;
}

.page-subtitle {
  font-size: 1.1rem;
  color: var(--color-text-muted);
}

.hidden-input {
    display: none;
}

.upload-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin-top: 1rem;
}

.pre-upload-tip {
    background: #eef8f6;
    color: #11473f;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    margin-bottom: 2.5rem;
    border-left: 4px solid var(--color-primary);
    font-size: 1.05rem;
    line-height: 1.5;
    text-align: left;
    max-width: 800px;
    width: 100%;
}
.pre-upload-tip strong {
    font-weight: 700;
}

.upload-box-wrapper {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    width: 100%;
    align-items: center;
}

.upload-actions {
    display: flex;
    gap: 2rem;
    width: 100%;
    max-width: 800px;
    justify-content: center;
}

.upload-box {
    border: 2px dashed var(--color-primary);
    border-radius: 16px;
    padding: 3rem 1.5rem;
    text-align: center;
    background: var(--color-bg-sage);
    cursor: pointer;
    transition: all 0.2s ease;
    flex: 1;
    max-width: 350px;
}

.camera-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    width: 100%;
    max-width: 600px;
}

.video-preview {
    width: 100%;
    border-radius: 12px;
    border: 2px solid var(--color-primary);
    background: #000;
}

.camera-actions {
    display: flex;
    gap: 1rem;
}

.upload-box:hover {
    background: #e6f0ed;
    border-color: #124b42;
}

.upload-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
}

.btn-primary {
    background: #1b3d2f;
    color: #ffffff;
    border: 1.5px solid #1b3d2f;
    padding: 0.75rem 1.6rem;
    font-size: 1rem;
    font-weight: 700;
    font-family: inherit;
    border-radius: 10px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 2px 6px rgba(27, 61, 47, 0.25);
    text-decoration: none;
    line-height: 1.2;
}

.btn-primary:hover:not(:disabled) {
    background: #14532d;
    border-color: #14532d;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(27, 61, 47, 0.35);
}

.btn-primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
}

.btn-secondary {
    background: #ffffff;
    color: #1b3d2f;
    border: 2px solid #1b3d2f;
    padding: 0.75rem 1.4rem;
    font-size: 0.95rem;
    font-weight: 700;
    font-family: inherit;
    border-radius: 10px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    text-decoration: none;
    line-height: 1.2;
}

.btn-secondary:hover:not(:disabled) {
    background: #1b3d2f;
    border-color: #1b3d2f;
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 3px 8px rgba(27, 61, 47, 0.25);
}

.btn-secondary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
}

.btn-outline {
    background: #ffffff;
    color: #1e293b;
    border: 2px solid #94a3b8;
    padding: 0.75rem 1.3rem;
    font-size: 0.95rem;
    font-weight: 700;
    font-family: inherit;
    border-radius: 10px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    text-decoration: none;
    line-height: 1.2;
}

.btn-outline:hover:not(:disabled) {
    background: #f1f5f9;
    border-color: #64748b;
    color: #0f172a;
    transform: translateY(-1px);
}

.dashboard-footer {
    width: 100%;
    display: flex;
    justify-content: center;
    margin-top: 3rem;
    padding-top: 2rem;
    border-top: 1px solid #eaeaea;
}

.btn-premium {
    background: #1b3d2f;
    color: white;
    border: 2px solid #1b3d2f;
    padding: 1rem 2.5rem;
    border-radius: 50px;
    font-size: 1.15rem;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 0 8px 20px rgba(27, 61, 47, 0.28);
    transition: all 0.25s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
}

.btn-premium:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 25px rgba(27, 61, 47, 0.38);
    background: #14532d;
    border-color: #14532d;
}

.btn-premium:active {
    transform: translateY(0);
    box-shadow: 0 4px 10px rgba(27, 61, 47, 0.25);
}

.disclaimer-banner {
    background: #fff8eb;
    color: #965a00;
    padding: 0.65rem 1rem;
    border-radius: 8px;
    margin: 1rem auto 0 auto;
    border: 1px solid #ffe2b3;
    font-size: 0.82rem;
    line-height: 1.45;
    text-align: left;
    max-width: 800px;
    width: 100%;
}
.disclaimer-banner strong {
    font-weight: 700;
}

.btn-icon {
    font-size: 1.3rem;
}

.error-banner {
    background: #fde8e8;
    color: #9b1c1c;
    padding: 1rem 2rem;
    border-radius: 8px;
    margin-top: 2rem;
    border: 1px solid #f8b4b4;
    font-weight: 600;
}

.loading-overlay {
    position: relative;
    width: 100%;
    min-height: 600px;
    border-radius: 16px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 2rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}

.loading-backdrop {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-size: cover;
    background-position: center;
    filter: blur(12px) brightness(0.25);
    z-index: 1;
}

.loading-content {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    max-width: 600px;
    padding: 2rem;
}

.scanner-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 3rem;
    width: 100%;
}

.scanner-image-wrapper {
    position: relative;
    width: 100%;
    max-width: 350px;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 0 25px rgba(52, 199, 89, 0.5);
    border: 2px solid var(--color-primary);
}

.scanner-image {
    width: 100%;
    height: auto;
    display: block;
    opacity: 0.85;
}

.scanner-line {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 4px;
    background: #34c759;
    box-shadow: 0 0 15px 5px rgba(52, 199, 89, 0.7);
    animation: scan 2s linear infinite alternate;
}

@keyframes scan {
    0% { top: 0; }
    100% { top: 100%; }
}

.loading-text {
    color: white;
    font-size: 1.5rem;
    font-weight: 700;
    margin-top: 1.5rem;
    text-shadow: 0 2px 4px rgba(0,0,0,0.8);
    height: 30px;
    text-align: center;
}

.tip-card {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 12px;
    padding: 1.5rem 2rem;
    width: 100%;
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    border-left: 6px solid var(--color-primary);
    animation: floatTip 0.5s ease-out;
}

@keyframes floatTip {
    0% { transform: translateY(15px); opacity: 0; }
    100% { transform: translateY(0); opacity: 1; }
}

.tip-header {
    font-size: 1.1rem;
    font-weight: 800;
    color: var(--color-primary);
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.tip-icon {
    font-size: 1.5rem;
}

.tip-content {
    font-size: 1.1rem;
    color: var(--color-text-main);
    line-height: 1.5;
    margin: 0;
    min-height: 48px;
}

.result-container {
    margin-top: 0.5rem;
}

.hotspot-dashboard {
    width: 100%;
    max-width: 1140px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    align-items: stretch;
}

.dashboard-header {
    text-align: left;
    margin-bottom: 0.65rem;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.4rem;
    width: 100%;
}

.dashboard-header-top {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    width: 100%;
}

.dashboard-title-group {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.hazard-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #fff0f0;
    color: #d92d20;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 700;
    border: 1px solid #fed4d2;
    margin: 0;
}

.pulse-dot {
    width: 8px;
    height: 8px;
    background-color: #d92d20;
    border-radius: 50%;
    animation: simple-pulse 2s infinite;
}

@keyframes simple-pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(217, 45, 32, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(217, 45, 32, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(217, 45, 32, 0); }
}

.dashboard-title {
    font-size: 1.35rem;
    font-weight: 800;
    color: var(--color-text-main);
    margin: 0;
    letter-spacing: -0.01em;
}

.dashboard-subtitle {
    font-size: 0.88rem;
    color: var(--color-text-muted);
    max-width: 900px;
    margin: 0;
    line-height: 1.4;
}

.interactive-viewer {
    position: relative;
    display: inline-block;
    max-width: 100%;
    max-height: clamp(380px, 64vh, 580px);
    border-radius: 16px;
    overflow: hidden;
    border: 2px solid var(--color-primary);
    background: #0f172a;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.14);
    line-height: 0;
}

.overlay-canvas {
    max-width: 100%;
    max-height: clamp(380px, 64vh, 580px);
    width: auto;
    height: auto;
    display: block;
    object-fit: contain;
}

/* Hotspots & Numbered Pins */
.hotspot-pulse {
    position: absolute;
    width: 44px;
    height: 44px;
    background: rgba(239, 68, 68, 0.35);
    border-radius: 50%;
    transform: translate(-50%, -50%);
    animation: pulse 2s infinite cubic-bezier(0.2, 0, 0, 1);
    pointer-events: none;
    z-index: 15;
}

.hotspot-pin {
    position: absolute;
    padding: 0 9px;
    height: 32px;
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    color: #ffffff;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    transform: translate(-50%, -50%);
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(0, 0, 0, 0.1);
    border: 2.5px solid #ffffff;
    z-index: 20;
    transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease, background 0.2s ease;
    user-select: none;
}

.pin-icon {
    font-size: 0.85rem;
    line-height: 1;
}

.pin-number {
    font-size: 0.85rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.01em;
}

.hotspot-pin:hover,
.hotspot-pin.hotspot-hovered {
    transform: translate(-50%, -50%) scale(1.18);
    box-shadow: 0 6px 20px rgba(220, 38, 38, 0.55), 0 0 0 2px #ffffff;
    z-index: 70 !important;
}

.hotspot-pin.hotspot-active {
    background: #1b3d2f;
    color: #ffffff;
    border-color: #86efac;
    transform: translate(-50%, -50%) scale(1.25);
    box-shadow: 0 0 0 4px #1b3d2f, 0 8px 24px rgba(27, 61, 47, 0.55);
    z-index: 80 !important;
}

.hotspot-pin.hotspot-active .pin-number {
    color: #ffffff;
}


/* Glassmorphism Hazard Details Overlay */
.hazard-overlay-wrapper {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    width: 90%;
    max-width: 500px;
    z-index: 50;
    pointer-events: none; /* Let clicks pass through empty wrapper space */
    transition: top 0.3s ease, bottom 0.3s ease;
}

.hazard-overlay-card {
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.5) inset;
    border-left: 6px solid #ff3b30;
    pointer-events: auto; /* Re-enable clicks on the card itself */
    text-align: left;
}

.overlay-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.75rem;
}

.overlay-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.overlay-title h4 {
    margin: 0;
    color: #1a1a1a;
    font-size: 1.15rem;
    font-weight: 800;
}

.overlay-icon {
    font-size: 1.2rem;
}

.overlay-close {
    background: rgba(0,0,0,0.05);
    border: none;
    color: #555;
    font-size: 1.1rem;
    cursor: pointer;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
}

.overlay-close:hover {
    background: #ff3b30;
    color: white;
}

.overlay-text {
    margin: 0;
    color: #333;
    line-height: 1.5;
    font-size: 0.95rem;
}

/* Slide Fade Transition */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(30px);
  opacity: 0;
}

.dynamic-box {
    position: absolute;
    border: 3px solid #ff3b30;
    background-color: rgba(255, 59, 48, 0.12);
    border-radius: 8px;
    pointer-events: none;
    transition: all 0.25s ease;
    z-index: 12;
}

.dynamic-box.box-active {
    border-color: #fbbf24;
    background-color: rgba(251, 191, 36, 0.18);
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.35), 0 0 24px rgba(251, 191, 36, 0.6);
    z-index: 14;
}

.dynamic-box.box-hovered {
    border: 2.5px dashed #ff3b30;
    background-color: rgba(255, 59, 48, 0.15);
}


/* Timer UX */
.timer-display {
    margin-top: 1.5rem;
    text-align: center;
}

.timer-text {
    font-size: 1.1rem;
    color: rgba(255, 255, 255, 0.9);
    margin: 0;
}

.timer-warning {
    margin-top: 0.75rem;
    background: rgba(255, 165, 0, 0.15);
    border: 1px solid rgba(255, 165, 0, 0.5);
    padding: 0.75rem 1rem;
    border-radius: 8px;
    color: #ffd27f;
    font-size: 0.95rem;
    line-height: 1.4;
    animation: slideUp 0.3s ease-out;
    max-width: 400px;
    margin-left: auto;
    margin-right: auto;
}

/* ═══════════════════════════════════════════════════════════════
   CIVIC HUB & ADVOCACY STYLES (Iteration 3, Epic 6)
   ═══════════════════════════════════════════════════════════════ */

.civic-badge-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
}

.civic-pill {
    background: #e8f5e9;
    color: #1b5e20;
    font-size: 0.85rem;
    font-weight: 700;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    border: 1px solid #c8e6c9;
    letter-spacing: 0.02em;
}

/* Space Type Selector: Private vs Public */
.space-type-container {
    width: 100%;
    margin-bottom: 1.5rem;
}

.space-type-selector {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    max-width: 900px;
    margin: 0 auto;
}

.space-type-btn {
    display: flex;
    align-items: center;
    gap: 1.1rem;
    padding: 1.1rem 1.4rem;
    background: #ffffff;
    border: 2px solid #e2e8f0;
    border-radius: 14px;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s ease;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.space-type-btn:hover {
    border-color: #cbd5e1;
    transform: translateY(-2px);
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.07);
}

.space-type-btn.btn-selected {
    border-color: #1b3d2f;
    background: #1b3d2f;
    box-shadow: 0 4px 16px rgba(27, 61, 47, 0.28);
}

.space-btn-icon {
    font-size: 2.2rem;
    line-height: 1;
    flex-shrink: 0;
}

.space-btn-content {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.space-btn-title {
    font-size: 1.05rem;
    font-weight: 800;
    color: #0f172a;
}

.space-type-btn.btn-selected .space-btn-title {
    color: #ffffff;
}

.space-btn-desc {
    font-size: 0.82rem;
    color: #64748b;
    line-height: 1.35;
}

.space-type-btn.btn-selected .space-btn-desc {
    color: #dcfce7;
}

/* Private Home Banner */
.private-home-banner {
    background: linear-gradient(135deg, #f7faf8 0%, #eef5f1 100%);
    border: 1px solid #cce3d5;
    border-radius: 16px;
    padding: 1.35rem 1.6rem;
    margin-bottom: 2rem;
    text-align: left;
    box-shadow: 0 4px 12px rgba(27, 61, 47, 0.05);
}

.home-banner-top {
    margin-bottom: 1.1rem;
}

.home-banner-title-group {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
}

.home-icon {
    font-size: 2.2rem;
    line-height: 1;
}

.home-headline {
    margin: 0 0 0.3rem 0;
    font-size: 1.25rem;
    font-weight: 800;
    color: #1b3d2f;
}

.home-subtext {
    margin: 0;
    font-size: 0.92rem;
    color: #334155;
    line-height: 1.5;
}

.home-room-selector-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    padding-top: 0.85rem;
    border-top: 1px solid #d8ebd0;
}

.room-selector-label {
    font-size: 0.88rem;
    color: #1b3d2f;
}

.room-type-chips {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.room-chip {
    background: #ffffff;
    border: 1px solid #bbf7d0;
    color: #166534;
    font-size: 0.84rem;
    font-weight: 700;
    padding: 0.45rem 0.95rem;
    border-radius: 999px;
    cursor: pointer;
    transition: all 0.15s ease;
}

.room-chip:hover {
    background: #dcfce7;
    border-color: #86efac;
}

.room-chip.chip-active {
    background: #1b3d2f;
    border-color: #1b3d2f;
    color: #ffffff;
    box-shadow: 0 2px 6px rgba(27, 61, 47, 0.2);
}

.room-custom-input-group {
    flex: 1;
    min-width: 220px;
}

.form-control-sm {
    width: 100%;
    padding: 0.45rem 0.85rem;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 0.85rem;
    background: #ffffff;
    box-sizing: border-box;
}

.form-control-sm:focus {
    outline: none;
    border-color: #1b3d2f;
    box-shadow: 0 0 0 2px rgba(27, 61, 47, 0.15);
}

/* Result Dashboard Space Mode Badges */
.result-space-badge-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.65rem;
    flex-wrap: wrap;
}

.space-mode-pill {
    font-size: 0.86rem;
    font-weight: 700;
    padding: 0.45rem 1rem;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
}

.space-mode-pill.private {
    background: #f0fdf4;
    color: #166534;
    border: 1px solid #bbf7d0;
}

.space-mode-pill.public {
    background: #eff6ff;
    color: #1e40af;
    border: 1px solid #bfdbfe;
}

.result-badge-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.result-badge-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.btn-switch-space {
    background: #1b3d2f;
    border: 1.5px solid #1b3d2f;
    color: #ffffff;
    font-size: 0.82rem;
    font-weight: 700;
    padding: 0.4rem 0.85rem;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s ease;
    box-shadow: 0 2px 6px rgba(27, 61, 47, 0.2);
}

.btn-switch-space:hover {
    background: #14532d;
    border-color: #14532d;
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(27, 61, 47, 0.3);
}

.btn-quick-history {
    background: #1b3d2f;
    border: 1.5px solid #1b3d2f;
    color: #ffffff;
    font-size: 0.82rem;
    font-weight: 700;
    padding: 0.4rem 0.85rem;
    border-radius: 8px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    transition: all 0.15s ease;
    box-shadow: 0 2px 6px rgba(27, 61, 47, 0.2);
}

.btn-quick-history:hover {
    background: #14532d;
    border-color: #14532d;
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(27, 61, 47, 0.3);
}

.btn-new-audit {
    background: #1b3d2f;
    border: 1.5px solid #1b3d2f;
    color: #ffffff;
    font-size: 0.82rem;
    font-weight: 700;
    padding: 0.4rem 0.85rem;
    border-radius: 8px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    transition: all 0.15s ease;
    box-shadow: 0 2px 6px rgba(27, 61, 47, 0.2);
}

.btn-new-audit:hover {
    background: #14532d;
    border-color: #14532d;
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(27, 61, 47, 0.3);
}

/* Modal In-Place Saved History Confirmation Banner */
.saved-history-banner {
    background: #f0fdf4;
    border: 1.5px solid #86efac;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin: 1.25rem 0 0.5rem 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    box-shadow: 0 2px 8px rgba(22, 101, 52, 0.08);
}

.saved-banner-text {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    flex: 1;
    min-width: 250px;
}

.saved-banner-icon {
    font-size: 1.4rem;
    line-height: 1;
}

.saved-banner-text strong {
    display: block;
    color: #166534;
    font-size: 0.96rem;
    margin-bottom: 0.2rem;
}

.saved-banner-text span {
    font-size: 0.86rem;
    color: #334155;
    line-height: 1.4;
}

.btn-goto-history {
    background: #1b3d2f;
    color: #ffffff;
    border: 1.5px solid #1b3d2f;
    font-size: 0.88rem;
    font-weight: 700;
    padding: 0.6rem 1.1rem;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    box-shadow: 0 2px 6px rgba(27, 61, 47, 0.2);
}

.btn-goto-history:hover {
    background: #14532d;
    border-color: #14532d;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(27, 61, 47, 0.28);
}

.btn-saved-history-link {
    background: #166534 !important;
    border-color: #166534 !important;
}

@media (max-width: 640px) {
    .space-type-selector {
        grid-template-columns: 1fr;
    }
}

/* Side-by-side Inspection Workspace Layout */
.audit-workspace-layout {
    display: flex;
    justify-content: center;
    align-items: stretch;
    gap: 1.5rem;
    margin-top: 0.75rem;
    margin-bottom: 1.5rem;
    text-align: left;
    width: 100%;
}

@media (max-width: 1024px) {
    .audit-workspace-layout {
        flex-direction: column;
        align-items: center;
        gap: 1.25rem;
    }
}

.workspace-image-container {
    flex: 0 1 auto;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    min-width: 0;
}

.workspace-side-panel {
    flex: 0 0 380px;
    width: 380px;
    display: flex;
    flex-direction: column;
    min-width: 340px;
    max-width: 400px;
    height: 100%;
    max-height: clamp(380px, 64vh, 580px);
}

/* Side Detail Card (Active Issue Selected) */
.side-detail-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 1.15rem 1.25rem;
    border: 1px solid #e5e7eb;
    border-left: 5px solid #d32f2f;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.07);
    display: flex;
    flex-direction: column;
    height: 100%;
    max-height: clamp(380px, 64vh, 580px);
    box-sizing: border-box;
    animation: sideSlideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes sideSlideIn {
    from { opacity: 0; transform: translateX(12px); }
    to { opacity: 1; transform: translateX(0); }
}

.side-detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #f1f5f9;
    flex-shrink: 0;
}

.side-nav-counter {
    display: inline-flex;
    align-items: center;
}

.barrier-index-pill {
    background: #f1f5f9;
    color: #1e293b;
    font-size: 0.78rem;
    font-weight: 800;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    border: 1px solid #e2e8f0;
    display: inline-flex;
    align-items: center;
    letter-spacing: -0.01em;
}

.side-category-row {
    margin-bottom: 0.4rem;
    display: flex;
    align-items: center;
    flex-shrink: 0;
}

.side-header-actions {
    display: flex;
    align-items: center;
    gap: 0.45rem;
}

.issue-nav-btn-group {
    display: flex;
    gap: 0.25rem;
}

.btn-issue-nav {
    background: #1b3d2f;
    border: 1.5px solid #1b3d2f;
    border-radius: 7px;
    width: 28px;
    height: 28px;
    font-size: 0.72rem;
    font-weight: 800;
    color: #ffffff;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
    box-shadow: 0 1px 4px rgba(27, 61, 47, 0.2);
}

.btn-issue-nav:hover {
    background: #14532d;
    color: #ffffff;
    border-color: #14532d;
}

.side-compliance-row {
    margin-bottom: 0.5rem;
}

.btn-side-close {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    width: 28px;
    height: 28px;
    font-size: 0.85rem;
    color: #64748b;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
}

.btn-side-close:hover {
    background: #fee2e2;
    color: #dc2626;
    border-color: #fca5a5;
}

.side-card-title {
    margin: 0 0 0.45rem 0;
    font-size: 1.12rem;
    font-weight: 800;
    color: #1e293b;
    line-height: 1.25;
    flex-shrink: 0;
}

.side-card-body-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 6px;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 transparent;
}

.side-card-body-scroll::-webkit-scrollbar {
    width: 5px;
}

.side-card-body-scroll::-webkit-scrollbar-track {
    background: transparent;
}

.side-card-body-scroll::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 4px;
}

.side-card-body-scroll::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}

.side-card-body {
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
}

.side-card-footer {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    margin-top: auto;
    padding-top: 0.65rem;
    border-top: 1px solid #f1f5f9;
    flex-shrink: 0;
}

.btn-side-action {
    width: 100%;
    justify-content: center;
    padding: 0.6rem 1rem;
    font-size: 0.88rem;
}

.btn-side-secondary {
    background: #1b3d2f;
    border: 1.5px solid #1b3d2f;
    color: #ffffff;
    padding: 0.55rem 0.95rem;
    border-radius: 10px;
    font-weight: 700;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 2px 6px rgba(27, 61, 47, 0.2);
}

.btn-side-secondary:hover {
    background: #14532d;
    border-color: #14532d;
    color: #ffffff;
}

/* Side Overview Card (Default State) */
.side-overview-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 1.15rem 1.25rem;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    display: flex;
    flex-direction: column;
    height: 100%;
    max-height: clamp(380px, 64vh, 580px);
    box-sizing: border-box;
    gap: 0.75rem;
}

.overview-header-group {
    display: flex;
    gap: 0.65rem;
    align-items: flex-start;
    flex-shrink: 0;
}

.overview-icon {
    font-size: 1.5rem;
}

.overview-heading {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 800;
    color: #1e293b;
}

.overview-instructions {
    margin: 0.25rem 0 0 0;
    font-size: 0.84rem;
    color: #64748b;
    line-height: 1.35;
}

.side-issue-list {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-right: 0.25rem;
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 transparent;
}

.side-issue-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.65rem 0.85rem;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s ease;
}

.side-issue-item:hover {
    background: #f0fdf4;
    border-color: #1b3d2f;
    transform: translateX(2px);
}

.side-issue-item.item-selected {
    background: #1b3d2f;
    border-color: #1b3d2f;
    box-shadow: 0 4px 14px rgba(27, 61, 47, 0.28);
}

.side-issue-item.item-selected .issue-item-title {
    color: #ffffff;
}

.side-issue-item.item-selected .issue-item-category {
    color: #bbf7d0;
}

.side-issue-item.item-selected .issue-item-number {
    background: #ffffff;
    color: #1b3d2f;
    font-weight: 900;
}

.side-issue-item.item-selected .issue-item-lrv {
    background: rgba(255, 255, 255, 0.2);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.4);
}

.side-issue-item.item-hovered:not(.item-selected) {
    background: #f0fdf4;
    border-color: #166534;
    transform: translateX(3px);
}

.issue-item-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 28px;
    height: 24px;
    padding: 0 6px;
    border-radius: 6px;
    background: #fee2e2;
    color: #b91c1c;
    font-size: 0.78rem;
    font-weight: 800;
    flex-shrink: 0;
    transition: all 0.2s ease;
}

.side-issue-item:hover:not(.item-selected) .issue-item-number,
.side-issue-item.item-hovered:not(.item-selected) .issue-item-number {
    background: #1b3d2f;
    color: #ffffff;
}

.issue-item-left {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    min-width: 0;
}

.issue-item-icon {
    font-size: 1.1rem;
    flex-shrink: 0;
}

.issue-item-texts {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.issue-item-title {
    font-size: 0.88rem;
    font-weight: 700;
    color: #1e293b;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.issue-item-category {
    font-size: 0.72rem;
    color: #64748b;
    text-transform: uppercase;
    font-weight: 600;
}

.issue-item-lrv {
    font-size: 0.8rem;
    font-weight: 700;
    color: #c62828;
    background: #ffebee;
    padding: 0.2rem 0.5rem;
    border-radius: 6px;
    flex-shrink: 0;
    margin-left: 0.5rem;
}

.side-advocacy-cta {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: auto;
    flex-shrink: 0;
}

.advocacy-pill-sm {
    font-size: 0.75rem;
    font-weight: 700;
    color: #166534;
    display: block;
    margin-bottom: 0.25rem;
}

.side-advocacy-sub {
    margin: 0;
    font-size: 0.85rem;
    color: #374151;
    line-height: 1.4;
}

.btn-full-width {
    width: 100%;
    justify-content: center;
    font-size: 0.95rem;
    padding: 0.75rem 1rem;
}

.side-card-fade-enter-active,
.side-card-fade-leave-active {
    transition: all 0.2s ease;
}

.side-card-fade-enter-from,
.side-card-fade-leave-to {
    opacity: 0;
    transform: scale(0.98);
}

.barrier-cat-pill {
    font-size: 0.78rem;
    font-weight: 700;
    color: #1b3d2f;
    background: #f0fdf4;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    border: 1px solid #bbf7d0;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    line-height: 1.3;
}

.cat-pill-icon {
    font-size: 0.85rem;
    line-height: 1;
}

.compliance-badge {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
}

.badge-fail {
    background: #ffebee;
    color: #c62828;
    border: 1px solid #ffcdd2;
}

.badge-ok {
    background: #e8f5e9;
    color: #2e7d32;
    border: 1px solid #c8e6c9;
}

.lrv-meter-container {
    background: #f8fafc;
    border-radius: 8px;
    padding: 0.6rem 0.75rem;
    margin-bottom: 0.75rem;
    border: 1px solid #edf2f7;
}

.lrv-meter-header {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    margin-bottom: 0.4rem;
}

.lrv-target strong {
    color: #2e7d32;
}

.lrv-meter-bar {
    height: 8px;
    background: #e2e8f0;
    border-radius: 4px;
    overflow: hidden;
}

.lrv-meter-fill {
    height: 100%;
    background: #2e7d32;
    border-radius: 4px;
    transition: width 0.6s ease;
}

.fill-danger {
    background: #d32f2f;
}

.barrier-impact {
    font-size: 0.9rem;
    color: #333;
    line-height: 1.4;
    margin: 0 0 0.5rem 0;
}

.barrier-solution {
    font-size: 0.85rem;
    color: #1e40af;
    background: #eff6ff;
    padding: 0.55rem 0.75rem;
    border-radius: 8px;
    border-left: 3px solid #3b82f6;
    line-height: 1.4;
    margin: 0;
}

.barrier-citation {
    margin-top: 0;
    font-size: 0.76rem;
    color: #64748b;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 0.35rem 0.6rem;
    border-radius: 6px;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

.btn-advocate-primary {
    background: #1b3d2f;
    color: #ffffff;
    border: none;
    padding: 0.85rem 1.4rem;
    font-size: 0.98rem;
    font-weight: 800;
    border-radius: 12px;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(27, 61, 47, 0.25);
    transition: all 0.2s ease;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.btn-advocate-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(27, 61, 47, 0.35);
    background: #275742;
}

/* Modal Dialog */
.modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 1rem;
}

.advocacy-modal-dialog {
    background: #ffffff;
    border-radius: 20px;
    width: 100%;
    max-width: 780px;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    text-align: left;
    display: flex;
    flex-direction: column;
    animation: modalPop 0.25s ease-out;
}

@keyframes modalPop {
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 1.5rem 1.75rem;
    border-bottom: 1px solid #edf2f7;
    background: #fafbfc;
    border-top-left-radius: 20px;
    border-top-right-radius: 20px;
}

.modal-pill {
    font-size: 0.75rem;
    font-weight: 700;
    color: #1b5e20;
    background: #e8f5e9;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    display: inline-block;
    margin-bottom: 0.35rem;
    text-transform: uppercase;
}

.modal-title {
    margin: 0;
    font-size: 1.35rem;
    font-weight: 800;
    color: #1a202c;
}

.modal-desc {
    margin: 0.25rem 0 0 0;
    font-size: 0.9rem;
    color: #718096;
}

.btn-modal-close {
    background: #edf2f7;
    border: none;
    border-radius: 50%;
    width: 32px;
    height: 32px;
    font-size: 1rem;
    color: #4a5568;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
}

.btn-modal-close:hover {
    background: #e2e8f0;
}

.modal-body {
    padding: 1.5rem 1.75rem;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
}

/* Council Selector Card */
.council-selector-card {
    background: #f7fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.1rem 1.25rem;
}

.form-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
}

.flex-2 { flex: 2; min-width: 250px; }
.flex-1 { flex: 1; min-width: 200px; }

.form-group {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}

.form-group label {
    font-size: 0.85rem;
    color: #4a5568;
}

.form-control {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
    font-size: 0.95rem;
    color: #1e293b;
    background: #ffffff;
    transition: border-color 0.2s;
}

.form-control:focus {
    outline: none;
    border-color: #2e7d32;
    box-shadow: 0 0 0 3px rgba(46, 125, 50, 0.15);
}

.read-only-pill {
    background: #e2e8f0;
    padding: 0.6rem 0.8rem;
    border-radius: 8px;
    font-size: 0.9rem;
    font-weight: 600;
    color: #334155;
    word-break: break-all;
}

.council-meta-row {
    display: flex;
    gap: 1.25rem;
    font-size: 0.8rem;
    color: #64748b;
    border-top: 1px dashed #cbd5e1;
    padding-top: 0.5rem;
    flex-wrap: wrap;
}

.form-grid-two {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

@media (max-width: 600px) {
    .form-grid-two { grid-template-columns: 1fr; }
}

/* Email Preview */
.email-preview-box {
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    overflow: hidden;
    background: #ffffff;
}

.email-preview-header {
    background: #f8fafc;
    padding: 0.6rem 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e2e8f0;
    font-size: 0.85rem;
    color: #475569;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.preview-badge {
    background: #e0f2fe;
    color: #0369a1;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    margin-right: 0.5rem;
    font-size: 0.75rem;
}

.btn-copy-sm {
    background: #1b3d2f;
    border: 1px solid #1b3d2f;
    padding: 0.3rem 0.65rem;
    border-radius: 6px;
    font-size: 0.8rem;
    cursor: pointer;
    font-weight: 700;
    color: #ffffff;
    transition: all 0.2s;
}

.btn-copy-sm:hover {
    background: #14532d;
    border-color: #14532d;
}

.email-textarea {
    width: 100%;
    padding: 0.85rem 1rem;
    border: none;
    font-family: inherit;
    font-size: 0.9rem;
    line-height: 1.55;
    color: #1e293b;
    resize: vertical;
    box-sizing: border-box;
}

.email-textarea:focus {
    outline: none;
}

.guideline-callout {
    background: #eff6ff;
    color: #1e40af;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.85rem;
    line-height: 1.4;
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
}

.modal-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.85rem;
    padding: 1.25rem 1.75rem;
    border-top: 1px solid #edf2f7;
    background: #fafbfc;
    border-bottom-left-radius: 20px;
    border-bottom-right-radius: 20px;
    flex-wrap: wrap;
}

.modal-footer .btn-primary,
.modal-footer .btn-secondary,
.modal-footer .btn-outline {
    margin: 0;
    min-height: 44px;
    padding: 0.65rem 1.35rem;
    font-size: 0.95rem;
    border-radius: 10px;
    line-height: 1.2;
}

.modal-footer button span {
    line-height: 1;
    display: inline-flex;
    align-items: center;
}

/* Success Screen */
.modal-success-screen {
    padding: 2.5rem 2rem;
    text-align: center;
}

.success-icon-large {
    font-size: 3.5rem;
    margin-bottom: 0.75rem;
}

.modal-success-screen h4 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 800;
    color: #1b5e20;
}

.success-ref {
    font-size: 1.1rem;
    color: #333;
    margin: 0.5rem 0;
}

.success-detail {
    color: #555;
    margin-bottom: 1.5rem;
}

.success-summary-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    text-align: left;
    max-width: 480px;
    margin: 0 auto 1.5rem auto;
    font-size: 0.9rem;
    line-height: 1.6;
}

.success-actions {
    display: flex;
    justify-content: center;
    gap: 1rem;
    flex-wrap: wrap;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
    transition: opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
    opacity: 0;
}

/* ═══════════════════════════════════════════════════════════════
 * CIVIC & ASSESSMENT HUB TABS
 * ═══════════════════════════════════════════════════════════════ */
.hub-tab-bar {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 0.25rem;
}

.hub-tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  padding: 0.75rem 1.25rem;
  font-size: 1.05rem;
  font-weight: 700;
  color: #64748b;
  cursor: pointer;
  border-radius: 8px 8px 0 0;
  transition: all 0.2s ease;
}

.hub-tab-btn:hover {
  color: #1b3d2f;
  background: #f1f5f9;
}

.hub-tab-btn.tab-active {
  color: #ffffff;
  border-bottom-color: #14532d;
  background: #1b3d2f;
  box-shadow: 0 4px 12px rgba(27, 61, 47, 0.25);
}

.tab-badge {
  background: #fee2e2;
  color: #991b1b;
  font-size: 0.75rem;
  font-weight: 800;
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
}

.tab-badge-counter {
  background: #e2e8f0;
  color: #334155;
  font-size: 0.78rem;
  font-weight: 800;
  padding: 0.15rem 0.55rem;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.tab-badge-counter.badge-highlight {
  background: #dcfce7;
  color: #166534;
}

.tab-active .tab-badge-counter {
  background: #dcfce7;
  color: #14532d;
}

/* ═══════════════════════════════════════════════════════════════
 * MUNICIPAL GEOCODER BANNER
 * ═══════════════════════════════════════════════════════════════ */
.municipal-geocoder-banner {
  background: linear-gradient(135deg, #f0fdf4 0%, #e6f4ea 100%);
  border: 1.5px solid #86efac;
  border-radius: 16px;
  padding: 1.25rem 1.75rem;
  margin-bottom: 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  box-shadow: 0 4px 12px rgba(22, 101, 52, 0.06);
  flex-wrap: wrap;
}

.geocoder-info {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  flex: 1;
  min-width: 320px;
}

.geocoder-badge-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.geo-shield-icon {
  font-size: 1.3rem;
}

.geo-banner-title {
  font-size: 0.85rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #166534;
}

.method-tag {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
}

.method-exif {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}

.method-geolocation {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fde68a;
}

.method-preset,
.method-default {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.geocoder-council-title {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  flex-wrap: wrap;
}

.council-headline {
  margin: 0;
  font-size: 1.45rem;
  font-weight: 800;
  color: #14532d;
}

.lga-boundary-tag {
  background: #ffffff;
  color: #166534;
  font-size: 0.82rem;
  font-weight: 700;
  padding: 0.2rem 0.65rem;
  border-radius: 8px;
  border: 1px solid #bbf7d0;
}

.geocoder-contacts {
  display: flex;
  gap: 1.25rem;
  font-size: 0.88rem;
  color: #374151;
  flex-wrap: wrap;
}

.contact-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.geocoder-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.btn-geo-action {
  background: #1b3d2f;
  color: #ffffff;
  border: 1.5px solid #1b3d2f;
  padding: 0.65rem 1rem;
  font-size: 0.9rem;
  font-weight: 700;
  border-radius: 10px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(27, 61, 47, 0.2);
}

.btn-geo-action:hover:not(:disabled) {
  background: #14532d;
  color: #ffffff;
  border-color: #14532d;
  transform: translateY(-1px);
}

.btn-geo-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-geo-preset {
  background: #1b3d2f;
  color: #ffffff;
  border-color: #1b3d2f;
}

.btn-geo-preset:hover {
  background: #14532d;
  border-color: #14532d;
}

/* Presets Panel */
.presets-dropdown-panel {
  background: #ffffff;
  border: 1.5px solid #cbd5e1;
  border-radius: 14px;
  padding: 1.25rem;
  margin-top: -1.25rem;
  margin-bottom: 2rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
}

.presets-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.85rem;
}

.presets-panel-header h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #334155;
}

.btn-close-presets {
  background: transparent;
  border: none;
  font-size: 1.1rem;
  color: #94a3b8;
  cursor: pointer;
}

.preset-chip-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 0.75rem;
}

.preset-chip-btn {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  text-align: left;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.preset-chip-btn:hover {
  background: #f0fdf4;
  border-color: #86efac;
  transform: translateY(-2px);
}

.preset-btn-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.92rem;
  color: #1e293b;
}

.preset-suburb-tag {
  font-size: 0.75rem;
  font-weight: 700;
  color: #166534;
  background: #dcfce7;
  padding: 0.1rem 0.45rem;
  border-radius: 6px;
}

.preset-btn-bottom {
  font-size: 0.8rem;
  color: #64748b;
  display: flex;
  gap: 0.4rem;
}

/* ═══════════════════════════════════════════════════════════════
 * PUBLIC SPATIAL HAZARD TAXONOMY FILTER BAR
 * ═══════════════════════════════════════════════════════════════ */
.taxonomy-filter-bar {
  margin-top: 0.35rem;
  padding: 0.35rem 0.65rem;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-label {
  font-size: 0.76rem;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.filter-chips {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.chip-btn {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #334155;
  padding: 0.22rem 0.6rem;
  font-size: 0.78rem;
  font-weight: 600;
  border-radius: 20px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  transition: all 0.15s ease;
}

.chip-btn:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
}

.chip-btn.chip-active {
  background: #1b3d2f;
  color: #ffffff;
  border-color: #1b3d2f;
  box-shadow: 0 2px 6px rgba(27, 61, 47, 0.2);
}

.chip-icon {
  font-size: 0.85rem;
}

.chip-count {
  font-size: 0.72rem;
  opacity: 0.85;
}

/* Side Detail Taxonomy Additions */
.taxonomy-code-pill {
  background: #1e293b;
  color: #f8fafc;
  font-family: monospace;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  letter-spacing: 0.04em;
}

.cognitive-impact-card {
  background: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 10px;
  padding: 0.55rem 0.75rem;
  margin: 0;
  display: flex;
  gap: 0.55rem;
  align-items: flex-start;
}

.cog-icon {
  font-size: 1.25rem;
  line-height: 1;
}

.cog-text {
  font-size: 0.88rem;
  line-height: 1.45;
  color: #92400e;
}

.cog-text strong {
  display: block;
  font-weight: 800;
  margin-bottom: 0.2rem;
  color: #78350f;
}

/* ═══════════════════════════════════════════════════════════════
 * CIVIC FEEDBACK & ASSESSMENT HISTORY TRACKER
 * ═══════════════════════════════════════════════════════════════ */
.civic-history-container {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
}

.history-hero-header {
  margin-bottom: 0.5rem;
}

.history-badge {
  display: inline-block;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 0.82rem;
  font-weight: 800;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  margin-bottom: 0.5rem;
}

.history-title {
  margin: 0;
  font-size: 1.9rem;
  font-weight: 800;
  color: #0f172a;
}

.history-subtitle {
  margin: 0.4rem 0 0 0;
  font-size: 1.05rem;
  color: #64748b;
}

.history-controls-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}

.history-search-box {
  display: flex;
  align-items: center;
  position: relative;
  width: 100%;
}

.search-icon {
  position: absolute;
  left: 1rem;
  font-size: 1.1rem;
  color: #94a3b8;
}

.history-search-input {
  width: 100%;
  padding: 0.75rem 2.5rem 0.75rem 2.85rem;
  border: 1.5px solid #cbd5e1;
  border-radius: 10px;
  font-size: 0.95rem;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}

.history-search-input:focus {
  border-color: #1b3d2f;
  box-shadow: 0 0 0 3px rgba(27, 61, 47, 0.1);
}

.clear-search-btn {
  position: absolute;
  right: 0.75rem;
  background: #e2e8f0;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  color: #475569;
  cursor: pointer;
}

.history-filter-pills {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.hist-filter-pill {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.45rem 0.9rem;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.hist-filter-pill:hover {
  background: #f1f5f9;
}

.hist-filter-pill.pill-active {
  background: #1b3d2f;
  color: #ffffff;
  border-color: #1b3d2f;
}

.btn-refresh-history {
  margin-left: auto;
  background: #1b3d2f;
  border: 1.5px solid #1b3d2f;
  color: #ffffff;
  font-size: 0.85rem;
  font-weight: 700;
  padding: 0.45rem 0.85rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  box-shadow: 0 1px 4px rgba(27, 61, 47, 0.2);
}

.btn-refresh-history:hover {
  background: #14532d;
  border-color: #14532d;
}

/* History Cards Grid */
.history-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 1.25rem;
}

.history-report-card {
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  border-radius: 14px;
  padding: 1.4rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 1rem;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.03);
  transition: all 0.2s ease;
}

.history-report-card:hover {
  border-color: #94a3b8;
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06);
}

.report-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ref-badge-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.ref-pill {
  background: #f1f5f9;
  color: #334155;
  font-family: monospace;
  font-weight: 700;
  font-size: 0.82rem;
  padding: 0.2rem 0.5rem;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
}

.status-badge {
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
}

.status-sent {
  background: #dbeafe;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.status-acknowledged {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.status-under_review {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fde68a;
}

.status-saved {
  background: #f1f5f9;
  color: #334155;
  border: 1px solid #cbd5e1;
}

.space-type-tag {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border-radius: 6px;
}

.space-type-tag.private {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.space-type-tag.public {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #bae6fd;
}

.report-timestamp {
  font-size: 0.82rem;
  color: #64748b;
  font-weight: 600;
}

.report-card-main {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.report-council-name {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
}

.report-email-to {
  margin: 0;
  font-size: 0.86rem;
  color: #64748b;
}

.report-location {
  margin: 0.25rem 0 0 0;
  font-size: 0.95rem;
  color: #1e293b;
}

.facility-badge {
  background: #f1f5f9;
  color: #475569;
  font-size: 0.75rem;
  padding: 0.15rem 0.45rem;
  border-radius: 6px;
  margin-left: 0.4rem;
}

.report-barriers-row {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.barrier-count-badge {
  font-size: 0.85rem;
  font-weight: 700;
  color: #b45309;
}

.barrier-mini-pills {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.mini-cat-pill {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-size: 0.74rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 6px;
}

.mini-cat-more {
  font-size: 0.74rem;
  color: #94a3b8;
  padding: 0.15rem 0.3rem;
}

.report-card-actions {
  display: flex;
  gap: 0.6rem;
  margin-top: 0.5rem;
}

.btn-history-view {
  background: #1b3d2f;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 0.6rem 1rem;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.15s;
}

.btn-history-view:hover {
  background: #14532d;
}

.btn-history-ack {
  background: #1b3d2f;
  color: #ffffff;
  border: 1.5px solid #1b3d2f;
  border-radius: 8px;
  padding: 0.6rem 0.85rem;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  transition: all 0.15s;
  box-shadow: 0 1px 4px rgba(27, 61, 47, 0.2);
}

.btn-history-ack:hover {
  background: #14532d;
  border-color: #14532d;
  color: #ffffff;
}

/* History Empty & Loading states */
.history-empty-card,
.history-loading-box {
  background: #ffffff;
  border: 2px dashed #cbd5e1;
  border-radius: 16px;
  padding: 3.5rem 2rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.85rem;
}

.empty-icon {
  font-size: 3rem;
}

.history-empty-card h3 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: #334155;
}

.history-empty-card p {
  margin: 0;
  font-size: 0.98rem;
  color: #64748b;
  max-width: 480px;
}

/* Historical Archive Detail Dialog */
.history-detail-dialog {
  background: #ffffff;
  border-radius: 20px;
  max-width: 820px;
  width: 95%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
}

.history-meta-banner {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.85rem;
  font-size: 0.88rem;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.meta-item strong {
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
}

.history-letter-body {
  font-family: inherit;
  font-size: 0.92rem;
  line-height: 1.6;
  white-space: pre-wrap;
  color: #1e293b;
  background: #ffffff;
  margin: 0;
  padding: 1.25rem;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

@media (max-width: 1024px) {
  .audit-workspace-layout {
    flex-direction: column;
    align-items: center;
    gap: 1.25rem;
  }
  .workspace-image-container,
  .interactive-viewer,
  .overlay-canvas {
    max-height: 48vh;
    width: 100%;
  }
  .workspace-side-panel {
    width: 100%;
    max-width: 600px;
    flex: 1 1 auto;
  }
  .side-detail-card,
  .side-overview-card {
    max-height: 52vh;
  }
}

@media (max-width: 640px) {
  .auditor-page {
    padding: 0.85rem 0.75rem;
  }
  .result-space-badge-row {
    flex-direction: column;
    align-items: stretch;
    gap: 0.5rem;
  }
  .result-badge-left,
  .result-badge-right {
    width: 100%;
    justify-content: space-between;
  }
  .dashboard-title-group {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.35rem;
  }
  .dashboard-title {
    font-size: 1.2rem;
  }
  .workspace-image-container,
  .interactive-viewer,
  .overlay-canvas {
    max-height: 40vh;
  }
  .workspace-side-panel,
  .side-detail-card,
  .side-overview-card {
    max-height: 54vh;
    padding: 1rem;
  }
}
</style>
