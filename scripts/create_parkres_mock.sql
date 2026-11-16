-- Fallback only. Prefer scripts/import_clue_and_parkres.js, which loads
-- real park reserves and seats assigned to them.
DROP TABLE IF EXISTS parkres;
CREATE TABLE parkres (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    feature_type VARCHAR(32) NOT NULL DEFAULT 'Reserve',
    bench_count INTEGER NOT NULL DEFAULT 0,
    geom geometry(Point, 4326)
);

INSERT INTO parkres (name, feature_type, bench_count, geom) VALUES
('Flagstaff Gardens', 'Reserve', 15, ST_SetSRID(ST_MakePoint(144.9546, -37.8105), 4326)),
('Flagstaff Gardens Benches', 'Bench', 1, ST_SetSRID(ST_MakePoint(144.9546, -37.8105), 4326)),
('Fitzroy Gardens Rest Area', 'Bench', 1, ST_SetSRID(ST_MakePoint(144.9806, -37.8114), 4326)),
('Carlton Gardens Seating', 'Bench', 1, ST_SetSRID(ST_MakePoint(144.9715, -37.8049), 4326));
