/**
 * Evacuation trigger zone utilities.
 *
 * Derives ICS-style evacuation zones from simulation frame perimeters:
 *   Order  (red)    — 0–2 h spread perimeter
 *   Alert  (orange) — 2–6 h spread perimeter
 *   Watch  (yellow) — 6–12 h spread perimeter
 *
 * All perimeter coords are [[lat, lng], ...] (engine convention).
 * GeoJSON coords are [lng, lat].
 */

import type { SimulationFrame } from "../types/simulation";

export type EvacZoneLabel = "Order" | "Alert" | "Watch";

export interface EvacZone {
  label: EvacZoneLabel;
  /** Display colour (CSS) */
  color: string;
  timeRangeLabel: string;
  /** Perimeter in engine [[lat, lng]] format */
  perimeter: number[][];
  areaHa: number;
  /** Community features that fall inside this zone */
  communitiesAtRisk: string[];
  /** Scale factor applied by the operator (1.0 = no change) */
  scale: number;
}

const ZONE_DEFS: Array<{
  label: EvacZoneLabel;
  targetHours: number;
  color: string;
  timeRangeLabel: string;
}> = [
  { label: "Order", targetHours: 2,  color: "#d32f2f", timeRangeLabel: "0–2 h" },
  { label: "Alert", targetHours: 6,  color: "#f57c00", timeRangeLabel: "2–6 h" },
  { label: "Watch", targetHours: 12, color: "#f9a825", timeRangeLabel: "6–12 h" },
];

/** Pick the frame whose time_hours is closest to target, with at least 3 perimeter points. */
function closestFrame(frames: SimulationFrame[], targetHours: number): SimulationFrame | null {
  let best: SimulationFrame | null = null;
  let bestDist = Infinity;
  for (const f of frames) {
    if (f.perimeter.length < 3) continue;
    const d = Math.abs(f.time_hours - targetHours);
    if (d < bestDist) { bestDist = d; best = f; }
  }
  return best;
}

/**
 * Scale a polygon outward or inward around its centroid.
 * factor > 1 expands, factor < 1 contracts.
 */
function scalePolygon(perimeter: number[][], factor: number): number[][] {
  if (factor === 1 || perimeter.length === 0) return perimeter;
  // Centroid (lat/lng)
  let sumLat = 0, sumLng = 0;
  for (const [lat, lng] of perimeter) { sumLat += lat; sumLng += lng; }
  const cLat = sumLat / perimeter.length;
  const cLng = sumLng / perimeter.length;
  return perimeter.map(([lat, lng]) => [
    cLat + (lat - cLat) * factor,
    cLng + (lng - cLng) * factor,
  ]);
}

// ── Point-in-polygon (ray casting, WGS84 approximation) ─────────────────────

function pointInPolygon(latPt: number, lngPt: number, ring: number[][]): boolean {
  let inside = false;
  const n = ring.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const [latI, lngI] = ring[i];
    const [latJ, lngJ] = ring[j];
    const cross =
      lngI > lngPt !== lngJ > lngPt &&
      latPt < ((latJ - latI) * (lngPt - lngI)) / (lngJ - lngI) + latI;
    if (cross) inside = !inside;
  }
  return inside;
}

/** Extract a representative lat/lng from a GeoJSON geometry (centroid approximation). */
function geometryCentroid(g: GeoJSON.Geometry): [number, number] | null {
  if (g.type === "Point") {
    return [g.coordinates[1], g.coordinates[0]];
  }
  if (g.type === "MultiPoint") {
    const [lng, lat] = g.coordinates[0];
    return [lat, lng];
  }
  if (g.type === "Polygon" && g.coordinates[0].length > 0) {
    let sLat = 0, sLng = 0;
    const ring = g.coordinates[0];
    for (const [lng, lat] of ring) { sLat += lat; sLng += lng; }
    return [sLat / ring.length, sLng / ring.length];
  }
  if (g.type === "MultiPolygon" && g.coordinates[0]?.[0]?.length) {
    const [lng, lat] = g.coordinates[0][0][0];
    return [lat, lng];
  }
  if (g.type === "LineString" && g.coordinates.length > 0) {
    const mid = g.coordinates[Math.floor(g.coordinates.length / 2)];
    return [mid[1], mid[0]];
  }
  return null;
}

/** Feature name from common GeoJSON property conventions. */
function featureName(f: GeoJSON.Feature): string {
  const p = f.properties as Record<string, unknown> | null;
  if (!p) return "Community";
  return String(p.name ?? p.NAME ?? p.label ?? p.community ?? "Community");
}

/**
 * Compute the communities that fall within a zone perimeter (engine [[lat,lng]] coords).
 */
function communitiesInZone(
  perimeter: number[][],
  communities: GeoJSON.FeatureCollection | null | undefined,
): string[] {
  if (!communities || perimeter.length < 3) return [];
  const names: string[] = [];
  for (const feat of communities.features) {
    const c = geometryCentroid(feat.geometry);
    if (!c) continue;
    if (pointInPolygon(c[0], c[1], perimeter)) {
      names.push(featureName(feat));
    }
  }
  return names;
}

// ── Polygon area via shoelace (approximate, degrees²→ ha) ───────────────────

function polygonAreaHa(perimeter: number[][]): number {
  if (perimeter.length < 3) return 0;
  // Convert to approximate metres using mid-latitude scaling
  const latScale = 111320; // m per degree latitude
  const midLat = perimeter.reduce((s, [lat]) => s + lat, 0) / perimeter.length;
  const lngScale = 111320 * Math.cos((midLat * Math.PI) / 180);
  let area = 0;
  const n = perimeter.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    area += (perimeter[j][1] * lngScale) * (perimeter[i][0] * latScale);
    area -= (perimeter[i][1] * lngScale) * (perimeter[j][0] * latScale);
  }
  return Math.abs(area) / 2 / 10_000; // m² → ha
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Derive evacuation zones from simulation frames.
 *
 * Returns up to 3 zones; a zone is omitted if no frame is close enough
 * to its target time bucket (must be within the simulation duration).
 */
export function computeEvacZones(
  frames: SimulationFrame[],
  communities: GeoJSON.FeatureCollection | null | undefined,
  scales: Record<EvacZoneLabel, number> = { Order: 1, Alert: 1, Watch: 1 },
): EvacZone[] {
  if (frames.length === 0) return [];

  const maxHours = frames[frames.length - 1].time_hours;
  const zones: EvacZone[] = [];

  for (const def of ZONE_DEFS) {
    if (def.targetHours > maxHours + 1) continue; // beyond simulation range
    const frame = closestFrame(frames, def.targetHours);
    if (!frame) continue;

    const scale = scales[def.label] ?? 1;
    const scaled = scalePolygon(frame.perimeter, scale);
    zones.push({
      label: def.label,
      color: def.color,
      timeRangeLabel: def.timeRangeLabel,
      perimeter: scaled,
      areaHa: polygonAreaHa(scaled),
      communitiesAtRisk: communitiesInZone(scaled, communities),
      scale,
    });
  }

  return zones;
}

/**
 * Convert evac zones to a GeoJSON FeatureCollection
 * (for export and map rendering). Coords in [lng, lat] order.
 */
export function evacZonesToGeoJSON(zones: EvacZone[]): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = zones.map((z) => {
    const coords = z.perimeter.map(([lat, lng]) => [lng, lat]);
    if (
      coords.length > 1 &&
      (coords[0][0] !== coords[coords.length - 1][0] ||
        coords[0][1] !== coords[coords.length - 1][1])
    ) {
      coords.push(coords[0]);
    }
    return {
      type: "Feature" as const,
      properties: {
        zone_label: z.label,
        zone_color: z.color,
        time_range: z.timeRangeLabel,
        area_ha: +z.areaHa.toFixed(1),
        communities_at_risk: z.communitiesAtRisk.join(", "),
        communities_count: z.communitiesAtRisk.length,
        scale_applied: z.scale,
      },
      geometry: {
        type: "Polygon" as const,
        coordinates: [coords],
      },
    };
  });
  return { type: "FeatureCollection", features };
}
