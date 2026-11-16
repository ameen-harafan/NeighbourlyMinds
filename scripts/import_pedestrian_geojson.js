import fs from "fs";
import pool from "../db.js";

async function importPedestrianNetwork() {
  console.log("Reading data/pedestrian_network_city_of_melbourne.geojson...");
  const raw = fs.readFileSync("data/pedestrian_network_city_of_melbourne.geojson", "utf-8");
  const data = JSON.parse(raw);
  const features = data.features || [];
  console.log(`Parsed ${features.length} features.`);

  await pool.query("TRUNCATE TABLE pedestrian_network RESTART IDENTITY;");

  const batchSize = 1000;
  for (let i = 0; i < features.length; i += batchSize) {
    const chunk = features.slice(i, i + batchSize);
    const valuePlaceholders = [];
    const params = [];

    chunk.forEach((feat, idx) => {
      valuePlaceholders.push(`(ST_SetSRID(ST_GeomFromGeoJSON($${idx + 1}), 4326))`);
      params.push(JSON.stringify(feat.geometry));
    });

    const sql = `INSERT INTO pedestrian_network (wkb_geometry) VALUES ${valuePlaceholders.join(", ")};`;
    await pool.query(sql, params);
    process.stdout.write(`\rImported ${Math.min(i + batchSize, features.length)} / ${features.length} edges...`);
  }

  console.log("\n✅ Finished importing pedestrian_network!");
  await pool.end();
}

importPedestrianNetwork().catch(console.error);
