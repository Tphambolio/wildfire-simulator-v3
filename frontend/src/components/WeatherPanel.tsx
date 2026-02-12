/** Weather and simulation parameter controls. */

import { useState } from "react";
import type { SimulationCreate, WeatherParams, FWIOverrides } from "../types/simulation";
import { FUEL_TYPES } from "../types/simulation";

interface WeatherPanelProps {
  onStartSimulation: (params: SimulationCreate) => void;
  ignitionPoint: { lat: number; lng: number } | null;
  isRunning: boolean;
}

export default function WeatherPanel({
  onStartSimulation,
  ignitionPoint,
  isRunning,
}: WeatherPanelProps) {
  const [weather, setWeather] = useState<WeatherParams>({
    wind_speed: 20,
    wind_direction: 270,
    temperature: 25,
    relative_humidity: 30,
    precipitation_24h: 0,
  });
  const [fwi, setFwi] = useState<FWIOverrides>({
    ffmc: 90,
    dmc: 45,
    dc: 300,
  });
  const [fuelType, setFuelType] = useState("C2");
  const [durationHours, setDurationHours] = useState(4);
  const [snapshotMinutes, setSnapshotMinutes] = useState(30);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = () => {
    if (!ignitionPoint) return;
    onStartSimulation({
      ignition_lat: ignitionPoint.lat,
      ignition_lng: ignitionPoint.lng,
      weather,
      fwi_overrides: fwi,
      duration_hours: durationHours,
      snapshot_interval_minutes: snapshotMinutes,
      fuel_type: fuelType,
    });
  };

  // Wind direction compass label
  const windLabel = (deg: number) => {
    const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
    return dirs[Math.round(deg / 45) % 8];
  };

  return (
    <div className="panel weather-panel">
      <h3>Simulation Parameters</h3>

      {!ignitionPoint && (
        <div className="hint">Click the map to set ignition point</div>
      )}

      {ignitionPoint && (
        <div className="ignition-info">
          Ignition: {ignitionPoint.lat.toFixed(4)}, {ignitionPoint.lng.toFixed(4)}
        </div>
      )}

      <div className="section">
        <h4>Weather</h4>

        <label>
          Wind Speed: <strong>{weather.wind_speed} km/h</strong>
          <input
            type="range"
            min={0}
            max={80}
            value={weather.wind_speed}
            onChange={(e) =>
              setWeather({ ...weather, wind_speed: Number(e.target.value) })
            }
          />
        </label>

        <label>
          Wind Direction: <strong>{weather.wind_direction}° ({windLabel(weather.wind_direction)})</strong>
          <input
            type="range"
            min={0}
            max={359}
            value={weather.wind_direction}
            onChange={(e) =>
              setWeather({ ...weather, wind_direction: Number(e.target.value) })
            }
          />
        </label>

        <label>
          Temperature: <strong>{weather.temperature}°C</strong>
          <input
            type="range"
            min={-10}
            max={45}
            value={weather.temperature}
            onChange={(e) =>
              setWeather({ ...weather, temperature: Number(e.target.value) })
            }
          />
        </label>

        <label>
          Relative Humidity: <strong>{weather.relative_humidity}%</strong>
          <input
            type="range"
            min={5}
            max={100}
            value={weather.relative_humidity}
            onChange={(e) =>
              setWeather({
                ...weather,
                relative_humidity: Number(e.target.value),
              })
            }
          />
        </label>
      </div>

      <div className="section">
        <h4>Fuel Type</h4>
        <select
          value={fuelType}
          onChange={(e) => setFuelType(e.target.value)}
        >
          {Object.entries(FUEL_TYPES).map(([code, name]) => (
            <option key={code} value={code}>
              {code} — {name}
            </option>
          ))}
        </select>
      </div>

      <div className="section">
        <h4>Duration</h4>
        <label>
          Simulation: <strong>{durationHours}h</strong>
          <input
            type="range"
            min={1}
            max={24}
            value={durationHours}
            onChange={(e) => setDurationHours(Number(e.target.value))}
          />
        </label>
        <label>
          Snapshots every: <strong>{snapshotMinutes} min</strong>
          <input
            type="range"
            min={5}
            max={60}
            step={5}
            value={snapshotMinutes}
            onChange={(e) => setSnapshotMinutes(Number(e.target.value))}
          />
        </label>
      </div>

      <button
        className="toggle-advanced"
        onClick={() => setShowAdvanced(!showAdvanced)}
      >
        {showAdvanced ? "Hide" : "Show"} FWI Overrides
      </button>

      {showAdvanced && (
        <div className="section">
          <h4>FWI Components</h4>
          <label>
            FFMC: <strong>{fwi.ffmc}</strong>
            <input
              type="range"
              min={0}
              max={101}
              value={fwi.ffmc ?? 85}
              onChange={(e) =>
                setFwi({ ...fwi, ffmc: Number(e.target.value) })
              }
            />
          </label>
          <label>
            DMC: <strong>{fwi.dmc}</strong>
            <input
              type="range"
              min={0}
              max={200}
              value={fwi.dmc ?? 40}
              onChange={(e) =>
                setFwi({ ...fwi, dmc: Number(e.target.value) })
              }
            />
          </label>
          <label>
            DC: <strong>{fwi.dc}</strong>
            <input
              type="range"
              min={0}
              max={800}
              value={fwi.dc ?? 200}
              onChange={(e) =>
                setFwi({ ...fwi, dc: Number(e.target.value) })
              }
            />
          </label>
        </div>
      )}

      <button
        className="btn-primary"
        onClick={handleSubmit}
        disabled={!ignitionPoint || isRunning}
      >
        {isRunning ? "Simulating..." : "Run Simulation"}
      </button>
    </div>
  );
}
