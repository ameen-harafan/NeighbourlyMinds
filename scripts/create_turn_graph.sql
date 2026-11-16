-- Turn-penalized graph for pgRouting.
-- Each pedestrian edge becomes a directed vertex. A connection between two
-- directed edges pays the outgoing length plus a heavy penalty when the
-- walking direction changes (a turn). Straight continuations are free.

DROP TABLE IF EXISTS turn_graph;
DROP TABLE IF EXISTS pedestrian_directed;

CREATE TABLE pedestrian_directed AS
SELECT
  row_number() OVER ()::bigint AS id,
  from_node,
  to_node,
  edge_id,
  length_m,
  azimuth,
  geom
FROM (
  SELECT
    source AS from_node,
    target AS to_node,
    ogc_fid AS edge_id,
    cost AS length_m,
    ST_Azimuth(ST_StartPoint(wkb_geometry), ST_EndPoint(wkb_geometry)) AS azimuth,
    wkb_geometry AS geom
  FROM pedestrian_network
  WHERE source IS NOT NULL
    AND target IS NOT NULL
    AND cost > 0
    AND ST_Azimuth(ST_StartPoint(wkb_geometry), ST_EndPoint(wkb_geometry)) IS NOT NULL
  UNION ALL
  SELECT
    target AS from_node,
    source AS to_node,
    ogc_fid AS edge_id,
    reverse_cost AS length_m,
    ST_Azimuth(ST_EndPoint(wkb_geometry), ST_StartPoint(wkb_geometry)) AS azimuth,
    ST_Reverse(wkb_geometry) AS geom
  FROM pedestrian_network
  WHERE source IS NOT NULL
    AND target IS NOT NULL
    AND reverse_cost > 0
    AND ST_Azimuth(ST_EndPoint(wkb_geometry), ST_StartPoint(wkb_geometry)) IS NOT NULL
) directed;

CREATE INDEX idx_pedestrian_directed_from ON pedestrian_directed (from_node);
CREATE INDEX idx_pedestrian_directed_to ON pedestrian_directed (to_node);
ANALYZE pedestrian_directed;

-- 200 m added for a turn of 35 degrees or more.
-- 600 m added for a sharp turn or U-turn (100 degrees or more).
-- A longer straight path therefore beats a shorter path that changes direction.
CREATE TABLE turn_graph AS
SELECT
  row_number() OVER ()::bigint AS id,
  a.id AS source,
  b.id AS target,
  (
    b.length_m + CASE
      WHEN degrees(abs(atan2(sin(b.azimuth - a.azimuth), cos(b.azimuth - a.azimuth)))) >= 100 THEN 600
      WHEN degrees(abs(atan2(sin(b.azimuth - a.azimuth), cos(b.azimuth - a.azimuth)))) >= 35 THEN 200
      ELSE 0
    END
  )::double precision AS cost
FROM pedestrian_directed a
JOIN pedestrian_directed b
  ON a.to_node = b.from_node
 AND a.id <> b.id;

CREATE INDEX idx_turn_graph_source ON turn_graph (source);
ANALYZE turn_graph;
