-- scripts/build_topology.sql
ALTER TABLE pedestrian_network ADD COLUMN IF NOT EXISTS "source" integer;
ALTER TABLE pedestrian_network ADD COLUMN IF NOT EXISTS "target" integer;
ALTER TABLE pedestrian_network ADD COLUMN IF NOT EXISTS "cost" double precision;
ALTER TABLE pedestrian_network ADD COLUMN IF NOT EXISTS "reverse_cost" double precision;

DROP TABLE IF EXISTS pedestrian_network_vertices;
CREATE TABLE pedestrian_network_vertices AS
SELECT row_number() over() as id, geom
FROM (
  SELECT DISTINCT ST_SnapToGrid(ST_StartPoint(wkb_geometry), 0.00001) as geom FROM pedestrian_network
  UNION
  SELECT DISTINCT ST_SnapToGrid(ST_EndPoint(wkb_geometry), 0.00001) as geom FROM pedestrian_network
) AS unique_pts;

CREATE INDEX idx_pedestrian_vertices_geom ON pedestrian_network_vertices USING GIST (geom);
ANALYZE pedestrian_network_vertices;

-- Update source
UPDATE pedestrian_network p
SET source = v.id
FROM pedestrian_network_vertices v
WHERE v.geom && ST_SnapToGrid(ST_StartPoint(p.wkb_geometry), 0.00001)
  AND ST_Equals(v.geom, ST_SnapToGrid(ST_StartPoint(p.wkb_geometry), 0.00001));

-- Update target
UPDATE pedestrian_network p
SET target = v.id
FROM pedestrian_network_vertices v
WHERE v.geom && ST_SnapToGrid(ST_EndPoint(p.wkb_geometry), 0.00001)
  AND ST_Equals(v.geom, ST_SnapToGrid(ST_EndPoint(p.wkb_geometry), 0.00001));

-- Calculate cost as length in meters
UPDATE pedestrian_network 
SET cost = ST_Length(wkb_geometry::geography), 
    reverse_cost = ST_Length(wkb_geometry::geography);
