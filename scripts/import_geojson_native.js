import fs from "fs";
import path from "path";
import JSONStream from "JSONStream";
import pg from "pg";
import "dotenv/config";

const { Pool } = pg;
const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: Number(process.env.DB_PORT) || 5432,
  database: process.env.DB_NAME || 'neighborlyminds',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || '1234',
});

const files = [
  { path: "data/abs_lga_boundaries_victoria_2025.geojson", table: "lga_boundaries_victoria" },
  { path: "data/pedestrian_network_city_of_melbourne.geojson", table: "pedestrian_network" },
  { path: "data/public_transport_stops_victoria.geojson", table: "public_transport_stops" },
  { path: "data/vicmap_foi_melbourne_landmark_candidates.geojson", table: "landmark_candidates_geo" },
  { path: "data/tree_canopies_2021_city_of_melbourne.geojson", table: "tree_canopies" }
];

async function importGeoJSON(filePath, tableName) {
  const client = await pool.connect();
  try {
    await client.query(`DROP TABLE IF EXISTS ${tableName}`);
    console.log(`\n🌍 Processing GeoJSON for table: ${tableName}`);

    let features = [];
    let count = 0;
    let tableCreated = false;
    let columns = [];

    await new Promise((resolve, reject) => {
      const stream = fs.createReadStream(filePath, { encoding: "utf8" });
      const parser = JSONStream.parse("features.*");

      stream.pipe(parser)
        .on("data", async (feature) => {
          parser.pause();
          try {
            if (!tableCreated) {
              tableCreated = true; // Set synchronously
              columns = Object.keys(feature.properties || {}).map(k => k.toLowerCase());
              let colDefs = columns.map(c => `"${c}" TEXT`).join(", ");
              if (colDefs) colDefs = ", " + colDefs;
              
              await client.query(`
                CREATE TABLE ${tableName} (
                  ogc_fid SERIAL PRIMARY KEY,
                  wkb_geometry geometry ${colDefs}
                )
              `);
            }

            features.push(feature);
            if (features.length >= 1000) {
              await insertBatch(client, tableName, columns, features);
              count += features.length;
              features = [];
            }
          } catch (err) {
            return reject(err);
          }
          parser.resume();
        })
        .on("end", async () => {
          try {
            if (features.length > 0 && tableCreated) {
              await insertBatch(client, tableName, columns, features);
              count += features.length;
            }
            resolve();
          } catch (err) {
            reject(err);
          }
        })
        .on("error", reject);
    });

    if (count > 0) {
      console.log(`Building spatial index for ${tableName}...`);
      await client.query(`CREATE INDEX "idx_${tableName}_geom" ON ${tableName} USING GIST (wkb_geometry)`);
      console.log(`✅ Successfully imported ${count} features into ${tableName}`);
    } else {
      console.warn(`⚠️ No features found in ${filePath}`);
    }
  } catch (err) {
    console.error(`❌ Failed to import ${tableName}:`, err);
  } finally {
    client.release();
  }
}

async function insertBatch(client, tableName, columns, features) {
  const values = [];
  const params = [];
  let pIdx = 1;

  for (const feat of features) {
    let rowParams = [];
    
    // Geometry
    if (!feat.geometry || Object.keys(feat.geometry).length === 0) {
      rowParams.push(`NULL`);
    } else {
      rowParams.push(`ST_SetSRID(ST_GeomFromGeoJSON($${pIdx++}), 4326)`);
      values.push(JSON.stringify(feat.geometry));
    }

    // Properties
    for (const col of columns) {
      rowParams.push(`$${pIdx++}`);
      let val = feat.properties[col] || feat.properties[col.toUpperCase()];
      values.push(val !== undefined && val !== null ? String(val) : null);
    }

    params.push(`(${rowParams.join(", ")})`);
  }

  let colNames = columns.map(c => `"${c}"`).join(", ");
  if (colNames) colNames = ", " + colNames;

  await client.query(
    `INSERT INTO ${tableName} (wkb_geometry${colNames}) VALUES ${params.join(", ")}`,
    values
  );
}

async function run() {
  for (const file of files) {
    const fullPath = path.resolve(process.cwd(), file.path);
    if (fs.existsSync(fullPath)) {
      await importGeoJSON(fullPath, file.table);
    } else {
      console.warn(`⚠️ File not found: ${file.path}`);
    }
  }
}

run().then(() => {
  pool.end();
  process.exit(0);
}).catch(err => {
  console.error("Fatal Error:", err);
  process.exit(1);
});
