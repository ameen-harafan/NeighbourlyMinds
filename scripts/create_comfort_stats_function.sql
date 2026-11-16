-- Shade density from the DataVic / City of Melbourne tree canopy layer,
-- and bench count from parkres (park reserves with seats assigned to them).

DO $$
BEGIN
    IF to_regclass('public.tree_canopies') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS idx_tree_canopies_geom ON tree_canopies USING GIST (wkb_geometry);
    END IF;
END $$;

CREATE OR REPLACE FUNCTION get_route_comfort_stats(route_geom geometry)
RETURNS TABLE (shade_percentage float, bench_count integer) AS $fn$
DECLARE
    total_length float;
    shaded_length float := 0;
    benches integer := 0;
    route_line geometry;
BEGIN
    IF route_geom IS NULL THEN
        RETURN QUERY SELECT 0.0::float, 0::integer;
        RETURN;
    END IF;

    route_line := ST_LineMerge(route_geom);
    IF GeometryType(route_line) = 'MULTILINESTRING' THEN
        SELECT d.geom INTO route_line
        FROM ST_Dump(route_line) AS d
        ORDER BY ST_Length(d.geom::geography) DESC
        LIMIT 1;
    END IF;

    total_length := ST_Length(route_geom::geography);
    IF total_length IS NULL OR total_length = 0 THEN
        RETURN QUERY SELECT 0.0::float, 0::integer;
        RETURN;
    END IF;

    BEGIN
        -- Shade density: share of sample points within 8 m of a canopy polygon.
        -- Sampling avoids buffering every intersecting canopy on each request.
        SELECT COALESCE(
            100.0 * COUNT(*) FILTER (WHERE covered) / NULLIF(COUNT(*), 0),
            0
        )
        INTO shaded_length
        FROM (
            SELECT EXISTS (
                SELECT 1
                FROM tree_canopies t
                WHERE t.wkb_geometry && ST_Expand(ST_LineInterpolatePoint(route_line, gs::float / 24), 0.00015)
                  AND ST_DWithin(
                    t.wkb_geometry,
                    ST_LineInterpolatePoint(route_line, gs::float / 24),
                    0.00009
                  )
            ) AS covered
            FROM generate_series(0, 24) AS gs
        ) samples;
    EXCEPTION
        WHEN OTHERS THEN
            shaded_length := 0;
    END;

    BEGIN
        -- Park benches: seats stored on parkres that the route passes within 40 m.
        SELECT COUNT(*)::integer
        INTO benches
        FROM parkres p
        WHERE p.feature_type = 'Bench'
          AND p.geom IS NOT NULL
          AND p.geom && ST_Expand(route_geom, 0.001)
          AND ST_DWithin(p.geom::geography, route_geom::geography, 40);
    EXCEPTION
        WHEN undefined_table OR undefined_column THEN
            benches := 0;
    END;

    RETURN QUERY
    SELECT
        LEAST(100.0, GREATEST(0.0, shaded_length))::float,
        COALESCE(benches, 0);
END;
$fn$ LANGUAGE plpgsql;
