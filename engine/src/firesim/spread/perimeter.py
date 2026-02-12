"""Fire perimeter extraction and analysis.

Converts fire front vertices to GeoJSON-compatible polygons,
calculates area, and provides polygon utilities.
"""

from __future__ import annotations

import math

from firesim.spread.huygens import FireVertex


def vertices_to_polygon(vertices: list[FireVertex]) -> list[tuple[float, float]]:
    """Convert fire vertices to a closed polygon of (lat, lng) tuples.

    Args:
        vertices: Fire front vertices

    Returns:
        List of (lat, lng) tuples forming a closed polygon.
        First and last points are the same.
    """
    if not vertices:
        return []

    coords = [(v.lat, v.lng) for v in vertices]

    # Close the polygon if not already closed
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    return coords


def calculate_polygon_area_ha(vertices: list[FireVertex]) -> float:
    """Calculate polygon area in hectares using the Shoelace formula.

    Uses a local meter-based projection from the centroid for accuracy.

    Args:
        vertices: Fire front vertices (at least 3)

    Returns:
        Area in hectares
    """
    if len(vertices) < 3:
        return 0.0

    # Calculate centroid for local projection
    cx = sum(v.lat for v in vertices) / len(vertices)

    # Convert to local meters
    m_per_deg_lat = 111320.0
    m_per_deg_lng = 111320.0 * math.cos(math.radians(cx))

    # Shoelace formula in meters
    n = len(vertices)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        xi = (vertices[i].lng) * m_per_deg_lng
        yi = (vertices[i].lat) * m_per_deg_lat
        xj = (vertices[j].lng) * m_per_deg_lng
        yj = (vertices[j].lat) * m_per_deg_lat
        area += xi * yj - xj * yi

    area_m2 = abs(area) / 2.0
    return area_m2 / 10000.0  # m2 to hectares


def polygon_to_geojson(
    vertices: list[FireVertex],
    properties: dict | None = None,
) -> dict:
    """Convert fire vertices to a GeoJSON Feature.

    Args:
        vertices: Fire front vertices
        properties: Optional properties dict for the Feature

    Returns:
        GeoJSON Feature dict with Polygon geometry.
        Coordinates are [lng, lat] per GeoJSON spec.
    """
    if not vertices:
        return {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": []},
            "properties": properties or {},
        }

    # GeoJSON uses [longitude, latitude] order
    coords = [[v.lng, v.lat] for v in vertices]
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords],
        },
        "properties": properties or {},
    }


def calculate_centroid(vertices: list[FireVertex]) -> tuple[float, float]:
    """Calculate centroid of fire front vertices.

    Args:
        vertices: Fire front vertices

    Returns:
        (lat, lng) of the centroid
    """
    if not vertices:
        return 0.0, 0.0
    lat = sum(v.lat for v in vertices) / len(vertices)
    lng = sum(v.lng for v in vertices) / len(vertices)
    return lat, lng
