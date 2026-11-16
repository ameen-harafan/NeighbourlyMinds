import crypto from "crypto";
import rateLimit from "express-rate-limit";

const DEFAULT_ALLOWED_ORIGINS = [
  "http://localhost:5173",
  "http://localhost:4173",
  "https://34-135-219-183.sslip.io",
  "https://www.neighborlyminds.me",
  "https://neighborlyminds.me",
  "http://www.neighborlyminds.me",
  "http://neighborlyminds.me",
  "https://neighborlyminds-frontend-794244018948.us-central1.run.app",
];

export const allowedOrigins = (process.env.ALLOWED_ORIGINS || DEFAULT_ALLOWED_ORIGINS.join(","))
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

export const corsOptions = {
  origin(origin, callback) {
    // Same-origin requests and server-to-server calls (curl, nginx) do not send Origin.
    if (!origin) return callback(null, true);
    if (allowedOrigins.includes(origin)) return callback(null, true);
    // Allow any neighborlyminds.me subdomain or Cloud Run preview URL
    if (/^https?:\/\/([a-z0-9-]+\.)?neighborlyminds\.me(:\d+)?$/i.test(origin)) return callback(null, true);
    if (/^https:\/\/neighborlyminds-[a-z0-9-]+\.us-central1\.run\.app$/i.test(origin)) return callback(null, true);
    return callback(null, false);
  },
  methods: ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "x-admin-token", "Accept", "Authorization"],
  maxAge: 600,
};

function limiter(windowMinutes, limit, message) {
  return rateLimit({
    windowMs: windowMinutes * 60 * 1000,
    limit,
    standardHeaders: "draft-8",
    legacyHeaders: false,
    message: { error: message },
  });
}

export const generalLimiter = limiter(1, 100, "Too many requests. Please wait a minute and try again.");
export const reportLimiter = limiter(15, 20, "Too many reports sent. Please try again later.");
export const uploadLimiter = limiter(15, 10, "Too many photos uploaded. Please try again in 15 minutes.");
export const pdfLimiter = limiter(15, 20, "Too many pocket cards requested. Please try again later.");
export const siteAccessLimiter = limiter(15, 5, "Too many wrong attempts. Please try again in 15 minutes.");

// Logs the real error on the server only. The user gets a plain message with no internal details.
export function sendServerError(res, publicMessage, error, context) {
  console.error(`[${context}]`, error?.code || "", error?.message || error);
  return res.status(500).json({ error: publicMessage });
}

// Compares two secrets in constant time so the response time does not leak how much matched.
export function secretsMatch(provided, expected) {
  if (typeof provided !== "string" || typeof expected !== "string" || !expected) return false;
  const a = crypto.createHash("sha256").update(provided).digest();
  const b = crypto.createHash("sha256").update(expected).digest();
  return crypto.timingSafeEqual(a, b);
}

export function requireAdminToken(req, res, next) {
  const expected = process.env.ADMIN_API_TOKEN;
  if (!expected) {
    return res.status(403).json({ error: "This action is turned off on this server." });
  }
  if (!secretsMatch(req.get("x-admin-token"), expected)) {
    return res.status(401).json({ error: "You are not allowed to do this action." });
  }
  return next();
}

export const ALLOWED_IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/heic",
  "image/heif",
  "image/pjpeg",
  "image/x-png",
  "application/octet-stream",
];
export const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;

// Checks the first bytes of the file, because the browser-supplied mimetype can be faked.
export function looksLikeImage(buffer) {
  if (!buffer || buffer.length < 12) return false;
  const isJpeg = buffer[0] === 0xff && buffer[1] === 0xd8 && buffer[2] === 0xff;
  const isPng = buffer.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]));
  const isWebp = buffer.subarray(0, 4).toString("ascii") === "RIFF" && buffer.subarray(8, 12).toString("ascii") === "WEBP";
  // HEIC/HEIF format: byte 4-7 is 'ftyp' followed by major brand (heic, mif1, msf1, heix, hevc)
  const isFtyp = buffer.subarray(4, 8).toString("ascii") === "ftyp";
  const brand = isFtyp ? buffer.subarray(8, 12).toString("ascii").toLowerCase() : "";
  const isHeic = isFtyp && (brand.startsWith("hei") || brand.startsWith("mif") || brand.startsWith("msf") || brand.startsWith("hev"));
  return isJpeg || isPng || isWebp || isHeic;
}
