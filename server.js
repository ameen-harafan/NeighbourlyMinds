import crypto from "crypto";
import express from "express";
import cors from "cors";
import pool from "./db.js";
import multer from "multer";
import axios from "axios";
import FormData from "form-data";
import PDFDocument from "pdfkit";
import helmet from "helmet";
import { drawFoldingPocketCard } from "./lib/pocketCardPdf.js";
import {
  corsOptions,
  generalLimiter,
  reportLimiter,
  uploadLimiter,
  pdfLimiter,
  siteAccessLimiter,
  sendServerError,
  secretsMatch,
  requireAdminToken,
  ALLOWED_IMAGE_TYPES,
  MAX_UPLOAD_BYTES,
  looksLikeImage,
} from "./lib/security.js";
import {
  DAYS,
  SPACE_TYPES,
  parseLatitude,
  parseLongitude,
  cleanText,
  cleanLongText,
  isValidLgaName,
  isValidReferenceId,
  isValidEmail,
  isValidPostcode,
  normaliseStatus,
  safeFileName,
} from "./lib/validators.js";

const isProduction = process.env.NODE_ENV === "production";

const app = express();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: MAX_UPLOAD_BYTES, files: 1 },
  fileFilter(req, file, callback) {
    const isAllowedMime = file.mimetype && ALLOWED_IMAGE_TYPES.includes(file.mimetype);
    const hasImageExt = /\.(jpe?g|png|webp|heic|heif)$/i.test(file.originalname);
    if (!isAllowedMime && !hasImageExt) {
      return callback(new multer.MulterError("LIMIT_UNEXPECTED_FILE", "image"));
    }
    return callback(null, true);
  },
});

// nginx sits in front of the API, so trust one proxy hop for the real client IP (rate limits).
app.set("trust proxy", 1);
app.use(helmet());
app.use(cors(corsOptions));
app.use(express.json({ limit: "200kb" }));
app.use("/api/", generalLimiter);

if (!isProduction) {
  app.get("/test-db", async (req, res) => {
    try {
      const result = await pool.query(
        "SELECT COUNT(*) FROM lga_dementia_estimates"
      );

      res.json({
        message: "Database connected successfully",
        rowCount: result.rows[0].count,
      });
    } catch (error) {
      sendServerError(res, "Database connection failed", error, "test-db");
    }
  });
}

app.post("/api/site-access", siteAccessLimiter, (req, res) => {
  const expected = process.env.SITE_ACCESS_PASSWORD;
  if (!expected) {
    return res.status(503).json({ error: "Site access is not set up yet. Please contact the team." });
  }
  if (!secretsMatch(req.body?.password, expected)) {
    return res.status(401).json({ error: "Incorrect password. Please try again." });
  }
  return res.json({ success: true });
});

app.get("/api/councils", async (req, res) => {
  try {
    const result = await pool.query(
      "SELECT DISTINCT lga_name FROM lga_dementia_estimates ORDER BY lga_name"
    );
    res.json(result.rows);
  } catch (error) {
    sendServerError(res, "Unable to load council list. Please try again.", error, "councils");
  }
});

app.get("/api/councils/:lgaName/dementia", async (req, res) => {
  try {
    const { lgaName } = req.params;
    if (!isValidLgaName(lgaName)) {
      return res.status(400).json({ error: "Please choose a council from the list." });
    }

    const result = await pool.query(
      `
      SELECT
        lga_code,
        lga_name,
        modelled_estimate,
        rounded_estimate
      FROM lga_dementia_estimates
      WHERE lga_name = $1
      `,
      [lgaName]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        message: "LGA not found",
      });
    }

    res.json(result.rows[0]);
  } catch (error) {
    sendServerError(res, "Unable to load dementia estimate. Please try again.", error, "dementia-estimate");
  }
});

app.get("/api/councils/contacts", async (req, res) => {
  try {
    const result = await pool.query(
      "SELECT * FROM council_contacts ORDER BY council_name"
    );
    res.json(result.rows);
  } catch (error) {
    sendServerError(res, "Unable to load council contacts. Please try again.", error, "council-contacts");
  }
});

app.get("/api/councils/:lgaName/contact", async (req, res) => {
  try {
    const { lgaName } = req.params;
    if (!isValidLgaName(lgaName)) {
      return res.status(400).json({ error: "Please choose a council from the list." });
    }
    // Strip trailing suffixes like ' (Vic.)' or ' City Council' if user provides simplified name
    const cleanTerm = lgaName.replace(/\s*\(Vic\.\)\s*$/i, "").trim();

    const result = await pool.query(
      `SELECT * FROM council_contacts 
       WHERE LOWER(council_name) LIKE LOWER($1)
       LIMIT 1`,
      [`%${cleanTerm}%`]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ message: "Council contact not found" });
    }

    res.json(result.rows[0]);
  } catch (error) {
    sendServerError(res, "Unable to load council contact. Please try again.", error, "council-contact");
  }
});

// Search councils by name, postal suburb, or postcode
app.get("/api/councils/search", async (req, res) => {
  try {
    const q = cleanText(req.query.q, 60);
    if (!q) {
      const result = await pool.query(
        "SELECT * FROM council_contacts ORDER BY council_name LIMIT 20"
      );
      return res.json(result.rows);
    }

    const result = await pool.query(
      `SELECT * FROM council_contacts 
       WHERE LOWER(council_name) LIKE LOWER($1) 
          OR LOWER(postal_suburb) LIKE LOWER($1)
          OR postcode LIKE $1
       ORDER BY council_name`,
      [`%${q}%`]
    );
    res.json(result.rows);
  } catch (error) {
    sendServerError(res, "Search is not available right now. Please try again later.", error, "council-search");
  }
});

// AC 6.2.1: Victorian LGA Directory Geocoding Resolver
// Resolves GPS point-in-polygon against Victorian LGA boundary shapefiles and returns municipal council contact
app.get("/api/councils/geocode", geocodeHandler);
app.post("/api/councils/geocode", geocodeHandler);

async function geocodeHandler(req, res) {
  try {
    const rawLat = req.query.lat ?? req.body?.lat ?? req.query.latitude ?? req.body?.latitude;
    const rawLng = req.query.lng ?? req.body?.lng ?? req.query.lon ?? req.query.longitude ?? req.body?.longitude;
    const lat = parseLatitude(rawLat);
    const lng = parseLongitude(rawLng);
    const suburb = cleanText(req.query.suburb ?? req.body?.suburb, 60);
    const postcode = String(req.query.postcode ?? req.body?.postcode ?? "").trim();

    const coordsSent = rawLat !== undefined || rawLng !== undefined;
    if (coordsSent && (lat === null || lng === null)) {
      return res.status(400).json({ error: "Location is not valid. Please try again or choose your council." });
    }
    if (postcode && !isValidPostcode(postcode)) {
      return res.status(400).json({ error: "Postcode must be 4 digits." });
    }

    // 1. Point-in-polygon lookup if valid coordinates provided
    if (lat !== null && lng !== null) {
      // Primary: ST_Contains point in polygon
      const containQuery = `
        SELECT 
          b.lga_code_2025, 
          b.lga_name_2025, 
          b.area_albers_sqkm,
          c.council_name,
          c.ceo_name,
          c.mayor_name,
          c.deputy_mayor_name,
          c.telephone,
          c.email,
          c.website,
          c.postal_address,
          c.postal_suburb,
          c.postcode
        FROM lga_boundaries_victoria b
        LEFT JOIN council_contacts c ON LOWER(c.council_name) LIKE LOWER('%' || b.lga_name_2025 || '%')
        WHERE ST_Contains(b.wkb_geometry, ST_SetSRID(ST_Point($1, $2), 4326))
        LIMIT 1;
      `;
      let geoRes = await pool.query(containQuery, [lng, lat]);

      // Secondary: If slightly outside polygon boundary (e.g. coastal edge or margin), find nearest LGA
      if (geoRes.rows.length === 0) {
        const nearestQuery = `
          SELECT 
            b.lga_code_2025, 
            b.lga_name_2025, 
            b.area_albers_sqkm,
            c.council_name,
            c.ceo_name,
            c.mayor_name,
            c.deputy_mayor_name,
            c.telephone,
            c.email,
            c.website,
            c.postal_address,
            c.postal_suburb,
            c.postcode
          FROM lga_boundaries_victoria b
          LEFT JOIN council_contacts c ON LOWER(c.council_name) LIKE LOWER('%' || b.lga_name_2025 || '%')
          ORDER BY ST_Distance(b.wkb_geometry, ST_SetSRID(ST_Point($1, $2), 4326))
          LIMIT 1;
        `;
        geoRes = await pool.query(nearestQuery, [lng, lat]);
      }

      if (geoRes.rows.length > 0) {
        const row = geoRes.rows[0];
        return res.json({
          success: true,
          method: "point-in-polygon",
          lgaName: row.lga_name_2025,
          lgaCode: row.lga_code_2025,
          coordinates: { latitude: lat, longitude: lng },
          council: {
            council_name: row.council_name || `${row.lga_name_2025} Council`,
            email: row.email || "enquiries@vic.gov.au",
            telephone: row.telephone || "1300 366 356",
            ceo_name: row.ceo_name,
            mayor_name: row.mayor_name,
            deputy_mayor_name: row.deputy_mayor_name,
            website: row.website,
            postal_address: row.postal_address,
            postal_suburb: row.postal_suburb,
            postcode: row.postcode
          }
        });
      }
    }

    // 2. Suburb / Postcode text search fallback
    if (suburb || postcode) {
      const subQuery = `
        SELECT * FROM council_contacts
        WHERE LOWER(postal_suburb) = LOWER($1) 
           OR postcode = $2
           OR LOWER(council_name) LIKE LOWER($3)
        LIMIT 1;
      `;
      const subRes = await pool.query(subQuery, [suburb, postcode, `%${suburb}%`]);
      if (subRes.rows.length > 0) {
        const c = subRes.rows[0];
        return res.json({
          success: true,
          method: "suburb-lookup",
          lgaName: c.council_name.replace(/\s*(City|Shire|Rural City)?\s*Council.*$/i, ""),
          council: c
        });
      }
    }

    // Default fallback to Melbourne City Council
    const defaultRes = await pool.query("SELECT * FROM council_contacts WHERE LOWER(council_name) LIKE '%melbourne%' LIMIT 1");
    return res.json({
      success: true,
      method: "default-fallback",
      lgaName: "Melbourne",
      council: defaultRes.rows[0]
    });
  } catch (error) {
    sendServerError(res, "Unable to find your council right now. Please choose it from the list.", error, "geocode");
  }
}

// Submit / Dispatch accessibility feedback report to local council
app.post("/api/councils/send-report", reportLimiter, async (req, res) => {
  try {
    const body = req.body || {};
    const councilName = cleanText(body.councilName, 120);
    const councilEmail = body.councilEmail ? String(body.councilEmail).trim() : "";
    const senderName = cleanText(body.senderName, 80);
    const senderEmail = body.senderEmail ? String(body.senderEmail).trim() : "";
    const locationName = cleanText(body.locationName, 120);
    const emailSubject = cleanText(body.emailSubject, 150);
    const emailBody = cleanLongText(body.emailBody, 20000);
    const spaceType = body.spaceType ? String(body.spaceType).toLowerCase() : "";
    const barrierSummary = body.barrierSummary;

    if (!emailBody.trim()) {
      return res.status(400).json({ error: "Report text is empty. Please add some details before saving." });
    }
    if (spaceType && !SPACE_TYPES.includes(spaceType)) {
      return res.status(400).json({ error: "Space type must be public or private." });
    }
    if ((councilEmail && !isValidEmail(councilEmail)) || (senderEmail && !isValidEmail(senderEmail))) {
      return res.status(400).json({ error: "Please enter a valid email address." });
    }
    if (barrierSummary !== undefined && (!Array.isArray(barrierSummary) || barrierSummary.length > 50)) {
      return res.status(400).json({ error: "Barrier list is not valid." });
    }

    const resolvedSpaceType = spaceType || (councilName && councilName.toLowerCase().includes('private') ? 'private' : 'public');
    const referencePrefix = resolvedSpaceType === 'private' ? 'HOME' : 'AUDIT';
    const referenceId = `${referencePrefix}-${Date.now().toString(36).toUpperCase()}-${crypto.randomInt(1000, 10000)}`;

    // New reports can only start as SAVED or SENT. Council statuses are set later.
    const reportStatus = normaliseStatus(body.status) === "SENT" ? "SENT" : "SAVED";
    const finalCouncilName = councilName || (resolvedSpaceType === 'private' ? 'Private Residence Assessment' : 'Victorian Municipal Council');
    const finalCouncilEmail = councilEmail || (resolvedSpaceType === 'private' ? 'caregiver@home.local' : 'enquiries@vic.gov.au');
    const finalSenderName = senderName || (resolvedSpaceType === 'private' ? 'Resident / Family' : 'Community Member');
    const finalLocationName = locationName || (resolvedSpaceType === 'private' ? 'Home Room' : 'Public Space');

    const insertRes = await pool.query(
      `INSERT INTO accessibility_reports (
        reference_id, space_type, council_name, council_email, sender_name,
        sender_email, location_name, barrier_summary, email_subject, email_body, status
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
      RETURNING *`,
      [
        referenceId,
        resolvedSpaceType,
        finalCouncilName,
        finalCouncilEmail,
        finalSenderName,
        senderEmail || '',
        finalLocationName,
        JSON.stringify(barrierSummary || []),
        emailSubject || (resolvedSpaceType === 'private' ? 'Home Accessibility & Renovation Plan' : 'Accessibility Barrier Report'),
        emailBody,
        reportStatus
      ]
    );

    console.log(`[Audit Hub] Recorded accessibility report ${referenceId} (${resolvedSpaceType})`);

    res.status(201).json({
      success: true,
      referenceId,
      report: insertRes.rows[0],
      message: `Accessibility report #${referenceId} recorded.`
    });
  } catch (error) {
    sendServerError(res, "Unable to save your report. Please try again.", error, "send-report");
  }
});

// The history list is not tied to a login, so the sender's email is never sent back.
function toPublicReport(row) {
  const { sender_email, ...rest } = row;
  let parsedBarriers = [];
  if (typeof rest.barrier_summary === "string") {
    try {
      parsedBarriers = JSON.parse(rest.barrier_summary);
    } catch (e) {
      parsedBarriers = [];
    }
  } else if (Array.isArray(rest.barrier_summary)) {
    parsedBarriers = rest.barrier_summary;
  }

  return {
    ...rest,
    barrier_summary: parsedBarriers,
    barrier_count: parsedBarriers.length
  };
}

// AC 6.2.3: Civic Feedback History Tracker Endpoints
// Retrieve filed accessibility reports with optional search and status filtering
app.get("/api/councils/reports", async (req, res) => {
  try {
    const rawStatus = req.query.status;
    const search = cleanText(req.query.search, 60);
    let query = "SELECT * FROM accessibility_reports WHERE 1=1";
    const params = [];

    if (rawStatus && rawStatus !== "ALL") {
      const status = normaliseStatus(rawStatus);
      if (!status) {
        return res.status(400).json({ error: "Status filter is not valid." });
      }
      params.push(status);
      query += ` AND UPPER(status) = $${params.length}`;
    }

    if (search) {
      params.push(`%${search.toLowerCase()}%`);
      query += ` AND (
        LOWER(reference_id) LIKE $${params.length} OR 
        LOWER(council_name) LIKE $${params.length} OR 
        LOWER(location_name) LIKE $${params.length} OR
        LOWER(sender_name) LIKE $${params.length}
      )`;
    }

    query += " ORDER BY created_at DESC LIMIT 100";

    const result = await pool.query(query, params);
    res.json(result.rows.map(toPublicReport));
  } catch (error) {
    sendServerError(res, "Unable to load report history. Please try again.", error, "report-history");
  }
});

// Retrieve single accessibility report details by reference ID
app.get("/api/councils/reports/:refId", async (req, res) => {
  try {
    const { refId } = req.params;
    if (!isValidReferenceId(refId)) {
      return res.status(400).json({ error: "Reference number is not valid." });
    }
    const result = await pool.query(
      "SELECT * FROM accessibility_reports WHERE reference_id = $1 LIMIT 1",
      [refId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: "Report not found" });
    }

    res.json(toPublicReport(result.rows[0]));
  } catch (error) {
    sendServerError(res, "Unable to load this report. Please try again.", error, "report-detail");
  }
});

// Update report status (e.g. simulate council response: ACKNOWLEDGED, UNDER_REVIEW)
app.patch("/api/councils/reports/:refId/status", reportLimiter, async (req, res) => {
  try {
    const { refId } = req.params;
    if (!isValidReferenceId(refId)) {
      return res.status(400).json({ error: "Reference number is not valid." });
    }
    const status = normaliseStatus(req.body?.status);
    if (!status) {
      return res.status(400).json({ error: "Status is not valid." });
    }

    const result = await pool.query(
      "UPDATE accessibility_reports SET status = $1 WHERE reference_id = $2 RETURNING *",
      [status, refId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: "Report not found" });
    }

    res.json({ success: true, updated: toPublicReport(result.rows[0]) });
  } catch (error) {
    sendServerError(res, "Unable to update report status. Please try again.", error, "report-status");
  }
});

// Delete a submission from the log (team/admin use only, not called by the frontend)
app.delete("/api/councils/reports/:refId", requireAdminToken, async (req, res) => {
  try {
    const { refId } = req.params;
    if (!isValidReferenceId(refId)) {
      return res.status(400).json({ error: "Reference number is not valid." });
    }
    const result = await pool.query(
      "DELETE FROM accessibility_reports WHERE reference_id = $1 RETURNING id, reference_id",
      [refId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: "Report not found" });
    }

    res.json({ success: true, deleted: result.rows[0] });
  } catch (error) {
    sendServerError(res, "Unable to delete this report. Please try again.", error, "report-delete");
  }
});

app.get("/api/landmarks", async (req, res) => {
  try {
    const result = await pool.query("SELECT * FROM landmarks");
    res.json(result.rows);
  } catch (error) {
    sendServerError(res, "Unable to load landmarks. Please try again.", error, "landmarks");
  }
});

app.get("/api/toilets", async (req, res) => {
  try {
    const result = await pool.query("SELECT * FROM public_toilets");
    res.json(result.rows);
  } catch (error) {
    sendServerError(res, "Unable to load public toilets. Please try again.", error, "toilets");
  }
});

// Official City of Melbourne & Victorian Regional Sensory Registry (DMP Sec 3.2)
const SENSOR_REGISTRY = [
  { id: "ICTMicroclimate-01", name: "Birrarung Marr Park Sensor", location: "Birrarung Marr Park", lat: -37.8185931, lon: 144.9716404, category: "park", noiseOffset: -4.0, tipBase: "Natural parkland soundscape with tree shade and river breezes" },
  { id: "ICTMicroclimate-02", name: "Lincoln Square Microclimate Sensor", location: "Lincoln Square, Carlton", lat: -37.8016, lon: 144.9628, category: "park", noiseOffset: -3.5, tipBase: "Quiet open square with shaded benches away from arterial traffic" },
  { id: "ICTMicroclimate-03", name: "Argyle Square Microclimate Sensor", location: "Argyle Square, Carlton", lat: -37.8025, lon: 144.9672, category: "park", noiseOffset: -3.2, tipBase: "Shaded park pathways with gentle neighborhood activity" },
  { id: "ICTMicroclimate-04", name: "Melbourne Town Hall Civic Sensor", location: "Swanston St / Collins St", lat: -37.8150, lon: 144.9665, category: "civic", noiseOffset: 1.5, tipBase: "Central civic boulevard with accessible seating and clear sightlines" },
  { id: "ICTMicroclimate-05", name: "State Library Victoria Sensor", location: "Swanston St Forecourt", lat: -37.8098, lon: 144.9652, category: "library", noiseOffset: -1.5, tipBase: "Quiet indoor reading areas and sheltered forecourt seating" },
  { id: "ICTMicroclimate-06", name: "Flinders St Station Precinct Sensor", location: "Flinders St Pedestrian Hub", lat: -37.8183, lon: 144.9671, category: "transit", noiseOffset: 2.5, tipBase: "Major transit concourse, best accessed during morning quiet lulls" },
  { id: "ICTMicroclimate-07", name: "Docklands Waterfront Sensor", location: "Victoria Harbour Promenade", lat: -37.8188, lon: 144.9471, category: "waterfront", noiseOffset: -2.0, tipBase: "Wide, open waterside boardwalks with low echo and calm views" },
  { id: "ICTMicroclimate-08", name: "Carlton Gardens Nature Sensor", location: "Carlton Gardens East", lat: -37.8052, lon: 144.9714, category: "park", noiseOffset: -4.5, tipBase: "Tranquil botanical gardens with wide, tree-lined walking paths" },
  { id: "ICTMicroclimate-09", name: "Southbank Promenade Sensor", location: "Yarra River Walkway", lat: -37.8205, lon: 144.9635, category: "commercial", noiseOffset: 1.2, tipBase: "Riverside pedestrian concourse with level walking surfaces" },
  { id: "ICTMicroclimate-10", name: "Chinatown Precinct Sensor", location: "Little Bourke St Corridor", lat: -37.8122, lon: 144.9685, category: "retail", noiseOffset: 1.8, tipBase: "Pedestrian corridor with early morning calm before dining crowds" },
  { id: "ICTMicroclimate-11", name: "Lygon St Dining Corridor Sensor", location: "Lygon St Italian Precinct", lat: -37.8005, lon: 144.9669, category: "commercial", noiseOffset: 1.0, tipBase: "Tree-lined pavement cafe strip, quietest before lunch service" },
  // Regional Frankston cluster
  { id: "Frankston-01", name: "Frankston Civic Centre Sensor #01", location: "Playne St Civic Precinct", lat: -38.1428, lon: 145.1225, category: "library", noiseOffset: -1.8, tipBase: "Quiet indoor reading corners and sheltered civic courtyard seating" },
  { id: "Frankston-02", name: "Bayside Centre Sensor #02", location: "Beach St Commercial Corridor", lat: -38.1442, lon: 145.1245, category: "commercial", noiseOffset: 3.5, tipBase: "Air-conditioned shopping corridors, quieter near South entrance" },
  { id: "Frankston-03", name: "Wells St Mall Sensor #03", location: "Wells St Pedestrian Mall", lat: -38.1435, lon: 145.1215, category: "retail", noiseOffset: 0.8, tipBase: "Pedestrian mall with seated dispensary waiting area" },
  { id: "Frankston-04", name: "Beach St Healthcare Sensor #04", location: "Beach St Healthcare Hub", lat: -38.1450, lon: 145.1260, category: "medical", noiseOffset: -2.2, tipBase: "Low-sensory waiting area, minimal street traffic noise" },
  { id: "Frankston-05", name: "Beauty Park Soundscape Sensor #05", location: "Spring St Lake Pavilion", lat: -38.1485, lon: 145.1275, category: "park", noiseOffset: -4.5, tipBase: "Natural soundscape, mature tree canopy shade, and lakeside seating" }
];

function haversineDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

// Epic 4: Daytime Sensory & Microclimate Schedule (9:00 AM – 5:00 PM)
app.get(["/api/sensory/schedule", "/api/sensory/daytime-schedule"], async (req, res) => {
  try {
    const rawDestination = cleanText(req.query.destination, 100) || "Frankston Library (Playne St)";
    const selectedDay = DAYS.includes(String(req.query.day)) ? String(req.query.day) : "Tuesday";
    const destLower = rawDestination.toLowerCase();

    const hasLat = req.query.lat !== undefined && req.query.lat !== "";
    const hasLon = req.query.lon !== undefined && req.query.lon !== "";
    const parsedLat = parseLatitude(req.query.lat);
    const parsedLon = parseLongitude(req.query.lon);
    if ((hasLat && parsedLat === null) || (hasLon && parsedLon === null)) {
      return res.status(400).json({ error: "Location is not valid. Please choose the place again." });
    }

    const queryLat = parsedLat ?? -37.8136; // Default to Civic Centre if missing
    const queryLon = parsedLon ?? 144.9631;

    // 1. Base initialization
    let isDbLive = false;
    let schedule = [];
    let matchedSensorInfo = {
      name: "Local Microclimate Sensor",
      location: "Nearest Monitoring Station",
      distanceMeters: 0,
      category: "general"
    };

    // 2. Query PostgreSQL PostGIS sensory schedule function

    try {
      const qRes = await pool.query(
        `SELECT * FROM get_destination_sensory_schedule($1, $2)`,
        [queryLon, queryLat]
      );
      if (qRes && qRes.rows && qRes.rows.length === 9) {
        isDbLive = true;
        matchedSensorInfo = {
          name: qRes.rows[0].sensor_source.split(" (")[0] || "Unknown Sensor",
          location: "Nearest Registered Sensor",
          distanceMeters: Number(qRes.rows[0].sensor_distance_meters) || 0,
          category: "general"
        };

        schedule = qRes.rows.map((r) => {
          const db = Number(Number(r.decibels).toFixed(1));
          const ped = Number(r.pedestrian_count);
          const noiseTier = db < 55 ? "Low" : db <= 62 ? "Moderate" : "High";
          const crowdTier = ped < 500 ? "Light" : ped <= 750 ? "Moderate" : "Busy";

          return {
            hour: Number(r.hour),
            label: r.label,
            window: r.window,
            decibels: db,
            noise: noiseTier,
            pedestrianCount: ped,
            crowd: crowdTier,
            sensorSource: r.sensor_source,
            isRecommended: false,
            tip: ""
          };
        });
      }
    } catch (e) {
      console.warn("[sensory-schedule] query unavailable:", e.message);
    }

    if (!isDbLive || schedule.length === 0) {
      return res.status(503).json({ error: "Noise and crowd information is not available for this place right now. Please try again later." });
    }

    // 4. Dynamic Quietest Hour Calculation:
    // Determine quietest hour based on lowest combined sensory score (60% acoustic + 40% crowd load)
    let bestScore = Infinity;
    let quietestHour = 10;

    schedule.forEach((item) => {
      const score = Number(item.decibels) * 0.6 + (Number(item.pedestrianCount) / 20) * 0.4;
      if (score < bestScore) {
        bestScore = score;
        quietestHour = item.hour;
      }
    });

    // Mark the dynamic quietest hour and contextualize reassurance tips
    schedule.forEach((item) => {
      const isQuiet = item.hour === quietestHour;
      item.isRecommended = isQuiet;
      item.tip = isQuiet
        ? `★ Quietest Choice: Best conditions for minimizing sensory overload (${item.window})`
        : `Normal active conditions for this precinct.`;
    });

    res.json({
      success: true,
      destination: rawDestination,
      matchedSensor: matchedSensorInfo,
      schedule,
      recommendedHour: quietestHour,
      isLive: isDbLive,
      dataSource: isDbLive
        ? "PostgreSQL PostGIS (noise_hourly & pedestrian_clean)"
        : "City of Melbourne Empirical Open Data"
    });
  } catch (error) {
    sendServerError(res, "Unable to load the noise and crowd schedule. Please try again.", error, "sensory-schedule");
  }
});

app.get("/api/routes/straight", async (req, res) => {
  try {
    const start_lon = parseLongitude(req.query.start_lon);
    const start_lat = parseLatitude(req.query.start_lat);
    const end_lon = parseLongitude(req.query.end_lon);
    const end_lat = parseLatitude(req.query.end_lat);

    if ([start_lon, start_lat, end_lon, end_lat].includes(null)) {
      return res.status(400).json({ error: "Start or destination location is missing or not valid." });
    }

    // 1. Get the straightest path geometries
    const routeResult = await pool.query(`
      SELECT ST_AsGeoJSON(ST_SetSRID(merged, 4326)) as geojson, ST_SetSRID(merged, 4326) as full_geom
      FROM (
        SELECT ST_LineMerge(ST_Collect(geom ORDER BY seq)) AS merged
        FROM get_straight_route($1, $2, $3, $4)
      ) sub;
    `, [start_lon, start_lat, end_lon, end_lat]);

    if (!routeResult.rows[0]?.full_geom) {
      return res.status(404).json({ error: "No route found" });
    }

    const routeGeomHex = routeResult.rows[0].full_geom;
    const geojson = JSON.parse(routeResult.rows[0].geojson);

    // 2. Get comfort statistics (shade and benches)
    const comfortResult = await pool.query(`
      SELECT * FROM get_route_comfort_stats($1::geometry);
    `, [routeGeomHex]);

    // 3. Get visual landmarks checklist
    const landmarksResult = await pool.query(`
      SELECT * FROM get_route_landmarks($1::geometry);
    `, [routeGeomHex]);

    res.json({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: geojson,
          properties: {
            shade_percentage: comfortResult.rows[0]?.shade_percentage || 0,
            bench_count: comfortResult.rows[0]?.bench_count || 0,
            landmarks: landmarksResult.rows
          }
        }
      ]
    });
  } catch (error) {
    sendServerError(res, "Unable to plan this walking route right now. Please try again.", error, "route-straight");
  }
});

app.post("/api/pdf/pocket-card", pdfLimiter, (req, res) => {
  try {
    const routeId = safeFileName(req.body?.routeId, "route");
    const doc = new PDFDocument({ size: "A4", margin: 0 });

    res.setHeader("Content-Type", "application/pdf");
    res.setHeader("Content-Disposition", `attachment; filename="pocket-card-${routeId}.pdf"`);

    doc.pipe(res);
    drawFoldingPocketCard(doc, req.body || {});
    doc.end();
  } catch (error) {
    console.error("[pocket-card]", error.message);
    if (!res.headersSent) {
      res.status(500).json({ error: "Unable to make the pocket card right now. Please try again." });
    } else {
      res.end();
    }
  }
});

const PORT = Number(process.env.PORT) || 3000;

function handleUpload(req, res, next) {
  upload.single("image")(req, res, (err) => {
    if (!err) return next();
    if (err instanceof multer.MulterError && err.code === "LIMIT_FILE_SIZE") {
      return res.status(413).json({ error: "Photo is too large. Please use a photo under 10 MB." });
    }
    if (err instanceof multer.MulterError) {
      return res.status(400).json({ error: "Please upload one JPG, PNG or WebP photo." });
    }
    return next(err);
  });
}

// In-memory job store for async vision audits (eliminates Safari 60s HTTP socket drops)
const auditJobs = new Map();

// Periodic cleanup of jobs older than 30 minutes
setInterval(() => {
  const now = Date.now();
  for (const [id, job] of auditJobs.entries()) {
    if (now - job.createdAt > 30 * 60 * 1000) {
      auditJobs.delete(id);
    }
  }
}, 5 * 60 * 1000);

app.post("/api/audit", uploadLimiter, handleUpload, async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: "No image file provided." });
  }
  if (!looksLikeImage(req.file.buffer)) {
    return res.status(400).json({ error: "This file is not a photo. Please upload a JPG, PNG or WebP photo." });
  }

  const jobId = crypto.randomUUID();
  const fileBuffer = req.file.buffer;
  const fileMime = req.file.mimetype;

  // Background worker to execute Florence-2/CLIP CV analysis
  const executeAuditAsync = async () => {
    try {
      const formData = new FormData();
      formData.append("file", fileBuffer, {
        filename: `upload-${jobId}.jpg`,
        contentType: fileMime || "image/jpeg",
      });

      const cvUrl = (process.env.CV_SERVICE_URL || "http://localhost:8000") + "/api/audit-image";
      const response = await axios.post(cvUrl, formData, {
        headers: {
          ...formData.getHeaders(),
        },
        timeout: 5 * 60 * 1000,
        maxBodyLength: MAX_UPLOAD_BYTES + 1024 * 1024,
      });

      auditJobs.set(jobId, {
        status: "completed",
        data: response.data,
        createdAt: Date.now(),
      });
    } catch (error) {
      console.error(`[audit-job ${jobId}]`, error.code || "", error.message);
      let errorMsg = "The photo check is not available right now. Please try again later.";
      if (error.response?.status === 400) {
        errorMsg = "We could not read this photo. Please try a clear photo of an indoor room.";
      }
      auditJobs.set(jobId, {
        status: "error",
        error: errorMsg,
        createdAt: Date.now(),
      });
    }
  };

  // Synchronous mode fallback (if explicitly requested via query param)
  if (req.query.sync === "true") {
    try {
      const formData = new FormData();
      formData.append("file", fileBuffer, {
        filename: `upload-${jobId}.jpg`,
        contentType: fileMime || "image/jpeg",
      });
      const cvUrl = (process.env.CV_SERVICE_URL || "http://localhost:8000") + "/api/audit-image";
      const response = await axios.post(cvUrl, formData, {
        headers: { ...formData.getHeaders() },
        timeout: 5 * 60 * 1000,
        maxBodyLength: MAX_UPLOAD_BYTES + 1024 * 1024,
      });
      return res.json(response.data);
    } catch (error) {
      if (error.response?.status === 400) {
        return res.status(400).json({ error: "We could not read this photo. Please try a clear photo of an indoor room." });
      }
      return res.status(502).json({ error: "The photo check is not available right now. Please try again later." });
    }
  }

  // Register job and start async worker immediately
  auditJobs.set(jobId, {
    status: "processing",
    createdAt: Date.now(),
  });
  executeAuditAsync();

  // Return within 100ms so Safari/mobile sockets NEVER time out
  return res.json({
    status: "processing",
    jobId,
  });
});

app.get("/api/audit/status/:jobId", generalLimiter, (req, res) => {
  const { jobId } = req.params;
  const job = auditJobs.get(jobId);
  if (!job) {
    return res.status(404).json({ error: "Job not found or expired. Please upload the photo again." });
  }
  return res.json(job);
});

app.use("/api/", (req, res) => {
  res.status(404).json({ error: "Not found." });
});

// Last error handler: body parser errors and anything unexpected. No stack trace goes to the browser.
app.use((err, req, res, next) => {
  if (err.type === "entity.too.large") {
    return res.status(413).json({ error: "The request is too large." });
  }
  if (err.type === "entity.parse.failed") {
    return res.status(400).json({ error: "The request format is not valid." });
  }
  console.error("[unhandled]", err.message);
  res.status(500).json({ error: "Something went wrong. Please try again." });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
