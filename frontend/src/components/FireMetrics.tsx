/** Fire metrics display panel showing current frame statistics. */

import type { SimulationFrame } from "../types/simulation";

interface FireMetricsProps {
  frame: SimulationFrame | null;
  status: string | null;
  totalFrames: number;
}

function classifyIntensity(hfi: number): { label: string; color: string } {
  if (hfi < 10) return { label: "Low", color: "#4caf50" };
  if (hfi < 500) return { label: "Moderate", color: "#ffeb3b" };
  if (hfi < 2000) return { label: "High", color: "#ff9800" };
  if (hfi < 4000) return { label: "Very High", color: "#f44336" };
  if (hfi < 10000) return { label: "Extreme", color: "#d32f2f" };
  return { label: "Ultra-Extreme", color: "#b71c1c" };
}

function formatFireType(ft: string): string {
  return ft
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function FireMetrics({ frame, status, totalFrames }: FireMetricsProps) {
  if (!frame) {
    return (
      <div className="panel metrics-panel">
        <h3>Fire Metrics</h3>
        <div className="hint">
          {status === "running" ? "Waiting for first frame..." : "Run a simulation to see metrics"}
        </div>
      </div>
    );
  }

  const intensity = classifyIntensity(frame.max_hfi_kw_m);

  return (
    <div className="panel metrics-panel">
      <h3>Fire Metrics</h3>

      <div className="metric-grid">
        <div className="metric">
          <span className="metric-label">Time</span>
          <span className="metric-value">{frame.time_hours.toFixed(1)}h</span>
        </div>

        <div className="metric">
          <span className="metric-label">Area</span>
          <span className="metric-value">{frame.area_ha.toFixed(1)} ha</span>
        </div>

        <div className="metric">
          <span className="metric-label">Head ROS</span>
          <span className="metric-value">{frame.head_ros_m_min.toFixed(1)} m/min</span>
        </div>

        <div className="metric">
          <span className="metric-label">HFI</span>
          <span className="metric-value" style={{ color: intensity.color }}>
            {frame.max_hfi_kw_m.toFixed(0)} kW/m
          </span>
        </div>

        <div className="metric">
          <span className="metric-label">Intensity</span>
          <span className="metric-value" style={{ color: intensity.color }}>
            {intensity.label}
          </span>
        </div>

        <div className="metric">
          <span className="metric-label">Fire Type</span>
          <span className="metric-value">{formatFireType(frame.fire_type)}</span>
        </div>

        <div className="metric">
          <span className="metric-label">Flame Length</span>
          <span className="metric-value">{frame.flame_length_m.toFixed(1)} m</span>
        </div>

        <div className="metric">
          <span className="metric-label">Frames</span>
          <span className="metric-value">{totalFrames}</span>
        </div>
      </div>

      {Object.keys(frame.fuel_breakdown).length > 0 && (
        <div className="fuel-breakdown">
          <h4>Fuel Mix</h4>
          {Object.entries(frame.fuel_breakdown).map(([fuel, pct]) => (
            <div key={fuel} className="fuel-bar">
              <span className="fuel-label">{fuel}</span>
              <div className="fuel-bar-track">
                <div
                  className="fuel-bar-fill"
                  style={{ width: `${pct * 100}%` }}
                />
              </div>
              <span className="fuel-pct">{(pct * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
