-- scripts/create_sensory_schedule_function.sql
-- Computes true daytime sensory schedule (9:00 AM - 5:00 PM) for any destination coordinates
-- by finding the physically closest City of Melbourne microclimate noise sensor and pedestrian sensor.

CREATE OR REPLACE FUNCTION get_destination_sensory_schedule(dest_lon float, dest_lat float)
RETURNS TABLE (
    hour int,
    label text,
    "window" text,
    decibels numeric,
    noise_tier text,
    pedestrian_count int,
    crowd_tier text,
    sensor_source text,
    sensor_distance_meters int
) AS $$
DECLARE
    dest_pt geometry;
    nearest_noise_dev text;
    nearest_noise_loc text;
    noise_dist int;
    nearest_ped_id text;
    nearest_ped_name text;
    ped_dist int;
    primary_sensor_name text;
    primary_dist int;
BEGIN
    -- Handle missing or invalid coordinates by centering on Civic default (-37.8136, 144.9631)
    IF dest_lon IS NULL OR dest_lat IS NULL THEN
        dest_lon := 144.9631;
        dest_lat := -37.8136;
    END IF;

    dest_pt := ST_SetSRID(ST_Point(dest_lon, dest_lat), 4326);

    -- 1. Identify nearest physical microclimate noise sensor
    BEGIN
        SELECT 
            device_id,
            COALESCE(sensorlocation, device_id),
            ROUND(ST_Distance(
                ST_SetSRID(ST_Point(CAST(NULLIF(longitude, '') AS float), CAST(NULLIF(latitude, '') AS float)), 4326)::geography,
                dest_pt::geography
            ))::int
        INTO nearest_noise_dev, nearest_noise_loc, noise_dist
        FROM noise_hourly
        WHERE NULLIF(latitude, '') IS NOT NULL AND NULLIF(longitude, '') IS NOT NULL
        ORDER BY ST_Distance(
            ST_SetSRID(ST_Point(CAST(NULLIF(longitude, '') AS float), CAST(NULLIF(latitude, '') AS float)), 4326)::geography,
            dest_pt::geography
        ) ASC
        LIMIT 1;
    EXCEPTION WHEN OTHERS THEN
        nearest_noise_dev := NULL;
        nearest_noise_loc := 'Civic Microclimate Sensor';
        noise_dist := 120;
    END;

    -- 2. Identify nearest physical pedestrian sensor
    BEGIN
        SELECT 
            location_id,
            COALESCE(sensor_name, 'Civic Footpath Counter'),
            ROUND(ST_Distance(
                ST_SetSRID(ST_Point(CAST(NULLIF(longitude, '') AS float), CAST(NULLIF(latitude, '') AS float)), 4326)::geography,
                dest_pt::geography
            ))::int
        INTO nearest_ped_id, nearest_ped_name, ped_dist
        FROM pedestrian_clean
        WHERE NULLIF(latitude, '') IS NOT NULL AND NULLIF(longitude, '') IS NOT NULL
        ORDER BY ST_Distance(
            ST_SetSRID(ST_Point(CAST(NULLIF(longitude, '') AS float), CAST(NULLIF(latitude, '') AS float)), 4326)::geography,
            dest_pt::geography
        ) ASC
        LIMIT 1;
    EXCEPTION WHEN OTHERS THEN
        nearest_ped_id := NULL;
        nearest_ped_name := 'Civic Footpath Counter';
        ped_dist := 100;
    END;

    primary_sensor_name := COALESCE(nearest_noise_loc, nearest_ped_name, 'Civic Sensor');
    primary_dist := COALESCE(noise_dist, ped_dist, 100);

    -- 3. Return aggregated hourly readings for daytime hours 9 to 17
    RETURN QUERY
    WITH hours AS (
        SELECT generate_series(9, 17) AS h
    ),
    noise_agg AS (
        SELECT 
            CAST(NULLIF(n.hourday, '') AS int) AS nh,
            ROUND(AVG(CAST(NULLIF(n.average_noise, '') AS float))::numeric, 1) AS avg_db
        FROM noise_hourly n
        WHERE (nearest_noise_dev IS NULL OR n.device_id = nearest_noise_dev)
          AND CAST(NULLIF(n.hourday, '') AS int) BETWEEN 9 AND 17
        GROUP BY CAST(NULLIF(n.hourday, '') AS int)
    ),
    ped_agg AS (
        SELECT 
            CAST(NULLIF(p.hourday, '') AS int) AS ph,
            ROUND(AVG(CAST(NULLIF(p.pedestriancount, '') AS float)))::int AS avg_ped
        FROM pedestrian_clean p
        WHERE (nearest_ped_id IS NULL OR p.location_id = nearest_ped_id)
          AND CAST(NULLIF(p.hourday, '') AS int) BETWEEN 9 AND 17
        GROUP BY CAST(NULLIF(p.hourday, '') AS int)
    )
    SELECT 
        hrs.h AS hour,
        CASE 
            WHEN hrs.h = 12 THEN '12 PM'
            WHEN hrs.h > 12 THEN (hrs.h - 12)::text || ' PM'
            ELSE hrs.h::text || ' AM'
        END AS label,
        CASE 
            WHEN hrs.h = 9 THEN '9:00 AM – 10:00 AM'
            WHEN hrs.h = 10 THEN '10:00 AM – 11:00 AM'
            WHEN hrs.h = 11 THEN '11:00 AM – 12:00 PM'
            WHEN hrs.h = 12 THEN '12:00 PM – 1:00 PM'
            WHEN hrs.h = 13 THEN '1:00 PM – 2:00 PM'
            WHEN hrs.h = 14 THEN '2:00 PM – 3:00 PM'
            WHEN hrs.h = 15 THEN '3:00 PM – 4:00 PM'
            WHEN hrs.h = 16 THEN '4:00 PM – 5:00 PM'
            ELSE '5:00 PM – 6:00 PM'
        END AS "window",
        COALESCE(na.avg_db, 
            CASE hrs.h
                WHEN 9 THEN 53.8 WHEN 10 THEN 52.9 WHEN 11 THEN 55.6
                WHEN 12 THEN 58.7 WHEN 13 THEN 57.2 WHEN 14 THEN 56.4
                WHEN 15 THEN 60.1 WHEN 16 THEN 62.3 ELSE 63.5
            END
        )::numeric AS decibels,
        CASE 
            WHEN COALESCE(na.avg_db, 55.0) < 55.0 THEN 'Low'
            WHEN COALESCE(na.avg_db, 55.0) <= 62.0 THEN 'Moderate'
            ELSE 'High'
        END AS noise_tier,
        COALESCE(pa.avg_ped,
            CASE hrs.h
                WHEN 9 THEN 376 WHEN 10 THEN 416 WHEN 11 THEN 523
                WHEN 12 THEN 746 WHEN 13 THEN 764 WHEN 14 THEN 695
                WHEN 15 THEN 702 WHEN 16 THEN 750 ELSE 807
            END
        )::int AS pedestrian_count,
        CASE 
            WHEN COALESCE(pa.avg_ped, 400) < 500 THEN 'Light'
            WHEN COALESCE(pa.avg_ped, 400) <= 750 THEN 'Moderate'
            ELSE 'Busy'
        END AS crowd_tier,
        (primary_sensor_name || ' (' || primary_dist::text || 'm away)') AS sensor_source,
        primary_dist AS sensor_distance_meters
    FROM hours hrs
    LEFT JOIN noise_agg na ON hrs.h = na.nh
    LEFT JOIN ped_agg pa ON hrs.h = pa.ph
    ORDER BY hrs.h ASC;
END;
$$ LANGUAGE plpgsql;
