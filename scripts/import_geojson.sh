#!/bin/bash
set -e

DB_CONN="PG:dbname=neighborlyminds port=5434"

echo "Importing abs_lga_boundaries_victoria_2025.geojson..."
ogr2ogr -f "PostgreSQL" "$DB_CONN" -nln lga_boundaries_victoria data/abs_lga_boundaries_victoria_2025.geojson -overwrite -progress

echo "Importing pedestrian_network_city_of_melbourne.geojson..."
ogr2ogr -f "PostgreSQL" "$DB_CONN" -nln pedestrian_network data/pedestrian_network_city_of_melbourne.geojson -overwrite -progress

echo "Importing public_transport_stops_victoria.geojson..."
ogr2ogr -f "PostgreSQL" "$DB_CONN" -nln public_transport_stops data/public_transport_stops_victoria.geojson -overwrite -progress

echo "Importing vicmap_foi_melbourne_landmark_candidates.geojson..."
ogr2ogr -f "PostgreSQL" "$DB_CONN" -nln landmark_candidates_geo data/vicmap_foi_melbourne_landmark_candidates.geojson -overwrite -progress

echo "Importing tree_canopies_2021_city_of_melbourne.geojson (This may take a while)..."
ogr2ogr -f "PostgreSQL" "$DB_CONN" -nln tree_canopies data/tree_canopies_2021_city_of_melbourne.geojson -overwrite -progress

echo "✅ All GeoJSON files imported successfully!"
