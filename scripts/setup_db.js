import fs from "fs";
import path from "path";
import pool from "../db.js";
import { execSync } from "child_process";
import "dotenv/config";

import pg from "pg";

async function runSqlFile(relativePath) {
  const fullPath = path.join(process.cwd(), relativePath);
  if (!fs.existsSync(fullPath)) {
    console.warn(`File not found: ${relativePath}, skipping.`);
    return;
  }
  console.log(`Executing ${relativePath}...`);
  const sql = fs.readFileSync(fullPath, "utf-8");
  try {
    await pool.query(sql);
    console.log(`✅ Applied ${relativePath}`);
  } catch (err) {
    console.warn(`⚠️ Warning executing ${relativePath}:`, err.message);
  }
}

async function ensureDatabaseExists() {
  const dbName = process.env.DB_NAME || 'neighborlyminds';
  // Connect to the default system 'postgres' database
  const client = new pg.Client({
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT || 5432,
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || '1234',
    database: 'postgres',
  });

  try {
    await client.connect();
    console.log(`\n🔍 Checking if database '${dbName}' exists...`);
    const res = await client.query(`SELECT 1 FROM pg_database WHERE datname = $1`, [dbName]);
    
    if (res.rowCount === 0) {
      console.log(`🏗️ Database '${dbName}' does not exist. Automating creation...`);
      await client.query(`CREATE DATABASE "${dbName}"`);
      console.log(`✅ Database '${dbName}' created successfully!`);
    } else {
      console.log(`✅ Database '${dbName}' already exists. Proceeding with setup...`);
    }
  } catch (err) {
    console.error("❌ Failed to automatically create database. Ensure Postgres is running.", err.message);
  } finally {
    await client.end();
  }
}

function runNodeScript(scriptPath) {
  console.log(`\n🚀 Running Node Script: ${scriptPath}`);
  try {
    execSync(`node ${scriptPath}`, { stdio: "inherit" });
    console.log(`✅ Successfully ran ${scriptPath}`);
  } catch (err) {
    console.error(`❌ Failed to run ${scriptPath}`);
  }
}



async function setup() {
  console.log("=== 🌟 NeighborlyMinds Master Database Automation 🌟 ===");
  try {
    // 0. Ensure the shell database exists before anything connects to it!
    await ensureDatabaseExists();

    // 1. Enable spatial extensions (MUST happen first)
    console.log("\n📦 Enabling PostGIS and pgRouting extensions...");
    await pool.query("CREATE EXTENSION IF NOT EXISTS postgis;");
    try {
      await pool.query("CREATE EXTENSION IF NOT EXISTS pgrouting;");
    } catch (e) {
      console.warn("⚠️ pgrouting extension not available in base postgres.");
    }

    // 2. Import all Data via Node Scripts
    runNodeScript("scripts/import_local_data.js");
    runNodeScript("scripts/import_clue_and_parkres.js");
    runNodeScript("scripts/import_council_contacts.js");

    // 3. Import massive Spatial GeoJSON Polygons Natively
    console.log("\n🌍 Importing GeoJSON Spatial Polygons natively via Node.js (GDAL no longer required)...");
    runNodeScript("scripts/import_geojson_native.js");

    // 4. Build Topology & Routing Graph
    console.log("\n🗺️ Building Street Routing Topology...");
    await runSqlFile("scripts/build_topology.sql");
    await runSqlFile("scripts/create_turn_graph.sql");

    // 5. Create Final Application Functions
    console.log("\n🛠️ Creating Application SQL Functions...");
    await runSqlFile("scripts/create_routing_function.sql");
    await runSqlFile("scripts/create_comfort_stats_function.sql");
    await runSqlFile("scripts/create_landmark_checklist_function.sql");
    await runSqlFile("scripts/create_sensory_schedule_function.sql");
    await runSqlFile("scripts/create_accessibility_reports_table.sql");

    console.log("\n=== 🎯 Database Automation Completed Successfully! 🎯 ===");
  } catch (error) {
    console.error("\n❌ Critical Setup Failure:", error);
  } finally {
    await pool.end();
  }
}

setup();
