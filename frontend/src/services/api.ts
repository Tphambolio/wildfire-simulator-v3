/** API client for the FireSim backend. */

import type { SimulationCreate, SimulationResponse } from "../types/simulation";

const API_BASE = import.meta.env.VITE_API_URL || "";

export async function createSimulation(
  params: SimulationCreate
): Promise<SimulationResponse> {
  const resp = await fetch(`${API_BASE}/api/v1/simulations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Failed to create simulation");
  }
  return resp.json();
}

export async function getSimulation(
  simId: string
): Promise<SimulationResponse> {
  const resp = await fetch(`${API_BASE}/api/v1/simulations/${simId}`);
  if (!resp.ok) {
    throw new Error(`Simulation ${simId} not found`);
  }
  return resp.json();
}

export function getWebSocketUrl(simId: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = API_BASE || `${proto}//${window.location.host}`;
  const wsBase = host.replace(/^http/, "ws");
  return `${wsBase}/api/v1/simulations/ws/${simId}`;
}
