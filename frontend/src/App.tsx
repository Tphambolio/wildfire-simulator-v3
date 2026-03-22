/** FireSim V3 — Canadian FBP Wildfire Spread Simulator */

import { useCallback, useState } from "react";
import MapView from "./components/MapView";
import WeatherPanel from "./components/WeatherPanel";
import FireMetrics from "./components/FireMetrics";
import TimeSlider from "./components/TimeSlider";
import { useSimulation } from "./hooks/useSimulation";
import type { SimulationCreate } from "./types/simulation";

export default function App() {
  const [ignitionPoint, setIgnitionPoint] = useState<{
    lat: number;
    lng: number;
  } | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const {
    status,
    frames,
    currentFrameIndex,
    currentFrame,
    isRunning,
    isPaused,
    startSimulation,
    setFrameIndex,
    pauseSimulation,
    resumeSimulation,
    cancelSimulation,
    error,
  } = useSimulation();

  const handleMapClick = useCallback((lat: number, lng: number) => {
    setIgnitionPoint({ lat, lng });
  }, []);

  const handleStartSimulation = useCallback(
    (params: SimulationCreate) => {
      startSimulation(params);
    },
    [startSimulation]
  );

  return (
    <div className="app">
      <header className="app-header">
        <h1>FireSim V3</h1>
        <span className="subtitle">Canadian FBP Wildfire Spread Simulator</span>
        <button
          className="sidebar-toggle"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? "\u2715" : "\u2630"}
        </button>
        {isRunning && !isPaused && (
          <button className="btn-control btn-pause" onClick={pauseSimulation} title="Pause simulation">
            &#9646;&#9646; Pause
          </button>
        )}
        {isPaused && (
          <>
            <button className="btn-control btn-resume" onClick={resumeSimulation} title="Resume simulation">
              &#9654; Resume
            </button>
            <button className="btn-control btn-cancel" onClick={cancelSimulation} title="Cancel simulation">
              &#9632; Cancel
            </button>
          </>
        )}
        {status && (
          <span className={`status-badge status-${status}`}>
            {status}
          </span>
        )}
      </header>

      <div className="app-content">
        <aside className={`sidebar${sidebarOpen ? "" : " collapsed"}`}>
          <WeatherPanel
            onStartSimulation={handleStartSimulation}
            ignitionPoint={ignitionPoint}
            isRunning={isRunning}
          />
          <FireMetrics
            frame={currentFrame}
            status={status}
            totalFrames={frames.length}
          />
        </aside>

        <main className="map-area">
          <MapView
            frames={frames}
            currentFrameIndex={currentFrameIndex}
            onMapClick={handleMapClick}
            ignitionPoint={ignitionPoint}
          />
          <TimeSlider
            frames={frames}
            currentIndex={currentFrameIndex}
            onIndexChange={setFrameIndex}
          />
        </main>
      </div>

      {error && (
        <div className="error-toast">
          {error}
        </div>
      )}
    </div>
  );
}
