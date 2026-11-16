#!/usr/bin/env python3
"""Generate the expanded Student C landmark-aware route data package."""

from __future__ import annotations

import csv
import heapq
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data"
OUT = ROOT / "frontend_backend_files"
PROCESSED_OUT = ROOT / "processed_data"

PROJECT_ESTIMATES = RAW / "lga_modelled_estimates.csv"
ABS_LGA_GEOJSON = RAW / "abs_lga_boundaries_victoria_2025.geojson"
CITY_LANDMARKS_CSV = RAW / "landmarks_places_city_of_melbourne.csv"
PEDESTRIAN_GEOJSON = RAW / "pedestrian_network_city_of_melbourne.geojson"
PUBLIC_TOILETS_CSV = RAW / "public_toilets_city_of_melbourne.csv"
TREE_CANOPY_GEOJSON = RAW / "tree_canopies_2021_city_of_melbourne.geojson"
VICMAP_FOI_GEOJSON = RAW / "vicmap_foi_melbourne_landmark_candidates.geojson"
PTV_STOPS_GEOJSON = RAW / "public_transport_stops_victoria.geojson"

MELBOURNE_BBOX = (144.30, -38.50, 145.80, -37.45)
LANDMARK_MATCH_RADIUS_M = 140

PLACE_TARGETS = [
    ("P001", "Melbourne Central Railway Station"),
    ("P002", "State Library Victoria"),
    ("P003", "Melbourne Town Hall"),
    ("P004", "Federation Square"),
    ("P005", "Parliament Railway Station"),
    ("P006", "Queen Victoria Market"),
    ("P007", "Royal Exhibition Building"),
    ("P008", "The Melbourne Athenaeum Library"),
]

ROUTE_CASES = [
    ("R001", "P001", "P002"),
    ("R002", "P002", "P003"),
    ("R003", "P003", "P004"),
    ("R004", "P004", "P005"),
    ("R005", "P006", "P002"),
    ("R006", "P007", "P001"),
]

TRANSPORT_MODES_FOR_LANDMARKS = {
    "METRO TRAIN",
    "REGIONAL TRAIN",
    "INTERSTATE TRAIN",
    "METRO TRAM",
    "SKYBUS",
    "REGIONAL COACH",
}


@dataclass(frozen=True)
class Place:
    place_id: str
    name: str
    category: str
    lga_code: str
    lat: float
    lon: float
    source_dataset: str


@dataclass(frozen=True)
class LandmarkCandidate:
    candidate_id: str
    name: str
    landmark_group: str
    feature_type: str
    feature_subtype: str
    lat: float
    lon: float
    source_dataset: str
    source_id: str
    prominence_score: float
    confidence_note: str
    qa_status: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clean_name(value: str | None) -> str:
    name = (value or "").strip()
    if name.isupper():
        name = name.title()
    return " ".join(name.split())


def in_melbourne_bbox(lon: float, lat: float) -> bool:
    min_lon, min_lat, max_lon, max_lat = MELBOURNE_BBOX
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    h = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius_m * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def bearing_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    d_lon = lon2 - lon1
    y = math.sin(d_lon) * math.cos(lat2)
    x = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
    )
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def angle_delta(before: float, after: float) -> float:
    return abs((after - before + 180) % 360 - 180)


def turn_label(before: float, after: float) -> str:
    signed = (after - before + 540) % 360 - 180
    if abs(signed) < 35:
        return "straight"
    return "right" if signed > 0 else "left"


def point_id(coord: tuple[float, float]) -> str:
    lon, lat = coord
    return f"N_{lat:.7f}_{lon:.7f}".replace("-", "M").replace(".", "_")


def parse_lat_lon(text: str) -> tuple[float, float]:
    lat_text, lon_text = text.split(",")
    return float(lat_text.strip()), float(lon_text.strip())


def simplify_ring(points: list, step: int = 8) -> list:
    if len(points) <= step + 2:
        return points
    simplified = points[::step]
    if simplified[-1] != points[-1]:
        simplified.append(points[-1])
    if simplified[0] != simplified[-1]:
        simplified.append(simplified[0])
    return simplified


def simplify_geometry(geometry: dict) -> dict:
    if not geometry:
        return geometry
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if geom_type == "Polygon":
        return {"type": "Polygon", "coordinates": [simplify_ring(ring) for ring in coords]}
    if geom_type == "MultiPolygon":
        return {"type": "MultiPolygon", "coordinates": [[simplify_ring(ring) for ring in polygon] for polygon in coords]}
    return geometry


def build_lga_selector_files() -> tuple[list[dict], dict]:
    lga_data = json.loads(ABS_LGA_GEOJSON.read_text(encoding="utf-8"))
    estimates = {row["lga_code"]: row for row in read_csv(PROJECT_ESTIMATES)}
    lga_rows = []
    features = []
    for feature in lga_data.get("features", []):
        props = feature.get("properties") or {}
        geometry = feature.get("geometry")
        if not geometry:
            continue
        lga_code = str(props.get("LGA_CODE_2025", ""))
        estimate = estimates.get(lga_code, {})
        row = {
            "lga_code": lga_code,
            "lga_name": str(props.get("LGA_NAME_2025", "")),
            "state_code": props.get("STATE_CODE_2021", ""),
            "state_name": props.get("STATE_NAME_2021", ""),
            "area_sqkm": props.get("AREA_ALBERS_SQKM", ""),
            "modelled_estimate": estimate.get("modelled_estimate", ""),
            "rounded_estimate": estimate.get("rounded_estimate", ""),
            "estimate_label": "Modelled estimate, not observed local diagnosis" if estimate.get("modelled_estimate") else "No estimate in current project table",
        }
        lga_rows.append(row)
        features.append({"type": "Feature", "properties": row, "geometry": simplify_geometry(geometry)})
    return lga_rows, {"type": "FeatureCollection", "name": "lga_selector_victoria_2025_simplified", "features": features}


def landmark_group_and_score(feature_type: str, feature_subtype: str, source: str, name: str) -> tuple[str, float, str]:
    ft = feature_type.lower()
    st = feature_subtype.lower()
    n = name.lower()
    if source == "public_transport":
        if "train" in st:
            return "transport_station", 5.0, "Official stop data; highly useful if the station sign is visible."
        if "tram" in st:
            return "transport_stop", 3.8, "Official stop data; useful but smaller than a station building."
        return "transport_stop", 3.4, "Official stop data; useful as a fallback public wayfinding cue."
    if source == "public_toilet":
        return "public_facility", 3.2, "Official council facility point; useful as a support point, not always a major visual landmark."
    if source == "city_landmark":
        if any(k in n for k in ["station", "library", "town hall", "market", "square", "hospital"]):
            return "major_public_landmark", 5.0, "Council landmark dataset; strong pilot landmark but visibility still needs street-level QA."
        return "local_landmark", 4.2, "Council landmark dataset; visibility still needs street-level QA."
    mapping = {
        "admin facility": ("civic_government", 4.0),
        "care facility": ("care_facility", 3.1),
        "commercial facility": ("shopping_centre", 4.0),
        "community space": ("community_space", 3.2),
        "community venue": ("community_venue", 3.8),
        "cultural centre": ("library_museum_gallery", 4.6),
        "education centre": ("school_university", 4.0),
        "emergency facility": ("emergency_service", 4.0),
        "health facility": ("health_service", 4.0),
        "hospital": ("hospital_health", 5.0),
        "landmark": ("heritage_landmark", 5.0),
        "place": ("historic_place", 4.2),
        "place of worship": ("place_of_worship", 3.7),
        "recreational resource": ("recreation_landmark", 3.6),
        "reserve": ("park_green_space", 4.1),
        "sport facility": ("sport_recreation", 3.5),
    }
    group, score = mapping.get(ft, ("other_public_feature", 3.0))
    if st in {"library", "museum", "art gallery", "general hospital", "hospital complex", "park", "gardens", "zoo"}:
        score = max(score, 4.7)
    if st in {"train station", "railway station"} or "station" in n:
        score = max(score, 4.8)
    if st in {"shopping centre", "shopping precinct"}:
        score = max(score, 4.3)
    if st in {"playground", "picnic site", "trailhead"}:
        score = max(score, 3.8)
    return group, score, "Victorian Government Vicmap FOI; stable candidate, route-side visibility still needs QA."


def make_candidate(prefix: str, source_number: int, name: str, feature_type: str, feature_subtype: str, lat: float, lon: float, source_dataset: str, source_kind: str, source_id: str) -> LandmarkCandidate | None:
    name = clean_name(name)
    if not name or not in_melbourne_bbox(lon, lat):
        return None
    group, score, note = landmark_group_and_score(feature_type, feature_subtype, source_kind, name)
    return LandmarkCandidate(
        candidate_id=f"{prefix}_{source_number:06d}",
        name=name,
        landmark_group=group,
        feature_type=feature_type,
        feature_subtype=feature_subtype,
        lat=lat,
        lon=lon,
        source_dataset=source_dataset,
        source_id=source_id,
        prominence_score=round(score, 2),
        confidence_note=note,
        qa_status="Machine selected; not street-view verified",
    )


def load_city_landmark_candidates() -> list[LandmarkCandidate]:
    candidates = []
    for index, row in enumerate(read_csv(CITY_LANDMARKS_CSV), start=1):
        try:
            lat, lon = parse_lat_lon(row["co_ordinates"])
        except Exception:
            continue
        candidate = make_candidate("COM", index, row.get("feature_name", ""), row.get("theme", ""), row.get("sub_theme", ""), lat, lon, "City of Melbourne Landmarks and Places of Interest", "city_landmark", row.get("feature_name", ""))
        if candidate:
            candidates.append(candidate)
    return candidates


def load_vicmap_landmark_candidates() -> list[LandmarkCandidate]:
    data = json.loads(VICMAP_FOI_GEOJSON.read_text(encoding="utf-8"))
    candidates = []
    for index, feature in enumerate(data.get("features", []), start=1):
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        if geometry.get("type") != "Point" or len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        candidate = make_candidate(
            "VICMAP",
            index,
            props.get("name_label") or props.get("name") or "",
            props.get("feature_type") or "",
            props.get("feature_subtype") or "",
            lat,
            lon,
            "Vicmap Features of Interest",
            "vicmap",
            str(props.get("ufi") or props.get("pfi") or index),
        )
        if candidate and candidate.prominence_score >= 3.1:
            candidates.append(candidate)
    return candidates


def load_transport_landmark_candidates() -> list[LandmarkCandidate]:
    data = json.loads(PTV_STOPS_GEOJSON.read_text(encoding="utf-8"))
    candidates = []
    for index, feature in enumerate(data.get("features", []), start=1):
        props = feature.get("properties") or {}
        mode = props.get("MODE") or ""
        if mode not in TRANSPORT_MODES_FOR_LANDMARKS:
            continue
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        if geometry.get("type") != "Point" or len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        candidate = make_candidate("PTV", index, props.get("STOP_NAME", ""), "public transport stop", mode.lower(), lat, lon, "Victorian Public Transport Stops", "public_transport", str(props.get("STOP_ID") or index))
        if candidate:
            candidates.append(candidate)
    return candidates


def load_public_toilet_landmark_candidates() -> list[LandmarkCandidate]:
    candidates = []
    for index, row in enumerate(read_csv(PUBLIC_TOILETS_CSV), start=1):
        try:
            lat = float(row["lat"])
            lon = float(row["lon"])
        except Exception:
            continue
        candidate = make_candidate("TOILET", index, row.get("name") or f"Public Toilet {index}", "public toilet", "public toilet", lat, lon, "City of Melbourne Public Toilets", "public_toilet", row.get("asset_id", "") or str(index))
        if candidate:
            candidates.append(candidate)
    return candidates


def build_landmark_candidates() -> list[LandmarkCandidate]:
    raw_candidates = load_city_landmark_candidates() + load_vicmap_landmark_candidates() + load_transport_landmark_candidates() + load_public_toilet_landmark_candidates()
    best_by_key: dict[tuple[str, str, int, int], LandmarkCandidate] = {}
    for candidate in raw_candidates:
        key = (candidate.name.lower(), candidate.landmark_group, round(candidate.lat, 4), round(candidate.lon, 4))
        current = best_by_key.get(key)
        if current is None or candidate.prominence_score > current.prominence_score:
            best_by_key[key] = candidate
    cleaned = []
    for index, candidate in enumerate(best_by_key.values(), start=1):
        cleaned.append(LandmarkCandidate(f"LM_{index:06d}", candidate.name, candidate.landmark_group, candidate.feature_type, candidate.feature_subtype, candidate.lat, candidate.lon, candidate.source_dataset, candidate.source_id, candidate.prominence_score, candidate.confidence_note, candidate.qa_status))
    return sorted(cleaned, key=lambda item: (item.landmark_group, item.name))


def landmark_to_row(candidate: LandmarkCandidate) -> dict:
    return {
        "candidate_id": candidate.candidate_id,
        "name": candidate.name,
        "landmark_group": candidate.landmark_group,
        "feature_type": candidate.feature_type,
        "feature_subtype": candidate.feature_subtype,
        "latitude": round(candidate.lat, 7),
        "longitude": round(candidate.lon, 7),
    }


def build_landmark_geojson(candidates: list[LandmarkCandidate]) -> dict:
    return {
        "type": "FeatureCollection",
        "name": "melbourne_landmark_candidates_for_wayfinding",
        "features": [
            {
                "type": "Feature",
                "properties": {key: value for key, value in landmark_to_row(candidate).items() if key not in {"latitude", "longitude"}},
                "geometry": {"type": "Point", "coordinates": [round(candidate.lon, 7), round(candidate.lat, 7)]},
            }
            for candidate in candidates
        ],
    }


def build_landmark_index(candidates: list[LandmarkCandidate], cell_size: float = 0.003):
    index: dict[tuple[int, int], list[LandmarkCandidate]] = defaultdict(list)
    for candidate in candidates:
        index[(int(candidate.lon / cell_size), int(candidate.lat / cell_size))].append(candidate)
    return index, cell_size


def nearest_landmark(point: tuple[float, float], landmark_index, cell_size: float, radius_m: float = LANDMARK_MATCH_RADIUS_M) -> dict | None:
    lon, lat = point
    gx = int(lon / cell_size)
    gy = int(lat / cell_size)
    best = None
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            for candidate in landmark_index.get((gx + dx, gy + dy), []):
                distance = haversine_m(point, (candidate.lon, candidate.lat))
                if distance > radius_m:
                    continue
                score = candidate.prominence_score * 100 - distance
                if best is None or score > best["score"]:
                    if distance <= 60 and candidate.prominence_score >= 4.0:
                        confidence = "high"
                    elif distance <= 120 and candidate.prominence_score >= 3.5:
                        confidence = "medium"
                    else:
                        confidence = "low"
                    best = {"candidate": candidate, "distance_m": distance, "confidence": confidence, "score": score}
    if best is None:
        return None
    candidate = best["candidate"]
    return {
        "landmark_id": candidate.candidate_id,
        "landmark_name": candidate.name,
        "landmark_group": candidate.landmark_group,
        "landmark_source": candidate.source_dataset,
        "landmark_distance_m": round(best["distance_m"], 1),
        "landmark_confidence": best["confidence"],
        "landmark_prominence_score": candidate.prominence_score,
    }


def build_places() -> list[Place]:
    rows = read_csv(CITY_LANDMARKS_CSV)
    places: list[Place] = []
    for place_id, name in PLACE_TARGETS:
        matches = [row for row in rows if row["feature_name"].strip().lower() == name.lower()]
        if not matches:
            raise ValueError(f"Missing landmark source row: {name}")
        row = matches[0]
        lat, lon = parse_lat_lon(row["co_ordinates"])
        places.append(Place(place_id, name, f"{row['theme']} - {row['sub_theme']}", "24600", lat, lon, "City of Melbourne Landmarks and Places of Interest"))
    return places


def load_graph(places: list[Place]):
    min_lat = min(place.lat for place in places) - 0.015
    max_lat = max(place.lat for place in places) + 0.015
    min_lon = min(place.lon for place in places) - 0.015
    max_lon = max(place.lon for place in places) + 0.015
    data = json.loads(PEDESTRIAN_GEOJSON.read_text(encoding="utf-8"))
    nodes: dict[str, tuple[float, float]] = {}
    edges = []
    adjacency: dict[str, list[tuple[str, float, float, str]]] = defaultdict(list)
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "LineString":
            continue
        coords = geometry.get("coordinates") or []
        for start, end in zip(coords, coords[1:]):
            a = (float(start[0]), float(start[1]))
            b = (float(end[0]), float(end[1]))
            if not (min_lon <= a[0] <= max_lon and min_lon <= b[0] <= max_lon and min_lat <= a[1] <= max_lat and min_lat <= b[1] <= max_lat):
                continue
            a_id = point_id(a)
            b_id = point_id(b)
            nodes[a_id] = a
            nodes[b_id] = b
            edge_id = f"E{len(edges) + 1:05d}"
            length = haversine_m(a, b)
            edges.append({"edge_id": edge_id, "from_node_id": a_id, "to_node_id": b_id, "length_m": round(length, 2), "walk_access": "yes", "source": "City of Melbourne Pedestrian Network"})
            adjacency[a_id].append((b_id, length, bearing_deg(a, b), edge_id))
            adjacency[b_id].append((a_id, length, bearing_deg(b, a), edge_id))
    return nodes, edges, adjacency


def nearest_node(place: Place, nodes: dict[str, tuple[float, float]]) -> str:
    return min(nodes, key=lambda node: haversine_m((place.lon, place.lat), nodes[node]))


def reconstruct_path(parents: dict[str, str | None], end: str) -> list[str]:
    path = [end]
    current = end
    while parents[current] is not None:
        current = parents[current] or ""
        path.append(current)
    path.reverse()
    return path


def shortest_path(start: str, end: str, adjacency) -> list[str]:
    queue = [(0.0, start)]
    distances = {start: 0.0}
    parents: dict[str, str | None] = {start: None}
    while queue:
        current_distance, node = heapq.heappop(queue)
        if node == end:
            break
        if current_distance > distances[node]:
            continue
        for next_node, length, _bearing, _edge_id in adjacency[node]:
            new_distance = current_distance + length
            if new_distance < distances.get(next_node, float("inf")):
                distances[next_node] = new_distance
                parents[next_node] = node
                heapq.heappush(queue, (new_distance, next_node))
    return reconstruct_path(parents, end) if end in parents else []


def fewer_turn_path(start: str, end: str, adjacency) -> list[str]:
    start_state = (start, None)
    queue = [(0.0, start_state)]
    distances = {start_state: 0.0}
    parents: dict[tuple[str, float | None], tuple[str, float | None] | None] = {start_state: None}
    best_end_state = None
    while queue:
        current_cost, state = heapq.heappop(queue)
        node, previous_bearing = state
        if node == end:
            best_end_state = state
            break
        if current_cost > distances[state]:
            continue
        for next_node, length, next_bearing, _edge_id in adjacency[node]:
            penalty = 90.0 if previous_bearing is not None and angle_delta(previous_bearing, next_bearing) >= 35 else 0.0
            next_state = (next_node, round(next_bearing, 3))
            new_cost = current_cost + length + penalty
            if new_cost < distances.get(next_state, float("inf")):
                distances[next_state] = new_cost
                parents[next_state] = state
                heapq.heappush(queue, (new_cost, next_state))
    if best_end_state is None:
        return []
    path = []
    state = best_end_state
    while state is not None:
        path.append(state[0])
        state = parents[state]
    path.reverse()
    return path


def path_length(path: list[str], nodes: dict[str, tuple[float, float]]) -> float:
    return sum(haversine_m(nodes[a], nodes[b]) for a, b in zip(path, path[1:]))


def turn_count(path: list[str], nodes: dict[str, tuple[float, float]]) -> int:
    bearings = [bearing_deg(nodes[a], nodes[b]) for a, b in zip(path, path[1:])]
    return sum(1 for a, b in zip(bearings, bearings[1:]) if angle_delta(a, b) >= 35)


def add_landmark_fields(step: dict, match: dict | None) -> dict:
    if match:
        step.update(match)
    else:
        step.update({"landmark_id": "", "landmark_name": "", "landmark_group": "", "landmark_source": "", "landmark_distance_m": "", "landmark_confidence": "none", "landmark_prominence_score": ""})
    return step


def instruction_with_landmark(base_text: str, match: dict | None) -> str:
    if not match or match["landmark_confidence"] == "low":
        return base_text
    return f"{base_text} Use {match['landmark_name']} as the visual cue."


def build_steps(route_id: str, path: list[str], nodes, origin: Place, destination: Place, landmark_index, landmark_cell_size: float) -> list[dict]:
    start_match = nearest_landmark((origin.lon, origin.lat), landmark_index, landmark_cell_size)
    steps = [
        add_landmark_fields(
            {"route_id": route_id, "step_order": 1, "instruction_text": f"Start near {origin.name}.", "distance_m": 0, "turn_type": "start", "latitude": round(origin.lat, 7), "longitude": round(origin.lon, 7)},
            start_match,
        )
    ]
    if len(path) < 2:
        steps.append(add_landmark_fields({"route_id": route_id, "step_order": 2, "instruction_text": "No connected walking route found.", "distance_m": 0, "turn_type": "no_path", "latitude": "", "longitude": ""}, None))
        return steps

    distance_since_instruction = haversine_m(nodes[path[0]], nodes[path[1]])
    previous_bearing = bearing_deg(nodes[path[0]], nodes[path[1]])
    for index in range(1, len(path) - 1):
        current_node = path[index]
        next_node = path[index + 1]
        next_bearing = bearing_deg(nodes[current_node], nodes[next_node])
        if angle_delta(previous_bearing, next_bearing) >= 35 and distance_since_instruction >= 20:
            turn = turn_label(previous_bearing, next_bearing)
            point = nodes[current_node]
            match = nearest_landmark(point, landmark_index, landmark_cell_size)
            metres = round(distance_since_instruction)
            base_text = f"Continue for about {metres} m, then turn {turn}."
            steps.append(add_landmark_fields({"route_id": route_id, "step_order": len(steps) + 1, "instruction_text": instruction_with_landmark(base_text, match), "distance_m": metres, "turn_type": turn, "latitude": round(point[1], 7), "longitude": round(point[0], 7)}, match))
            distance_since_instruction = 0.0
        distance_since_instruction += haversine_m(nodes[current_node], nodes[next_node])
        previous_bearing = next_bearing

    if distance_since_instruction >= 10:
        metres = round(distance_since_instruction)
        point = nodes[path[-1]]
        arrival_match = nearest_landmark((destination.lon, destination.lat), landmark_index, landmark_cell_size)
        base_text = f"Continue for about {metres} m toward {destination.name}."
        steps.append(add_landmark_fields({"route_id": route_id, "step_order": len(steps) + 1, "instruction_text": instruction_with_landmark(base_text, arrival_match), "distance_m": metres, "turn_type": "straight", "latitude": round(point[1], 7), "longitude": round(point[0], 7)}, arrival_match))

    arrival_match = nearest_landmark((destination.lon, destination.lat), landmark_index, landmark_cell_size)
    steps.append(add_landmark_fields({"route_id": route_id, "step_order": len(steps) + 1, "instruction_text": f"Arrive near {destination.name}.", "distance_m": 0, "turn_type": "arrival", "latitude": round(destination.lat, 7), "longitude": round(destination.lon, 7)}, arrival_match))
    return steps


def sample_path(path: list[str], nodes: dict[str, tuple[float, float]], interval_m: float = 25.0) -> list[tuple[float, float]]:
    samples = []
    for a_id, b_id in zip(path, path[1:]):
        a = nodes[a_id]
        b = nodes[b_id]
        length = max(haversine_m(a, b), 1)
        steps = max(1, int(length // interval_m))
        for index in range(steps):
            ratio = index / steps
            samples.append((a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio))
    if path:
        samples.append(nodes[path[-1]])
    return samples


def ring_bbox(ring: list) -> tuple[float, float, float, float]:
    lons = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    return min(lons), min(lats), max(lons), max(lats)


def point_in_ring(point: tuple[float, float], ring: list) -> bool:
    x, y = point
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        intersects = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi)
        if intersects:
            inside = not inside
        j = i
    return inside


def iter_outer_rings(geometry: dict):
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if geom_type == "Polygon" and coords:
        yield coords[0]
    elif geom_type == "MultiPolygon":
        for polygon in coords:
            if polygon:
                yield polygon[0]


def build_canopy_index() -> dict[tuple[int, int], list[tuple[tuple[float, float, float, float], list]]]:
    data = json.loads(TREE_CANOPY_GEOJSON.read_text(encoding="utf-8"))
    cell_size = 0.002
    index: dict[tuple[int, int], list[tuple[tuple[float, float, float, float], list]]] = defaultdict(list)
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        for ring in iter_outer_rings(geometry):
            if len(ring) < 4:
                continue
            bbox = ring_bbox(ring)
            min_x, min_y, max_x, max_y = bbox
            for gx in range(int(min_x / cell_size), int(max_x / cell_size) + 1):
                for gy in range(int(min_y / cell_size), int(max_y / cell_size) + 1):
                    index[(gx, gy)].append((bbox, ring))
    return index


def canopy_ratio(samples: list[tuple[float, float]], canopy_index) -> tuple[float, int, int]:
    if not samples:
        return 0.0, 0, 0
    cell_size = 0.002
    covered = 0
    for point in samples:
        x, y = point
        candidates = canopy_index.get((int(x / cell_size), int(y / cell_size)), [])
        if any(min_x <= x <= max_x and min_y <= y <= max_y and point_in_ring(point, ring) for (min_x, min_y, max_x, max_y), ring in candidates):
            covered += 1
    return covered / len(samples), covered, len(samples)


def support_points_for_route(route_id: str, path: list[str], nodes) -> list[dict]:
    coords = [nodes[node] for node in path]
    points = []
    for index, row in enumerate(read_csv(PUBLIC_TOILETS_CSV), start=1):
        lat = float(row["lat"])
        lon = float(row["lon"])
        point = (lon, lat)
        nearest = min((haversine_m(point, coord) for coord in coords), default=float("inf"))
        if nearest <= 120:
            points.append({"support_point_id": f"SP_{route_id}_{index:03d}", "route_id": route_id, "name": row["name"], "support_type": "public_toilet", "latitude": round(lat, 7), "longitude": round(lon, 7), "wheelchair": row.get("wheelchair", ""), "baby_facility": row.get("baby_facil", ""), "distance_to_route_m": round(nearest, 1), "source": "City of Melbourne Public Toilets"})
    return points[:5]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    lga_rows, lga_geojson = build_lga_selector_files()
    places = build_places()
    landmark_candidates = build_landmark_candidates()
    landmark_rows = [landmark_to_row(candidate) for candidate in landmark_candidates]
    landmark_index, landmark_cell_size = build_landmark_index(landmark_candidates)
    nodes, graph_edges, adjacency = load_graph(places)
    canopy_index = build_canopy_index()
    place_lookup = {place.place_id: place for place in places}
    place_nodes = {place.place_id: nearest_node(place, nodes) for place in places}

    places_rows = [{"place_id": p.place_id, "name": p.name, "category": p.category, "lga_code": p.lga_code, "latitude": round(p.lat, 7), "longitude": round(p.lon, 7), "source": p.source_dataset} for p in places]
    route_rows = []
    route_steps = []
    route_step_landmarks = []
    support_rows = []
    canopy_rows = []
    pocket_cards = []
    used_node_ids = set()
    used_edge_node_pairs = set()

    for route_id, origin_id, destination_id in ROUTE_CASES:
        origin = place_lookup[origin_id]
        destination = place_lookup[destination_id]
        start = place_nodes[origin_id]
        end = place_nodes[destination_id]
        shortest = shortest_path(start, end, adjacency)
        fewer = fewer_turn_path(start, end, adjacency)
        shortest_length = path_length(shortest, nodes) if shortest else 0
        fewer_length = path_length(fewer, nodes) if fewer else 0
        shortest_turns = turn_count(shortest, nodes) if shortest else 0
        fewer_turns = turn_count(fewer, nodes) if fewer else 0
        extra_ratio = ((fewer_length - shortest_length) / shortest_length) if shortest_length and fewer else 0
        use_fewer = fewer and fewer_turns < shortest_turns and extra_ratio <= 0.25
        selected = fewer if use_fewer else shortest
        strategy = "fewer_turns" if use_fewer else "shortest_baseline"
        selected_length = path_length(selected, nodes) if selected else 0
        selected_turns = turn_count(selected, nodes) if selected else 0
        samples = sample_path(selected, nodes)
        canopy, covered_samples, total_samples = canopy_ratio(samples, canopy_index)
        supports = support_points_for_route(route_id, selected, nodes)
        steps = build_steps(route_id, selected, nodes, origin, destination, landmark_index, landmark_cell_size)

        used_node_ids.update(selected)
        used_edge_node_pairs.update(tuple(sorted(pair)) for pair in zip(selected, selected[1:]))
        turn_steps = [step for step in steps if step["turn_type"] in {"left", "right"}]
        matched_turn_steps = [step for step in turn_steps if step["landmark_confidence"] in {"high", "medium"}]
        all_matched_steps = [step for step in steps if step["landmark_confidence"] in {"high", "medium"}]

        route_rows.append({
            "route_id": route_id,
            "origin_place_id": origin_id,
            "origin_name": origin.name,
            "destination_place_id": destination_id,
            "destination_name": destination.name,
            "selected_strategy": strategy,
            "total_length_m": round(selected_length, 1),
            "meaningful_turns": selected_turns,
            "shortest_length_m": round(shortest_length, 1),
            "shortest_turns": shortest_turns,
            "fewer_turn_length_m": round(fewer_length, 1) if fewer else "",
            "fewer_turns": fewer_turns if fewer else "",
            "extra_distance_ratio": round(extra_ratio, 4),
            "route_step_count": len(steps),
            "landmark_matched_steps": len(all_matched_steps),
            "turn_steps_with_landmark": len(matched_turn_steps),
            "turn_landmark_coverage_ratio": round(len(matched_turn_steps) / len(turn_steps), 3) if turn_steps else 1,
            "public_toilet_support_points": len(supports),
            "canopy_sample_ratio": round(canopy, 3),
            "data_limitations": "Landmark candidates cover Greater Melbourne, but route network remains City of Melbourne pilot; manual visibility QA required.",
        })
        canopy_rows.append({"route_id": route_id, "canopy_sample_ratio": round(canopy, 3), "covered_sample_points": covered_samples, "total_sample_points": total_samples, "label": "Historical canopy proxy, not live shade", "source": "City of Melbourne Tree Canopies 2021"})
        route_steps.extend(steps)
        route_step_landmarks.extend({
            "route_id": step["route_id"],
            "step_order": step["step_order"],
            "turn_type": step["turn_type"],
            "latitude": step["latitude"],
            "longitude": step["longitude"],
            "landmark_id": step["landmark_id"],
            "landmark_name": step["landmark_name"],
            "landmark_group": step["landmark_group"],
            "landmark_distance_m": step["landmark_distance_m"],
            "landmark_confidence": step["landmark_confidence"],
            "landmark_source": step["landmark_source"],
        } for step in steps)
        support_rows.extend(supports)
        pocket_cards.append({
            "payload_id": f"{route_id}_CARD",
            "route_id": route_id,
            "title": f"{origin.name} to {destination.name}",
            "selected_strategy": strategy,
            "total_length_m": round(selected_length, 1),
            "meaningful_turns": selected_turns,
            "landmark_matched_steps": len(all_matched_steps),
            "turn_landmark_coverage_ratio": route_rows[-1]["turn_landmark_coverage_ratio"],
            "canopy": canopy_rows[-1],
            "support_points": supports,
            "steps": [{"order": step["step_order"], "text": step["instruction_text"], "distance_m": step["distance_m"], "turn_type": step["turn_type"], "landmark": step["landmark_name"] or None, "landmark_confidence": step["landmark_confidence"]} for step in steps],
            "source_notes": [
                "Landmark candidates combine Vicmap FOI, City of Melbourne landmarks, Public Transport Stops and Public Toilets.",
                "Routes use City of Melbourne Pedestrian Network open data.",
                "Canopy is based on 2021 tree canopy geometry and is not live shade.",
                "Route-side visibility, crossings and entrances still need manual QA before real navigation use.",
            ],
            "created_at": date.today().isoformat(),
        })

    node_rows = [{"node_id": node_id, "latitude": round(nodes[node_id][1], 7), "longitude": round(nodes[node_id][0], 7), "source": "City of Melbourne Pedestrian Network"} for node_id in sorted(used_node_ids)]
    edge_rows = [edge for edge in graph_edges if tuple(sorted([edge["from_node_id"], edge["to_node_id"]])) in used_edge_node_pairs]
    group_counts = Counter(row["landmark_group"] for row in landmark_rows)
    source_counts = Counter(candidate.source_dataset for candidate in landmark_candidates)
    category_summary = [{"landmark_group": group, "candidate_count": count} for group, count in sorted(group_counts.items())]

    data_sources = [
        {"source_id": "S1", "dataset": "ABS ASGS Local Government Area Boundaries 2025", "publisher": "Australian Bureau of Statistics", "file_used": "raw_data/abs_lga_boundaries_victoria_2025.geojson", "url": "https://geo.abs.gov.au/arcgis/rest/services/ASGS2025/LGA/MapServer/0/query", "used_for": "Victoria LGA selector geometry and lga_code join", "limitation": "Boundary geometry only; dementia numbers are joined modelled estimates, not observations."},
        {"source_id": "S2", "dataset": "Landmarks and Places of Interest", "publisher": "City of Melbourne", "file_used": "raw_data/landmarks_places_city_of_melbourne.csv", "url": "https://data.melbourne.vic.gov.au/explore/dataset/landmarks-and-places-of-interest-including-schools-theatres-health-services-spor/", "used_for": "High-quality local landmarks and route start/end pilot places", "limitation": "Does not prove every landmark is visible from the walking route."},
        {"source_id": "S3", "dataset": "Pedestrian Network", "publisher": "City of Melbourne / Victorian open data", "file_used": "raw_data/pedestrian_network_city_of_melbourne.geojson", "url": "https://discover.data.vic.gov.au/dataset/pedestrian-network", "used_for": "Walking graph, shortest route and fewer-turn route comparison", "limitation": "City of Melbourne pilot network only. Route needs manual safety QA."},
        {"source_id": "S4", "dataset": "Public Toilets", "publisher": "City of Melbourne", "file_used": "raw_data/public_toilets_city_of_melbourne.csv", "url": "https://data.melbourne.vic.gov.au/explore/dataset/public-toilets/", "used_for": "Support points and public-facility landmarks near routes", "limitation": "Toilets are support points, not benches or guaranteed rest stops."},
        {"source_id": "S5", "dataset": "Tree Canopies 2021 Urban Forest", "publisher": "City of Melbourne", "file_used": "raw_data/tree_canopies_2021_city_of_melbourne.geojson", "url": "https://data.melbourne.vic.gov.au/explore/dataset/tree-canopies-2021-urban-forest/export/", "used_for": "Historical canopy comfort proxy for selected routes", "limitation": "Historical canopy geometry only; not live shade or weather."},
        {"source_id": "S6", "dataset": "NeighbourlyMinds LGA Modelled Dementia Estimates", "publisher": "Project processed ABS and AIHW data", "file_used": "raw_data/lga_modelled_estimates.csv", "url": "local project file derived from ABS and AIHW source workbooks", "used_for": "Join modelled estimate labels to LGA selector", "limitation": "Modelled estimate only; not observed local diagnosis."},
        {"source_id": "S7", "dataset": "Vicmap Features of Interest - FOI Index Centroid", "publisher": "Victorian Government", "file_used": "raw_data/vicmap_foi_melbourne_landmark_candidates.geojson", "url": "https://discover.data.vic.gov.au/dataset/vicmap-features-of-interest-rest-api", "used_for": "Broad Melbourne landmark candidates: parks, schools, hospitals, libraries, civic buildings, worship places, sport and community facilities", "limitation": "Official feature location, but not proof of street-level visibility from a specific route."},
        {"source_id": "S8", "dataset": "Public Transport Stops", "publisher": "Department of Transport and Planning Victoria", "file_used": "raw_data/public_transport_stops_victoria.geojson", "url": "https://discover.data.vic.gov.au/dataset/public-transport-lines-and-stops", "used_for": "Train, tram, coach and SkyBus stops as recognisable transport landmarks", "limitation": "Stop points can represent platforms or signs; route-side visibility still needs QA."},
    ]
    app_manifest = {
        "generated_at": date.today().isoformat(),
        "scope": "Expanded Student C Iteration 2 data package: Victoria LGA selector, Greater Melbourne landmark candidates, City of Melbourne route pilot.",
        "frontend_entry_files": {
            "lga_selector": "lga_selector_for_app.geojson",
            "places": "places_for_app.json",
            "landmark_candidates": "landmark_candidates_for_app.json",
            "landmark_candidates_geojson": "landmark_candidates_for_app.geojson",
            "landmark_category_summary": "landmark_category_summary.csv",
            "routes": "route_results_for_app.json",
            "route_steps": "route_steps_for_app.json",
            "route_step_landmarks": "route_step_landmarks_for_app.json",
            "support_points": "support_points_for_app.json",
            "canopy_context": "route_canopy_context_for_app.json",
            "pocket_cards": "pocket_card_payloads.json",
        },
        "counts": {
            "lga_features": len(lga_geojson["features"]),
            "places": len(places_rows),
            "landmark_candidates": len(landmark_rows),
            "landmark_groups": len(group_counts),
            "landmark_sources": dict(source_counts),
            "routes": len(route_rows),
            "route_steps": len(route_steps),
            "route_step_landmark_rows": len(route_step_landmarks),
            "support_points": len(support_rows),
            "route_nodes": len(node_rows),
            "route_edges": len(edge_rows),
        },
        "limitations": [
            "Expanded landmark candidates cover Greater Melbourne, but the walking route graph remains a City of Melbourne pilot.",
            "Landmark matching is spatial and rule-based; it does not prove a user can see the landmark from the footpath.",
            "Manual QA is still required for crossings, entrances, construction changes and visual clarity.",
            "Canopy is a historical proxy, not live shade.",
            "Public toilets are support points, not benches.",
            "LGA dementia numbers are modelled estimates, not observed counts.",
        ],
    }
    cleaning_quality = {
        "generated_at": app_manifest["generated_at"],
        "scope": app_manifest["scope"],
        "counts": app_manifest["counts"],
        "limitations": app_manifest["limitations"],
    }

    write_csv(OUT / "data_sources_used.csv", data_sources)
    write_json(OUT / "data_sources_used.json", data_sources)
    write_csv(OUT / "lga_selector_for_app.csv", lga_rows)
    write_json(OUT / "lga_selector_for_app.geojson", lga_geojson)
    write_csv(OUT / "places_for_app.csv", places_rows)
    write_json(OUT / "places_for_app.json", places_rows)
    write_csv(OUT / "landmark_candidates_for_app.csv", landmark_rows)
    write_json(OUT / "landmark_candidates_for_app.json", landmark_rows)
    write_json(OUT / "landmark_candidates_for_app.geojson", build_landmark_geojson(landmark_candidates))
    write_csv(OUT / "landmark_category_summary.csv", category_summary)
    write_csv(OUT / "route_nodes_for_app.csv", node_rows)
    write_json(OUT / "route_nodes_for_app.json", node_rows)
    write_csv(OUT / "route_edges_for_app.csv", edge_rows)
    write_json(OUT / "route_edges_for_app.json", edge_rows)
    write_csv(OUT / "route_results_for_app.csv", route_rows)
    write_json(OUT / "route_results_for_app.json", route_rows)
    write_csv(OUT / "route_steps_for_app.csv", route_steps)
    write_json(OUT / "route_steps_for_app.json", route_steps)
    write_csv(OUT / "route_step_landmarks_for_app.csv", route_step_landmarks)
    write_json(OUT / "route_step_landmarks_for_app.json", route_step_landmarks)
    write_csv(OUT / "support_points_for_app.csv", support_rows)
    write_json(OUT / "support_points_for_app.json", support_rows)
    write_csv(OUT / "route_canopy_context_for_app.csv", canopy_rows)
    write_json(OUT / "route_canopy_context_for_app.json", canopy_rows)
    write_json(OUT / "pocket_card_payloads.json", pocket_cards)
    write_json(OUT / "app_data_manifest.json", app_manifest)

    write_csv(PROCESSED_OUT / "cleaned_landmark_candidates.csv", landmark_rows)
    write_json(PROCESSED_OUT / "cleaned_landmark_candidates.json", landmark_rows)
    write_json(PROCESSED_OUT / "cleaned_landmark_candidates.geojson", build_landmark_geojson(landmark_candidates))
    write_csv(PROCESSED_OUT / "cleaned_landmark_category_summary.csv", category_summary)
    write_csv(PROCESSED_OUT / "cleaned_route_results_with_landmark_coverage.csv", route_rows)
    write_csv(PROCESSED_OUT / "cleaned_route_step_landmark_matches.csv", route_step_landmarks)
    write_json(PROCESSED_OUT / "cleaned_route_step_landmark_matches.json", route_step_landmarks)
    write_json(PROCESSED_OUT / "cleaning_quality_summary.json", cleaning_quality)

    readme = f"""# Student C Expanded Iteration 2 Delivery

Generated: {date.today().isoformat()}

This package supports AC 5.1.1 Straight-Path Comfort Routing with Landmark
Reassurance and AC 5.1.2 Print-Ready Pocket Independence Card.

## What changed in this expanded version

The first version only had a small set of pilot landmarks. This version adds a
larger official landmark candidate layer for Greater Melbourne by combining:

- Vicmap Features of Interest: parks, schools, hospitals, libraries, civic
  facilities, worship places, shopping centres, community venues and sport
  facilities.
- Victorian Public Transport Stops: train, tram, coach and SkyBus stops.
- City of Melbourne Landmarks and Places of Interest.
- City of Melbourne Public Toilets as support-point landmarks.

The processing code matches nearby landmark candidates to each generated route
instruction, so the frontend can display landmark reassurance directly.

## Main frontend/backend files

- app_data_manifest.json
- data_sources_used.json/csv
- lga_selector_for_app.geojson/csv
- places_for_app.json/csv
- landmark_candidates_for_app.json/csv/geojson
- landmark_category_summary.csv
- route_results_for_app.json/csv
- route_steps_for_app.json/csv
- route_step_landmarks_for_app.json/csv
- route_nodes_for_app.json/csv
- route_edges_for_app.json/csv
- support_points_for_app.json/csv
- route_canopy_context_for_app.json/csv
- pocket_card_payloads.json

## Important limitation

The landmark layer is much wider now, but this is still not a real
safety-certified navigation system. The route graph is still a City of Melbourne
pilot because the available pedestrian network file is City of Melbourne based.
Landmark matching is spatial and rule-based, so each recommended cue still needs
manual QA for street-level visibility, entrances, crossings and temporary
construction changes.
"""
    (OUT / "README_for_frontend_backend.md").write_text(readme, encoding="utf-8")
    print(json.dumps(app_manifest["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
