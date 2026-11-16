#!/bin/bash
# scripts/setup_db.sh
# Run this script to completely setup the database from scratch on a new machine.

echo "Installing Database Data..."
node scripts/import_local_data.js

echo "Building Spatial Topology..."
psql -p 5434 -d neighborlyminds -f scripts/build_topology.sql

echo "Building turn-penalized routing graph..."
psql -p 5434 -d neighborlyminds -f scripts/create_turn_graph.sql

echo "Creating Routing Functions..."
psql -p 5434 -d neighborlyminds -f scripts/create_routing_function.sql

echo "Creating Comfort Stats Functions..."
psql -p 5434 -d neighborlyminds -f scripts/create_comfort_stats_function.sql

echo "Importing CLUE buildings and PARKRES benches..."
node scripts/import_clue_and_parkres.js || psql -p 5434 -d neighborlyminds -f scripts/create_parkres_mock.sql

echo "Creating Landmark Checklist Functions..."
psql -p 5434 -d neighborlyminds -f scripts/create_landmark_checklist_function.sql

echo "Creating Sensory Schedule Functions..."
psql -p 5434 -d neighborlyminds -f scripts/create_sensory_schedule_function.sql

echo "Database Setup Complete!"
