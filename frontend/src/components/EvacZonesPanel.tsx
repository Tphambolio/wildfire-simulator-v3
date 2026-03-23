/**
 * Evacuation Trigger Zones panel.
 *
 * Displays ICS-style evac zone statistics and allows operators to:
 *  - Toggle zone overlay visibility
 *  - Adjust zone boundary scale (0.5× – 2.0×) for manual refinement
 */

import type { EvacZone, EvacZoneLabel } from "../utils/evacZones";

interface EvacZonesPanelProps {
  zones: EvacZone[];
  visible: boolean;
  scales: Record<EvacZoneLabel, number>;
  onToggleVisible: (v: boolean) => void;
  onScaleChange: (label: EvacZoneLabel, scale: number) => void;
}

const ZONE_ORDER: EvacZoneLabel[] = ["Order", "Alert", "Watch"];

const ZONE_BG: Record<EvacZoneLabel, string> = {
  Order: "rgba(211,47,47,0.15)",
  Alert: "rgba(245,124,0,0.15)",
  Watch: "rgba(249,168,37,0.12)",
};

const ZONE_BORDER: Record<EvacZoneLabel, string> = {
  Order: "#d32f2f",
  Alert: "#f57c00",
  Watch: "#f9a825",
};

export default function EvacZonesPanel({
  zones,
  visible,
  scales,
  onToggleVisible,
  onScaleChange,
}: EvacZonesPanelProps) {
  if (zones.length === 0) return null;

  return (
    <div className="panel evac-panel">
      <div className="evac-header">
        <h3>Evacuation Zones</h3>
        <button
          className={`ov-vis-btn ${visible ? "on" : "off"}`}
          onClick={() => onToggleVisible(!visible)}
          title={visible ? "Hide zones" : "Show zones"}
        >
          {visible ? "ON" : "OFF"}
        </button>
      </div>

      {ZONE_ORDER.filter((l) => zones.some((z) => z.label === l)).map((label) => {
        const zone = zones.find((z) => z.label === label)!;
        const scale = scales[label];
        return (
          <div
            key={label}
            className="evac-zone-card"
            style={{
              background: ZONE_BG[label],
              borderLeft: `4px solid ${ZONE_BORDER[label]}`,
            }}
          >
            <div className="evac-zone-title">
              <span
                className="evac-zone-dot"
                style={{ background: zone.color }}
              />
              <strong>{label}</strong>
              <span className="evac-zone-time">{zone.timeRangeLabel}</span>
            </div>

            <div className="evac-zone-stats">
              <span>{zone.areaHa.toFixed(0)} ha</span>
              {zone.communitiesAtRisk.length > 0 && (
                <span className="evac-zone-pop" title={zone.communitiesAtRisk.join(", ")}>
                  {zone.communitiesAtRisk.length} communit{zone.communitiesAtRisk.length === 1 ? "y" : "ies"}
                </span>
              )}
            </div>

            {zone.communitiesAtRisk.length > 0 && (
              <div className="evac-zone-communities">
                {zone.communitiesAtRisk.slice(0, 4).join(", ")}
                {zone.communitiesAtRisk.length > 4 && ` +${zone.communitiesAtRisk.length - 4} more`}
              </div>
            )}

            <div className="evac-zone-scale-row">
              <span className="evac-scale-label">Boundary scale</span>
              <input
                type="range"
                min={0.5}
                max={2.0}
                step={0.05}
                value={scale}
                className="evac-scale-slider"
                onChange={(e) => onScaleChange(label, parseFloat(e.target.value))}
              />
              <span className="evac-scale-value">{scale.toFixed(2)}×</span>
              {scale !== 1 && (
                <button
                  className="evac-scale-reset"
                  onClick={() => onScaleChange(label, 1)}
                  title="Reset to model boundary"
                >
                  ↺
                </button>
              )}
            </div>
          </div>
        );
      })}

      <div className="evac-legend">
        <span style={{ color: "#d32f2f" }}>■</span> Evacuation Order &nbsp;
        <span style={{ color: "#f57c00" }}>■</span> Alert &nbsp;
        <span style={{ color: "#f9a825" }}>■</span> Watch
      </div>
    </div>
  );
}
