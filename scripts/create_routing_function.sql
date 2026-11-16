-- Straight-path route: pgRouting Dijkstra over the turn-penalized graph.
-- Direction changes are priced in turn_graph, so the cheapest path is the
-- one that stays straight. This replaces edge-azimuth biasing, which did
-- not charge for turns at junctions.

CREATE OR REPLACE FUNCTION get_straight_route(
    start_lon float, start_lat float,
    end_lon float, end_lat float
)
RETURNS TABLE (
    seq integer, path_seq integer, node bigint, edge bigint, cost float, agg_cost float, geom geometry
) AS $fn$
DECLARE
    start_node integer;
    end_node integer;
    edge_sql text;
BEGIN
    IF to_regclass('public.turn_graph') IS NULL OR to_regclass('public.pedestrian_directed') IS NULL THEN
        RAISE EXCEPTION 'Turn-penalized graph is missing. Run scripts/create_turn_graph.sql after scripts/build_topology.sql.';
    END IF;

    SELECT id INTO start_node
    FROM pedestrian_network_vertices
    ORDER BY pedestrian_network_vertices.geom <-> ST_SetSRID(ST_MakePoint(start_lon, start_lat), 4326)
    LIMIT 1;

    SELECT id INTO end_node
    FROM pedestrian_network_vertices
    ORDER BY pedestrian_network_vertices.geom <-> ST_SetSRID(ST_MakePoint(end_lon, end_lat), 4326)
    LIMIT 1;

    IF start_node IS NULL OR end_node IS NULL THEN
        RETURN;
    END IF;

    -- Virtual start vertex -1 pays the first edge length.
    -- Virtual end vertex -2 is free once an edge arrives at the destination node.
    edge_sql := format($q$
        SELECT id::bigint AS id, source::bigint AS source, target::bigint AS target, cost
        FROM turn_graph
        UNION ALL
        SELECT (-1000000000 - id)::bigint, (-1)::bigint, id::bigint, length_m
        FROM pedestrian_directed
        WHERE from_node = %s
        UNION ALL
        SELECT (-2000000000 - id)::bigint, id::bigint, (-2)::bigint, 0::double precision
        FROM pedestrian_directed
        WHERE to_node = %s
    $q$, start_node, end_node);

    RETURN QUERY
    SELECT
        r.seq::integer,
        r.path_seq::integer,
        r.node,
        r.edge,
        r.cost::float,
        r.agg_cost::float,
        d.geom
    FROM pgr_dijkstra(edge_sql, -1::bigint, -2::bigint, true) r
    JOIN pedestrian_directed d ON d.id = r.node
    WHERE r.node > 0
    ORDER BY r.seq;
END;
$fn$ LANGUAGE plpgsql;
