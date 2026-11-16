// Input checks shared by the API routes in server.js.
// Values that fail a check return null so the route can answer 400.

export const REPORT_STATUSES = ["SAVED", "SENT", "ACKNOWLEDGED", "UNDER_REVIEW"];
export const SPACE_TYPES = ["public", "private"];
export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const REFERENCE_ID_PATTERN = /^(HOME|AUDIT)-[A-Z0-9]{4,12}-\d{4}$/;
const LGA_NAME_PATTERN = /^[A-Za-z][A-Za-z .'()-]{1,59}$/;
const EMAIL_PATTERN = /^[^\s@]{1,64}@[^\s@]{1,190}\.[A-Za-z]{2,}$/;
const POSTCODE_PATTERN = /^\d{4}$/;

function isBlank(value) {
  return value === undefined || value === null || String(value).trim() === "";
}

function parseNumberInRange(value, min, max) {
  if (isBlank(value)) return null;
  const num = Number(value);
  if (!Number.isFinite(num) || num < min || num > max) return null;
  return num;
}

export function parseLatitude(value) {
  return parseNumberInRange(value, -90, 90);
}

export function parseLongitude(value) {
  return parseNumberInRange(value, -180, 180);
}

// Keeps letters, numbers, spaces and normal address punctuation only.
export function cleanText(value, maxLength = 100) {
  if (isBlank(value)) return "";
  return String(value)
    .normalize("NFKC")
    .replace(/[^\p{L}\p{N} ,.'&()/#-]/gu, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, maxLength);
}

// For longer free text (report body). Removes control characters but keeps new lines.
export function cleanLongText(value, maxLength) {
  if (isBlank(value)) return "";
  return String(value)
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "")
    .slice(0, maxLength);
}

export function isValidLgaName(value) {
  return typeof value === "string" && LGA_NAME_PATTERN.test(value.trim());
}

export function isValidReferenceId(value) {
  return typeof value === "string" && REFERENCE_ID_PATTERN.test(value);
}

export function isValidEmail(value) {
  return typeof value === "string" && value.length <= 254 && EMAIL_PATTERN.test(value);
}

export function isValidPostcode(value) {
  return typeof value === "string" && POSTCODE_PATTERN.test(value);
}

export function normaliseStatus(value) {
  if (isBlank(value)) return null;
  const status = String(value).trim().toUpperCase();
  return REPORT_STATUSES.includes(status) ? status : null;
}

// Used for the Content-Disposition header, so only safe file name characters are kept.
export function safeFileName(value, fallback = "route") {
  const cleaned = String(value || "").replace(/[^A-Za-z0-9_-]/g, "").slice(0, 40);
  return cleaned || fallback;
}
