import fs from "fs";
import path from "path";
import csv from "csv-parser";
import pg from "pg";
import "dotenv/config";

const { Pool } = pg;

const pool = new Pool(process.env.DATABASE_URL ? {
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL.includes("localhost") ? false : { rejectUnauthorized: false }
} : {
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT),
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
});

// Files to import
const files = [
  { path: "data/lga_modelled_estimates.csv", table: "lga_dementia_estimates" },
  { path: "data/landmarks_places_city_of_melbourne.csv", table: "landmarks" },
  { path: "data/public_toilets_city_of_melbourne.csv", table: "public_toilets" },
  { path: "data_processing/noise_clean.csv", table: "noise_clean" },
  { path: "data_processing/noise_hourly_clean.csv", table: "noise_hourly" },
  { path: "data_processing/cleaned_landmark_candidates.csv", table: "cleaned_landmark_candidates" },
  { path: "data_processing/location.csv", table: "location" },
  { path: "data_processing/joined_data.csv", table: "joined_data" },
  { path: "data_processing/cleaned_route_step_landmark_matches.csv", table: "cleaned_route_step_landmark_matches" },
  { path: "data_processing/cleaned_route_results_with_landmark_coverage.csv", table: "cleaned_route_results_with_landmark_coverage" },
  { path: "data_processing/pedestrian_clean.csv", table: "pedestrian_clean" },
  { path: "data_processing/estimate.csv", table: "estimate" },
  { path: "data_processing/demographic.csv", table: "demographic" },
  { path: "data_processing/cleaned_landmark_category_summary.csv", table: "cleaned_landmark_category_summary" },
  { path: "data_processing/sensor_locations_clean.csv", table: "sensor_locations_clean" }
];

function sanitizeColumnName(name) {
  return name
    .replace(/^[\uFEFF\xA0]+/, "")
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, "_")
    .replace(/^_+|_+$/g, "");
}

async function importCsv(filePath, tableName) {
  return new Promise((resolve, reject) => {
    const results = [];
    let headers = [];

    fs.createReadStream(filePath)
      .pipe(csv())
      .on("headers", (h) => {
        headers = h.map(sanitizeColumnName);
      })
      .on("data", (data) => {
        const row = {};
        for (const [key, value] of Object.entries(data)) {
          row[sanitizeColumnName(key)] = value;
        }
        results.push(row);
      })
      .on("end", async () => {
        if (results.length === 0) {
          console.log(`Skipping ${tableName}, no data found.`);
          return resolve();
        }

        console.log(`Importing ${results.length} rows into ${tableName}...`);
        
        const client = await pool.connect();
        try {
          await client.query("BEGIN");

          // Drop existing table to ensure clean state
          await client.query(`DROP TABLE IF EXISTS ${tableName}`);

          // Create table
          const columnDefs = headers.map((col) => `"${col}" TEXT`).join(", ");
          await client.query(`CREATE TABLE ${tableName} (${columnDefs})`);

          // Insert data in batches of 200 rows for high performance
          const columnsStr = headers.map(c => `"${c}"`).join(", ");
          const batchSize = 200;
          for (let i = 0; i < results.length; i += batchSize) {
            const batch = results.slice(i, i + batchSize);
            const valueClauses = [];
            const values = [];
            let paramIdx = 1;

            for (const row of batch) {
              const rowPlaceholders = [];
              for (const col of headers) {
                rowPlaceholders.push(`$${paramIdx++}`);
                values.push(row[col]);
              }
              valueClauses.push(`(${rowPlaceholders.join(", ")})`);
            }

            await client.query(
              `INSERT INTO ${tableName} (${columnsStr}) VALUES ${valueClauses.join(", ")}`,
              values
            );
          }

          // If latitude and longitude exist, populate geometry and spatial index
          if (headers.includes("latitude") && headers.includes("longitude")) {
            try {
              await client.query(`
                ALTER TABLE ${tableName} ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);
                UPDATE ${tableName} 
                SET geom = ST_SetSRID(ST_Point(CAST(NULLIF(longitude, '') AS float), CAST(NULLIF(latitude, '') AS float)), 4326) 
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND NULLIF(latitude, '') IS NOT NULL AND NULLIF(longitude, '') IS NOT NULL;
                CREATE INDEX IF NOT EXISTS "idx_${tableName}_geom" ON ${tableName} USING GIST (geom);
              `);
            } catch (spatialErr) {
              // Ignore spatial errors if PostGIS is not yet initialized for this table
            }
          }

          await client.query("COMMIT");
          console.log(`✅ Successfully imported ${tableName}`);
        } catch (e) {
          await client.query("ROLLBACK");
          console.error(`❌ Failed to import ${tableName}:`, e);
        } finally {
          client.release();
          resolve();
        }
      })
      .on("error", reject);
  });
}

async function run() {
  console.log("Starting import...");
  for (const file of files) {
    const fullPath = path.resolve(process.cwd(), file.path);
    if (fs.existsSync(fullPath)) {
      await importCsv(fullPath, file.table);
    } else {
      console.warn(`⚠️ File not found: ${file.path}`);
    }
  }

  // Ensure convenience views are created if council_contacts exists
  let client;
  try {
    client = await pool.connect();
    await client.query(`
      CREATE OR REPLACE VIEW victorian_council_contacts_2026_cleaned AS 
      SELECT * FROM council_contacts;
      CREATE OR REPLACE VIEW victorian_council_contacts AS 
      SELECT * FROM council_contacts;
    `);
  } catch (e) {
    // ignore if table not present
  } finally {
    if (client) client.release();
  }

  await pool.end();
  console.log("Import complete!");
}

run().then(() => {
  process.exit(0);
}).catch((err) => {
  console.error("Fatal Error:", err);
  process.exit(1);
});
