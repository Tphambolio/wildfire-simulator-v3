/** MapLibre GL map with fire perimeter rendering.
 *
 * Uses MapLibre GL (open-source, no token required) with
 * OpenStreetMap raster tiles by default, or Mapbox satellite
 * when VITE_MAPBOX_TOKEN is set.
 */

import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import type { SimulationFrame } from "../types/simulation";

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || "";

function getMapStyle(): maplibregl.StyleSpecification {
  if (MAPBOX_TOKEN) {
    return {
      version: 8,
      name: "Satellite",
      sources: {
        mapbox: {
          type: "raster",
          tiles: [
            `https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v12/tiles/{z}/{x}/{y}?access_token=${MAPBOX_TOKEN}`,
          ],
          tileSize: 512,
          attribution: "&copy; Mapbox &copy; OpenStreetMap",
        },
      },
      layers: [{ id: "mapbox-tiles", type: "raster", source: "mapbox" }],
    };
  }
  return {
    version: 8,
    name: "OSM",
    sources: {
      osm: {
        type: "raster",
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
        tileSize: 256,
        attribution: "&copy; OpenStreetMap contributors",
      },
    },
    layers: [
      { id: "osm-tiles", type: "raster", source: "osm", minzoom: 0, maxzoom: 19 },
    ],
  };
}

interface MapViewProps {
  frames: SimulationFrame[];
  currentFrameIndex: number;
  onMapClick: (lat: number, lng: number) => void;
  ignitionPoint: { lat: number; lng: number } | null;
}

export default function MapView({
  frames,
  currentFrameIndex,
  onMapClick,
  ignitionPoint,
}: MapViewProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const [mapReady, setMapReady] = useState(false);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const m = new maplibregl.Map({
      container: mapContainer.current,
      style: getMapStyle(),
      center: [-114.0, 51.0],
      zoom: 10,
    });

    m.addControl(new maplibregl.NavigationControl(), "top-right");

    m.on("load", () => {
      m.addSource("fire-perimeter", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      m.addLayer({
        id: "fire-fill",
        type: "fill",
        source: "fire-perimeter",
        paint: {
          "fill-color": [
            "interpolate",
            ["linear"],
            ["get", "hfi"],
            0, "#ffeb3b",
            2000, "#ff9800",
            4000, "#f44336",
            10000, "#b71c1c",
          ],
          "fill-opacity": 0.4,
        },
      });

      m.addLayer({
        id: "fire-outline",
        type: "line",
        source: "fire-perimeter",
        paint: {
          "line-color": "#ff3d00",
          "line-width": 2.5,
        },
      });

      m.addSource("fire-history", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      m.addLayer(
        {
          id: "fire-history-outline",
          type: "line",
          source: "fire-history",
          paint: {
            "line-color": "#ff9800",
            "line-width": 1,
            "line-opacity": 0.5,
            "line-dasharray": [2, 2],
          },
        },
        "fire-fill"
      );

      setMapReady(true);
    });

    m.on("click", (e) => {
      onMapClick(e.lngLat.lat, e.lngLat.lng);
    });

    map.current = m;

    return () => {
      m.remove();
      map.current = null;
    };
  }, []);

  // Update ignition marker
  useEffect(() => {
    if (!map.current) return;

    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }

    if (ignitionPoint) {
      const el = document.createElement("div");
      el.className = "ignition-marker";
      el.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" fill="#ff3d00" stroke="white" stroke-width="2"/>
        <text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-weight="bold">&#x1F525;</text>
      </svg>`;

      markerRef.current = new maplibregl.Marker({ element: el })
        .setLngLat([ignitionPoint.lng, ignitionPoint.lat])
        .addTo(map.current);

      map.current.flyTo({
        center: [ignitionPoint.lng, ignitionPoint.lat],
        zoom: 11,
        duration: 1000,
      });
    }
  }, [ignitionPoint]);

  // Update fire perimeter on map
  useEffect(() => {
    if (!map.current || !mapReady || frames.length === 0) return;

    const currentFrame = frames[currentFrameIndex];
    if (!currentFrame || currentFrame.perimeter.length < 3) return;

    const coords = currentFrame.perimeter.map(([lat, lng]) => [lng, lat]);
    if (
      coords.length > 1 &&
      (coords[0][0] !== coords[coords.length - 1][0] ||
        coords[0][1] !== coords[coords.length - 1][1])
    ) {
      coords.push(coords[0]);
    }

    const currentGeoJSON: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "Polygon", coordinates: [coords] },
          properties: {
            time_hours: currentFrame.time_hours,
            area_ha: currentFrame.area_ha,
            hfi: currentFrame.max_hfi_kw_m,
          },
        },
      ],
    };

    (map.current.getSource("fire-perimeter") as maplibregl.GeoJSONSource)?.setData(
      currentGeoJSON
    );

    const historyFeatures: GeoJSON.Feature[] = frames
      .slice(1, currentFrameIndex)
      .filter((f) => f.perimeter.length >= 3)
      .map((f) => {
        const c = f.perimeter.map(([lat, lng]) => [lng, lat]);
        if (c.length > 1 && (c[0][0] !== c[c.length - 1][0] || c[0][1] !== c[c.length - 1][1])) {
          c.push(c[0]);
        }
        return {
          type: "Feature" as const,
          geometry: { type: "Polygon" as const, coordinates: [c] },
          properties: { time_hours: f.time_hours },
        };
      });

    (map.current.getSource("fire-history") as maplibregl.GeoJSONSource)?.setData({
      type: "FeatureCollection",
      features: historyFeatures,
    });
  }, [frames, currentFrameIndex, mapReady]);

  return (
    <div ref={mapContainer} style={{ width: "100%", height: "100%" }} />
  );
}
