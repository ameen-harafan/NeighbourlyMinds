-- CLUE buildings (Census of Land Use and Employment) at turning nodes of a
-- straight-path route. Instructions read as turn cues, not "walk past".

DROP FUNCTION IF EXISTS get_route_landmarks(geometry);
DROP FUNCTION IF EXISTS nearest_visual_landmark(geometry, float);

ALTER TABLE landmarks ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);
UPDATE landmarks
SET geom = ST_SetSRID(ST_MakePoint(split_part(co_ordinates, ',', 2)::float, split_part(co_ordinates, ',', 1)::float), 4326)
WHERE co_ordinates ~ '^-?[0-9.]+,\s*-?[0-9.]+$'
  AND geom IS NULL;
CREATE INDEX IF NOT EXISTS idx_landmarks_geom ON landmarks USING GIST (geom);

CREATE OR REPLACE FUNCTION nearest_visual_landmark(at_point geometry, radius_m float)
RETURNS TABLE (landmark_name varchar, space_use varchar, distance float) AS $fn$
DECLARE
    cue_name text;
    cue_use text;
    cue_dist float;
BEGIN
    IF at_point IS NULL THEN
        RETURN;
    END IF;

    cue_name := NULL;
    IF to_regclass('public.clue_buildings') IS NOT NULL THEN
        BEGIN
            SELECT
                c.building_name,
                c.predominant_space_use,
                ST_Distance(at_point::geography, c.geom::geography)
            INTO cue_name, cue_use, cue_dist
            FROM clue_buildings c
            WHERE c.geom IS NOT NULL
              AND c.building_name IS NOT NULL
              AND c.building_name <> ''
              AND c.geom && ST_Expand(at_point, radius_m / 90000.0)
              AND ST_DWithin(at_point::geography, c.geom::geography, radius_m)
            ORDER BY c.prominence DESC, ST_Distance(at_point::geography, c.geom::geography)
            LIMIT 1;
        EXCEPTION
            WHEN undefined_table OR undefined_column THEN
                cue_name := NULL;
        END;

        IF cue_name IS NOT NULL THEN
            landmark_name := cue_name;
            space_use := cue_use;
            distance := cue_dist;
            RETURN NEXT;
            RETURN;
        END IF;
    END IF;

    cue_name := NULL;
    IF to_regclass('public.landmarks') IS NOT NULL THEN
        SELECT
            l.feature_name,
            ST_Distance(at_point::geography, l.geom::geography)
        INTO cue_name, cue_dist
        FROM landmarks l
        WHERE l.geom IS NOT NULL
          AND l.feature_name IS NOT NULL
          AND l.feature_name <> ''
          AND l.geom && ST_Expand(at_point, radius_m / 90000.0)
          AND ST_DWithin(at_point::geography, l.geom::geography, radius_m)
        ORDER BY ST_Distance(at_point::geography, l.geom::geography)
        LIMIT 1;

        IF cue_name IS NOT NULL THEN
            landmark_name := cue_name;
            space_use := 'Landmark';
            distance := cue_dist;
            RETURN NEXT;
        END IF;
    END IF;
END;
$fn$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_route_landmarks(route_geom geometry)
RETURNS TABLE (
    landmark_name varchar,
    distance float,
    instruction text,
    turn_direction varchar,
    space_use varchar
) AS $fn$
DECLARE
    route_line geometry;
    pt record;
    prev_pt geometry;
    prev_az double precision;
    next_az double precision;
    signed double precision;
    angle_deg double precision;
    direction text;
    cue_name varchar;
    cue_use varchar;
    cue_dist float;
    label text;
    last_turn geometry;
    turn_steps integer := 0;
BEGIN
    IF route_geom IS NULL THEN
        RETURN;
    END IF;

    route_line := ST_LineMerge(route_geom);
    IF GeometryType(route_line) = 'MULTILINESTRING' THEN
        SELECT d.geom INTO route_line
        FROM ST_Dump(route_line) AS d
        ORDER BY ST_Length(d.geom::geography) DESC
        LIMIT 1;
    END IF;

    IF route_line IS NULL OR GeometryType(route_line) <> 'LINESTRING' THEN
        RETURN;
    END IF;

    SELECT n.landmark_name, n.space_use, n.distance
    INTO cue_name, cue_use, cue_dist
    FROM nearest_visual_landmark(ST_StartPoint(route_line), 120) n;

    IF cue_name IS NOT NULL THEN
        label := CASE WHEN cue_name ILIKE 'the %' THEN cue_name ELSE 'the ' || cue_name END;
        landmark_name := cue_name;
        distance := cue_dist;
        instruction := format('Start near %s', label);
        turn_direction := 'start';
        space_use := cue_use;
        RETURN NEXT;
    ELSE
        landmark_name := 'Start';
        distance := 0;
        instruction := 'Start here and follow the straight path';
        turn_direction := 'start';
        space_use := NULL;
        RETURN NEXT;
    END IF;

    prev_pt := NULL;
    prev_az := NULL;
    last_turn := NULL;

    FOR pt IN
        SELECT (dp).path[1] AS i, (dp).geom AS geom
        FROM (SELECT ST_DumpPoints(route_line) AS dp) dumped
        ORDER BY 1
    LOOP
        IF prev_pt IS NULL THEN
            prev_pt := pt.geom;
            CONTINUE;
        END IF;

        IF ST_Distance(prev_pt::geography, pt.geom::geography) < 5 THEN
            CONTINUE;
        END IF;

        next_az := ST_Azimuth(prev_pt, pt.geom);
        IF prev_az IS NOT NULL AND next_az IS NOT NULL THEN
            signed := atan2(sin(next_az - prev_az), cos(next_az - prev_az));
            angle_deg := degrees(abs(signed));
            IF angle_deg >= 35
               AND (last_turn IS NULL OR ST_Distance(last_turn::geography, prev_pt::geography) >= 40)
               AND turn_steps < 6 THEN
                direction := CASE WHEN signed >= 0 THEN 'right' ELSE 'left' END;
                cue_name := NULL;
                cue_use := NULL;
                cue_dist := NULL;

                SELECT n.landmark_name, n.space_use, n.distance
                INTO cue_name, cue_use, cue_dist
                FROM nearest_visual_landmark(prev_pt, 80) n;

                IF cue_name IS NULL THEN
                    SELECT n.landmark_name, n.space_use, n.distance
                    INTO cue_name, cue_use, cue_dist
                    FROM nearest_visual_landmark(prev_pt, 140) n;
                END IF;

                IF cue_name IS NOT NULL THEN
                    label := CASE WHEN cue_name ILIKE 'the %' THEN cue_name ELSE 'the ' || cue_name END;
                    landmark_name := cue_name;
                    distance := cue_dist;
                    instruction := format('Turn %s at %s', direction, label);
                    turn_direction := direction;
                    space_use := cue_use;
                ELSE
                    landmark_name := format('Turn %s', direction);
                    distance := 0;
                    instruction := format('Turn %s, then keep straight', direction);
                    turn_direction := direction;
                    space_use := NULL;
                END IF;

                RETURN NEXT;
                last_turn := prev_pt;
                turn_steps := turn_steps + 1;
            END IF;
        END IF;

        prev_az := next_az;
        prev_pt := pt.geom;
    END LOOP;

    cue_name := NULL;
    SELECT n.landmark_name, n.space_use, n.distance
    INTO cue_name, cue_use, cue_dist
    FROM nearest_visual_landmark(ST_EndPoint(route_line), 120) n;

    IF cue_name IS NOT NULL THEN
        label := CASE WHEN cue_name ILIKE 'the %' THEN cue_name ELSE 'the ' || cue_name END;
        landmark_name := cue_name;
        distance := cue_dist;
        instruction := format('Arrive near %s', label);
        turn_direction := 'arrive';
        space_use := cue_use;
        RETURN NEXT;
    END IF;
END;
$fn$ LANGUAGE plpgsql;
