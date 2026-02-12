/** Time slider for scrubbing through simulation frames. */

import type { SimulationFrame } from "../types/simulation";

interface TimeSliderProps {
  frames: SimulationFrame[];
  currentIndex: number;
  onIndexChange: (index: number) => void;
}

export default function TimeSlider({
  frames,
  currentIndex,
  onIndexChange,
}: TimeSliderProps) {
  if (frames.length < 2) return null;

  const currentFrame = frames[currentIndex];

  return (
    <div className="time-slider">
      <span className="time-label">
        T = {currentFrame?.time_hours.toFixed(1) ?? "0"}h
      </span>
      <input
        type="range"
        min={0}
        max={frames.length - 1}
        value={currentIndex}
        onChange={(e) => onIndexChange(Number(e.target.value))}
      />
      <span className="time-label">
        {frames[frames.length - 1]?.time_hours.toFixed(1)}h
      </span>
    </div>
  );
}
