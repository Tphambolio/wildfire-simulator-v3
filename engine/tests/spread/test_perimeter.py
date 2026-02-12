"""Tests for fire perimeter extraction and analysis.

Tests cover polygon conversion, area calculation, GeoJSON export,
and centroid calculation.
"""

import math

import pytest

from firesim.spread.huygens import FireVertex
from firesim.spread.perimeter import (
    calculate_centroid,
    calculate_polygon_area_ha,
    polygon_to_geojson,
    vertices_to_polygon,
)


@pytest.fixture
def square_vertices():
    """A ~1km square at latitude 51.

    Vertices form a square roughly 1km on each side.
    At lat 51: 1 deg lat = 111320m, 1 deg lng = 111320*cos(51) = ~70080m
    So ~1km = 0.009 deg lat, 0.01427 deg lng
    """
    half_lat = 0.0045  # ~500m in lat
    half_lng = 0.00714  # ~500m in lng at lat 51
    center_lat, center_lng = 51.0, -114.0
    return [
        FireVertex(lat=center_lat + half_lat, lng=center_lng - half_lng),
        FireVertex(lat=center_lat + half_lat, lng=center_lng + half_lng),
        FireVertex(lat=center_lat - half_lat, lng=center_lng + half_lng),
        FireVertex(lat=center_lat - half_lat, lng=center_lng - half_lng),
    ]


@pytest.fixture
def triangle_vertices():
    """A simple triangle."""
    return [
        FireVertex(lat=51.0, lng=-114.0),
        FireVertex(lat=51.01, lng=-114.0),
        FireVertex(lat=51.005, lng=-113.99),
    ]


@pytest.fixture
def circle_vertices():
    """A circle of ~200m radius at lat 51."""
    center_lat, center_lng = 51.0, -114.0
    radius_m = 200.0
    m_per_deg_lat = 111320.0
    m_per_deg_lng = 111320.0 * math.cos(math.radians(center_lat))
    vertices = []
    for i in range(36):
        angle = 2.0 * math.pi * i / 36
        dlat = radius_m * math.cos(angle) / m_per_deg_lat
        dlng = radius_m * math.sin(angle) / m_per_deg_lng
        vertices.append(
            FireVertex(lat=center_lat + dlat, lng=center_lng + dlng)
        )
    return vertices


class TestVerticesToPolygon:
    """Test conversion of vertices to closed polygon."""

    def test_closes_polygon(self, square_vertices):
        """Output polygon should be closed (first == last)."""
        poly = vertices_to_polygon(square_vertices)
        assert poly[0] == poly[-1]

    def test_already_closed_not_doubled(self):
        """If vertices already form a closed ring, don't add extra point."""
        v = [
            FireVertex(lat=51.0, lng=-114.0),
            FireVertex(lat=51.01, lng=-114.0),
            FireVertex(lat=51.0, lng=-113.99),
            FireVertex(lat=51.0, lng=-114.0),
        ]
        poly = vertices_to_polygon(v)
        assert len(poly) == 4  # 3 unique + 1 closing

    def test_empty_returns_empty(self):
        assert vertices_to_polygon([]) == []

    def test_output_is_lat_lng_tuples(self, square_vertices):
        poly = vertices_to_polygon(square_vertices)
        for point in poly:
            assert isinstance(point, tuple)
            assert len(point) == 2


class TestCalculatePolygonAreaHa:
    """Test polygon area calculation."""

    def test_square_area_approximately_correct(self, square_vertices):
        """A ~1km x 1km square should be ~100 ha."""
        area = calculate_polygon_area_ha(square_vertices)
        # 1km^2 = 100 ha. Our square is approximate, so allow 20% tolerance
        assert 80.0 < area < 120.0

    def test_triangle_positive_area(self, triangle_vertices):
        area = calculate_polygon_area_ha(triangle_vertices)
        assert area > 0.0

    def test_circle_area_pi_r_squared(self, circle_vertices):
        """Circle of 200m radius: area = pi * 200^2 = ~125664 m2 = ~12.57 ha."""
        area = calculate_polygon_area_ha(circle_vertices)
        expected = math.pi * 200.0**2 / 10000.0  # ~12.57 ha
        # Allow 10% tolerance (polygon approximation of circle)
        assert abs(area - expected) / expected < 0.10

    def test_fewer_than_three_returns_zero(self):
        assert calculate_polygon_area_ha([]) == 0.0
        assert calculate_polygon_area_ha([FireVertex(51.0, -114.0)]) == 0.0
        assert (
            calculate_polygon_area_ha(
                [FireVertex(51.0, -114.0), FireVertex(51.01, -114.0)]
            )
            == 0.0
        )

    def test_area_independent_of_vertex_order(self, square_vertices):
        """Area should be the same regardless of CW/CCW ordering."""
        area_cw = calculate_polygon_area_ha(square_vertices)
        area_ccw = calculate_polygon_area_ha(list(reversed(square_vertices)))
        assert abs(area_cw - area_ccw) < 0.01


class TestPolygonToGeoJSON:
    """Test GeoJSON export."""

    def test_geojson_structure(self, square_vertices):
        geojson = polygon_to_geojson(square_vertices)
        assert geojson["type"] == "Feature"
        assert geojson["geometry"]["type"] == "Polygon"
        assert "coordinates" in geojson["geometry"]
        assert "properties" in geojson

    def test_geojson_coordinates_lng_lat_order(self, square_vertices):
        """GeoJSON coordinates should be [lng, lat] per spec."""
        geojson = polygon_to_geojson(square_vertices)
        coords = geojson["geometry"]["coordinates"][0]
        # First vertex is (lat=51.0045, lng~-114.007)
        first = coords[0]
        assert first[0] < 0  # longitude is negative (western hemisphere)
        assert first[1] > 50  # latitude is positive (~51)

    def test_geojson_closed_ring(self, square_vertices):
        geojson = polygon_to_geojson(square_vertices)
        coords = geojson["geometry"]["coordinates"][0]
        assert coords[0] == coords[-1]

    def test_geojson_with_properties(self, square_vertices):
        props = {"time_hours": 1.5, "area_ha": 100.0}
        geojson = polygon_to_geojson(square_vertices, properties=props)
        assert geojson["properties"]["time_hours"] == 1.5

    def test_geojson_empty_vertices(self):
        geojson = polygon_to_geojson([])
        assert geojson["geometry"]["coordinates"] == []


class TestCalculateCentroid:
    """Test centroid calculation."""

    def test_square_centroid(self, square_vertices):
        lat, lng = calculate_centroid(square_vertices)
        assert abs(lat - 51.0) < 0.001
        assert abs(lng - (-114.0)) < 0.001

    def test_empty_returns_origin(self):
        lat, lng = calculate_centroid([])
        assert lat == 0.0
        assert lng == 0.0

    def test_single_point(self):
        lat, lng = calculate_centroid([FireVertex(lat=51.5, lng=-114.5)])
        assert lat == 51.5
        assert lng == -114.5
