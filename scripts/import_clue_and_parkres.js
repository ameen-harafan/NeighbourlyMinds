// Loads Census of Land Use and Employment (CLUE) buildings and a parkres
// bench layer. Park reserves come from City of Melbourne park landmarks.
// Bench points are street seats within 200 m of those reserves.
import fs from "fs";
import path from "path";
import csv from "csv-parser";
import pg from "pg";
import "dotenv/config";

const { Pool } = pg;

const pool = new Pool({
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT),
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
});

const CLUE_CSV = "data/clue_buildings_2024.csv";
const SEATS_CSV = "data/street_seats.csv";
const LANDMARKS_CSV = "data/landmarks_places_city_of_melbourne.csv";
const PARK_RADIUS_M = 200;

const EXCLUDED_USES = new Set([
  "House/Townhouse",
  "Residential Apartment",
  "Student Accommodation",
  "Unoccupied - Unused",
  "Storage",
  "Parking - Commercial Covered",
  "Equipment Installation",
]);

const USE_SCORE = {
  "Community Use": 80,
  "Hospital/Clinic": 80,
  "Educational/Research": 75,
  "Performances, Conferences, Ceremonies": 75,
  "Entertainment/Recreation - Indoor": 70,
  "Retail - Shop": 65,
  "Commercial Accommodation": 55,
  "Office": 40,
};

const CIVIC_NAME = /post office|town hall|library|railway|station|church|cathedral|market|museum|gallery|hospital|theatre|theater/i;

function readCsv(filePath) {
  return new Promise((resolve, reject) => {
    const rows = [];
    fs.createReadStream(filePath)
      .pipe(csv())
      .on("data", (row) => rows.push(row))
      .on("end", () => resolve(rows))
      .on("error", reject);
  });
}

function field(row, name) {
  if (row[name] != null) return row[name];
  const key = Object.keys(row).find((k) => k.replace(/^\uFEFF/, "") === name);
  return key ? row[key] : "";
}

function metersBetween(a, b) {
  const toRad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * toRad;
  const dLon = (b.lon - a.lon) * toRad;
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(a.lat * toRad) * Math.cos(b.lat * toRad) * Math.sin(dLon / 2) ** 2;
  return 2 * 6371000 * Math.asin(Math.sqrt(h));
}

function prominence(row) {
  const use = field(row, "predominant_space_use");
  const name = field(row, "building_name").trim();
  if (!name) return 0;
  const civic = CIVIC_NAME.test(name);
  if (EXCLUDED_USES.has(use) && !civic) return 0;
  let score = USE_SCORE[use] ?? (EXCLUDED_USES.has(use) ? 0 : 50);
  const floors = Number(field(row, "number_of_floors_above_ground")) || 0;
  if (floors >= 6) score += 10;
  if (civic) score += 30;
  if (use === "Office" && floors < 4 && !civic) return 0;
  return score;
}

async function main() {
  if (!fs.existsSync(CLUE_CSV) || !fs.existsSync(SEATS_CSV) || !fs.existsSync(LANDMARKS_CSV)) {
    throw new Error("Missing CLUE, seat, or landmark CSV under data/.");
  }

  const clueRows = await readCsv(CLUE_CSV);
  const seatRows = await readCsv(SEATS_CSV);
  const landmarkRows = await readCsv(LANDMARKS_CSV);

  const buildings = new Map();
  for (const row of clueRows) {
    const score = prominence(row);
    if (score <= 0) continue;
    const lon = Number(field(row, "longitude"));
    const lat = Number(field(row, "latitude"));
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
    const name = field(row, "building_name").trim();
    const key = name.toLowerCase();
    const floors = Number(field(row, "number_of_floors_above_ground")) || 0;
    const existing = buildings.get(key);
    if (existing && (existing.score > score || (existing.score === score && existing.floors >= floors))) {
      continue;
    }
    buildings.set(key, {
      name,
      use: field(row, "predominant_space_use"),
      address: field(row, "street_address"),
      floors,
      score,
      lon,
      lat,
    });
  }

  const parks = [];
  for (const row of landmarkRows) {
    const sub = field(row, "sub_theme");
    if (!/park|garden|reserve/i.test(sub)) continue;
    const coords = field(row, "co_ordinates");
    const [latText, lonText] = coords.split(",").map((part) => part.trim());
    const lat = Number(latText);
    const lon = Number(lonText);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    parks.push({ name: field(row, "feature_name"), lon, lat, benches: 0 });
  }

  const benches = [];
  for (const row of seatRows) {
    const type = field(row, "type");
    if (type !== "Seat" && type !== "Picnic Setting") continue;
    const lon = Number(field(row, "longitude"));
    const lat = Number(field(row, "latitude"));
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
    const nearPark = parks.some((park) => metersBetween(park, { lon, lat }) <= PARK_RADIUS_M);
    if (!nearPark) continue;
    benches.push({
      name: field(row, "description") || "Park bench",
      lon,
      lat,
    });
  }

  for (const park of parks) {
    park.benches = benches.filter((bench) => metersBetween(park, bench) <= PARK_RADIUS_M).length;
  }

  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query("DROP TABLE IF EXISTS clue_buildings");
    await client.query(`
      CREATE TABLE clue_buildings (
        id SERIAL PRIMARY KEY,
        building_name TEXT NOT NULL,
        predominant_space_use TEXT,
        street_address TEXT,
        floors INTEGER,
        prominence INTEGER NOT NULL,
        geom geometry(Point, 4326) NOT NULL
      )
    `);
    await client.query("DROP TABLE IF EXISTS parkres");
    await client.query(`
      CREATE TABLE parkres (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255),
        feature_type VARCHAR(32) NOT NULL,
        bench_count INTEGER NOT NULL DEFAULT 0,
        geom geometry(Point, 4326) NOT NULL
      )
    `);

    for (const building of buildings.values()) {
      await client.query(
        `INSERT INTO clue_buildings (building_name, predominant_space_use, street_address, floors, prominence, geom)
         VALUES ($1, $2, $3, $4, $5, ST_SetSRID(ST_MakePoint($6, $7), 4326))`,
        [building.name, building.use, building.address, building.floors, building.score, building.lon, building.lat]
      );
    }

    for (const park of parks) {
      await client.query(
        `INSERT INTO parkres (name, feature_type, bench_count, geom)
         VALUES ($1, 'Reserve', $2, ST_SetSRID(ST_MakePoint($3, $4), 4326))`,
        [park.name, park.benches, park.lon, park.lat]
      );
    }

    for (const bench of benches) {
      await client.query(
        `INSERT INTO parkres (name, feature_type, bench_count, geom)
         VALUES ($1, 'Bench', 1, ST_SetSRID(ST_MakePoint($2, $3), 4326))`,
        [bench.name, bench.lon, bench.lat]
      );
    }

    await client.query("CREATE INDEX idx_clue_buildings_geom ON clue_buildings USING GIST (geom)");
    await client.query("CREATE INDEX idx_parkres_geom ON parkres USING GIST (geom)");
    await client.query("COMMIT");
    console.log(
      `Imported ${buildings.size} CLUE buildings, ${parks.length} park reserves, ${benches.length} park benches.`
    );
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
