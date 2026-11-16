import fs from "fs";
import path from "path";
import csv from "csv-parser";
import pg from "pg";
import "dotenv/config";

const { Pool } = pg;

const pool = new Pool(
  process.env.DATABASE_URL
    ? { connectionString: process.env.DATABASE_URL }
    : {
        host: process.env.DB_HOST || "localhost",
        port: Number(process.env.DB_PORT) || 5434,
        database: process.env.DB_NAME || "neighborlyminds",
        user: process.env.DB_USER || "akhileshchitte",
        password: process.env.DB_PASSWORD || "",
      }
);

function sanitizeColumnName(name) {
  return name
    .replace(/^[\uFEFF\xA0]+/, "")
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, "_")
    .replace(/^_+|_+$/g, "");
}

async function importCouncilContacts() {
  const possiblePaths = [
    "data/victorian_council_contacts_2026_cleaned (2).csv",
    "data/victorian_council_contacts_2026_cleaned (1).csv",
    "data/victorian_council_contacts_2026_cleaned.csv"
  ];

  let csvPath = possiblePaths.find((p) => fs.existsSync(path.resolve(process.cwd(), p)));

  if (!csvPath) {
    console.error("❌ Council contacts CSV file not found in data/ directory!");
    process.exit(1);
  }

  console.log(`Reading council contacts from: ${csvPath}`);

  const rows = [];
  await new Promise((resolve, reject) => {
    fs.createReadStream(path.resolve(process.cwd(), csvPath))
      .pipe(csv())
      .on("data", (data) => {
        const cleanedRow = {};
        for (const [key, val] of Object.entries(data)) {
          const cleanKey = sanitizeColumnName(key);
          const cleanVal = typeof val === "string" ? val.trim() : val;
          cleanedRow[cleanKey] = cleanVal === "" ? null : cleanVal;
        }
        if (cleanedRow.council_name) {
          rows.push(cleanedRow);
        }
      })
      .on("end", resolve)
      .on("error", reject);
  });

  console.log(`Parsed ${rows.length} council contact records.`);

  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    // Drop previous views and table if needed
    await client.query("DROP VIEW IF EXISTS victorian_council_contacts_2026_cleaned CASCADE;");
    await client.query("DROP VIEW IF EXISTS victorian_council_contacts CASCADE;");
    await client.query("DROP TABLE IF EXISTS council_contacts CASCADE;");

    // Create table with explicit schema
    await client.query(`
      CREATE TABLE council_contacts (
        council_name TEXT PRIMARY KEY,
        ceo_name TEXT NOT NULL,
        mayor_name TEXT,
        deputy_mayor_name TEXT,
        telephone TEXT NOT NULL,
        email TEXT,
        website TEXT NOT NULL,
        postal_address TEXT NOT NULL,
        postal_suburb TEXT NOT NULL,
        postcode VARCHAR(10) NOT NULL
      );
    `);

    // Insert records
    const insertSql = `
      INSERT INTO council_contacts (
        council_name, ceo_name, mayor_name, deputy_mayor_name,
        telephone, email, website, postal_address, postal_suburb, postcode
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    `;

    for (const r of rows) {
      await client.query(insertSql, [
        r.council_name,
        r.ceo_name || "",
        r.mayor_name || null,
        r.deputy_mayor_name || null,
        r.telephone || "",
        r.email || null,
        r.website || "",
        r.postal_address || "",
        r.postal_suburb || "",
        r.postcode || ""
      ]);
    }

    // Create Index
    await client.query(`
      CREATE INDEX idx_council_contacts_name_lower 
      ON council_contacts (LOWER(council_name));
    `);

    // Create convenience views
    await client.query(`
      CREATE OR REPLACE VIEW victorian_council_contacts_2026_cleaned AS 
      SELECT * FROM council_contacts;
    `);

    await client.query(`
      CREATE OR REPLACE VIEW victorian_council_contacts AS 
      SELECT * FROM council_contacts;
    `);

    await client.query("COMMIT");
    console.log("✅ Successfully imported council_contacts and created views!");
  } catch (err) {
    await client.query("ROLLBACK");
    console.error("❌ Failed to import council contacts:", err);
    throw err;
  } finally {
    client.release();
    await pool.end();
  }
}

importCouncilContacts().catch((err) => {
  console.error("Fatal error during council contacts import:", err);
  process.exit(1);
});
