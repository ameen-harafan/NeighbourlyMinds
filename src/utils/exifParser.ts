/**
 * Pure TypeScript EXIF GPS Metadata Extractor
 * Extracts GPS latitude and longitude from uploaded photo files without external dependencies.
 * Automatically detects photo location coordinates for local council resolution.
 */

export interface ExifGpsCoordinates {
  latitude: number
  longitude: number
  hasGps: boolean
  source: 'exif' | 'geolocation' | 'preset'
}

/**
 * Extracts GPS coordinates from a JPEG/TIFF File or Blob.
 */
export async function extractExifGpsFromBlob(file: Blob): Promise<ExifGpsCoordinates | null> {
  try {
    const buffer = await file.arrayBuffer()
    const view = new DataView(buffer)

    // Check for JPEG SOI marker (0xFFD8)
    if (view.getUint16(0, false) !== 0xFFD8) {
      return null
    }

    let offset = 2
    const length = view.byteLength

    while (offset < length) {
      if (view.getUint8(offset) !== 0xFF) {
        break
      }

      const marker = view.getUint8(offset + 1)

      // APP1 marker (0xFFE1) contains EXIF metadata
      if (marker === 0xE1) {
        const app1Length = view.getUint16(offset + 2, false)
        const exifHeader = view.getUint32(offset + 4, false)
        // Check for 'Exif' ASCII (0x45786966)
        if (exifHeader === 0x45786966) {
          const tiffOffset = offset + 10
          return parseTiffGps(view, tiffOffset)
        }
        offset += 2 + app1Length
      } else if ((marker >= 0xE0 && marker <= 0xEF) || marker === 0xFE) {
        const segmentLength = view.getUint16(offset + 2, false)
        offset += 2 + segmentLength
      } else if (marker === 0xDA) {
        // Start of Scan marker - EXIF always comes before SOS
        break
      } else {
        offset += 2
      }
    }

    return null
  } catch (err) {
    console.warn('[ExifParser] Could not parse EXIF GPS:', err)
    return null
  }
}

function parseTiffGps(view: DataView, tiffOffset: number): ExifGpsCoordinates | null {
  const byteOrder = view.getUint16(tiffOffset, false)
  const littleEndian = byteOrder === 0x4949 // 'II'

  const firstIfdOffset = view.getUint32(tiffOffset + 4, littleEndian)
  const ifd0Offset = tiffOffset + firstIfdOffset

  const numEntries = view.getUint16(ifd0Offset, littleEndian)
  let gpsIfdOffset = 0

  for (let i = 0; i < numEntries; i++) {
    const entryOffset = ifd0Offset + 2 + i * 12
    if (entryOffset + 12 > view.byteLength) break
    const tag = view.getUint16(entryOffset, littleEndian)

    // 0x8825 = GPSInfo IFD Pointer
    if (tag === 0x8825) {
      gpsIfdOffset = tiffOffset + view.getUint32(entryOffset + 8, littleEndian)
      break
    }
  }

  if (!gpsIfdOffset || gpsIfdOffset + 2 > view.byteLength) {
    return null
  }

  const gpsEntries = view.getUint16(gpsIfdOffset, littleEndian)
  let latRef = 'N'
  let lonRef = 'E'
  let rawLat: number[] | null = null
  let rawLon: number[] | null = null

  for (let i = 0; i < gpsEntries; i++) {
    const entryOffset = gpsIfdOffset + 2 + i * 12
    if (entryOffset + 12 > view.byteLength) break
    const tag = view.getUint16(entryOffset, littleEndian)

    if (tag === 1) { // GPSLatitudeRef
      latRef = String.fromCharCode(view.getUint8(entryOffset + 8))
    } else if (tag === 2) { // GPSLatitude
      const valOffset = tiffOffset + view.getUint32(entryOffset + 8, littleEndian)
      rawLat = readRationalCoords(view, valOffset, littleEndian)
    } else if (tag === 3) { // GPSLongitudeRef
      lonRef = String.fromCharCode(view.getUint8(entryOffset + 8))
    } else if (tag === 4) { // GPSLongitude
      const valOffset = tiffOffset + view.getUint32(entryOffset + 8, littleEndian)
      rawLon = readRationalCoords(view, valOffset, littleEndian)
    }
  }

  if (rawLat && rawLon && rawLat.length >= 3 && rawLon.length >= 3) {
    const lat0 = rawLat[0] ?? 0
    const lat1 = rawLat[1] ?? 0
    const lat2 = rawLat[2] ?? 0
    const lon0 = rawLon[0] ?? 0
    const lon1 = rawLon[1] ?? 0
    const lon2 = rawLon[2] ?? 0
    let lat = lat0 + lat1 / 60 + lat2 / 3600
    let lon = lon0 + lon1 / 60 + lon2 / 3600

    if (latRef.toUpperCase() === 'S') lat = -lat
    if (lonRef.toUpperCase() === 'W') lon = -lon

    return {
      latitude: Number(lat.toFixed(6)),
      longitude: Number(lon.toFixed(6)),
      hasGps: true,
      source: 'exif'
    }
  }

  return null
}

function readRationalCoords(view: DataView, offset: number, littleEndian: boolean): number[] | null {
  if (offset + 24 > view.byteLength) return null
  const dNum = view.getUint32(offset, littleEndian)
  const dDen = view.getUint32(offset + 4, littleEndian) || 1
  const mNum = view.getUint32(offset + 8, littleEndian)
  const mDen = view.getUint32(offset + 12, littleEndian) || 1
  const sNum = view.getUint32(offset + 16, littleEndian)
  const sDen = view.getUint32(offset + 20, littleEndian) || 1

  return [dNum / dDen, mNum / mDen, sNum / sDen]
}

/**
 * Standard Victorian Public Corridor Location Presets
 * Allows users to quickly test or audit recognizable Victorian public facilities.
 */
export const VICTORIAN_PUBLIC_LOCATION_PRESETS = [
  {
    name: 'Melbourne City Library & Flinder St Station Corridor',
    suburb: 'Melbourne',
    council: 'Melbourne City Council',
    lat: -37.8180,
    lng: 144.9671,
    facilityType: 'Transit & Civic Corridor'
  },
  {
    name: 'State Library Victoria Municipal Hallway (Swanston St)',
    suburb: 'Melbourne',
    council: 'Melbourne City Council',
    lat: -37.8098,
    lng: 144.9652,
    facilityType: 'Public Library Entry'
  },
  {
    name: 'Fitzroy Town Hall Public Walkway (Napier St)',
    suburb: 'Fitzroy',
    council: 'Yarra City Council',
    lat: -37.7997,
    lng: 144.9789,
    facilityType: 'Civic Hallway'
  },
  {
    name: 'St Kilda Town Hall & Public Library Foyer',
    suburb: 'St Kilda',
    council: 'Port Phillip City Council',
    lat: -37.8679,
    lng: 144.9821,
    facilityType: 'Municipal Entrance'
  },
  {
    name: 'Geelong City Hall & Johnstone Park Public Concourse',
    suburb: 'Geelong',
    council: 'Greater Geelong City Council',
    lat: -38.1472,
    lng: 144.3578,
    facilityType: 'Regional Municipal Hub'
  },
  {
    name: 'Ballarat Town Hall & Sturt St Civic Passage',
    suburb: 'Ballarat',
    council: 'Ballarat City Council',
    lat: -37.5615,
    lng: 143.8580,
    facilityType: 'Historic Civic Concourse'
  }
]
