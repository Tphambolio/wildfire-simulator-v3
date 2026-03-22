"""Simulation REST endpoints."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from firesim_api.schemas.simulation import (
    SimulationCreate,
    SimulationFrame as FrameSchema,
    SimulationResponse,
    SimulationStatus,
)
from firesim_api.services.runner import SimulationRunner
from firesim_api.ws.manager import ConnectionManager
from firesim.types import SimulationFrame

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/simulations", tags=["simulations"])

# Shared state — injected from main app
runner: SimulationRunner | None = None
ws_manager: ConnectionManager | None = None


def _frame_to_schema(frame: SimulationFrame) -> FrameSchema:
    """Convert engine SimulationFrame to API schema."""
    return FrameSchema(
        time_hours=frame.time_hours,
        perimeter=[[lat, lng] for lat, lng in frame.perimeter],
        area_ha=round(frame.area_ha, 2),
        head_ros_m_min=round(frame.head_ros_m_min, 2),
        max_hfi_kw_m=round(frame.max_hfi_kw_m, 1),
        fire_type=frame.fire_type.value,
        flame_length_m=round(frame.flame_length_m, 2),
        fuel_breakdown=frame.fuel_breakdown,
        spot_fires=frame.spot_fires,
        num_fronts=frame.num_fronts,
        burned_cells=frame.burned_cells,
    )


def _on_frame(sim_id: str, frame: SimulationFrame) -> None:
    """Callback from simulation thread — broadcast frame via WebSocket."""
    if ws_manager is None:
        return
    event = {
        "type": "simulation.frame",
        "simulation_id": sim_id,
        "frame": _frame_to_schema(frame).model_dump(),
    }
    ws_manager.broadcast_from_thread(sim_id, event)


@router.post("", response_model=SimulationResponse)
async def create_simulation(params: SimulationCreate) -> SimulationResponse:
    """Start a new fire spread simulation."""
    if runner is None:
        raise HTTPException(status_code=500, detail="Runner not initialized")

    sim_id = runner.create(params, on_frame=_on_frame)

    return SimulationResponse(
        simulation_id=sim_id,
        status=SimulationStatus.RUNNING,
        config=params,
    )


@router.get("/{sim_id}", response_model=SimulationResponse)
async def get_simulation(sim_id: str) -> SimulationResponse:
    """Get simulation status and results."""
    if runner is None:
        raise HTTPException(status_code=500, detail="Runner not initialized")

    run = runner.get(sim_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    frames = [_frame_to_schema(f) for f in run.get_frames()]

    return SimulationResponse(
        simulation_id=run.id,
        status=run.status,
        config=run.config,
        frames=frames,
        error=run.error,
    )


@router.websocket("/ws/{sim_id}")
async def simulation_websocket(websocket: WebSocket, sim_id: str) -> None:
    """WebSocket endpoint for streaming simulation frames."""
    if ws_manager is None or runner is None:
        await websocket.close(code=1011)
        return

    run = runner.get(sim_id)
    if run is None:
        await websocket.close(code=4004, reason="Simulation not found")
        return

    await ws_manager.connect(sim_id, websocket)

    try:
        # Send any frames that already exist
        for frame in run.get_frames():
            await websocket.send_json({
                "type": "simulation.frame",
                "simulation_id": sim_id,
                "frame": _frame_to_schema(frame).model_dump(),
            })

        # If already done, send completion
        if run.status == SimulationStatus.COMPLETED:
            await websocket.send_json({
                "type": "simulation.completed",
                "simulation_id": sim_id,
            })
        elif run.status == SimulationStatus.FAILED:
            await websocket.send_json({
                "type": "simulation.error",
                "simulation_id": sim_id,
                "error": run.error,
            })

        # Keep connection alive; process control messages and wait for terminal state
        while run.status in (SimulationStatus.RUNNING, SimulationStatus.PAUSED):
            try:
                msg_text = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                try:
                    msg = json.loads(msg_text)
                    action = msg.get("action")
                    if action == "pause":
                        run.pause()
                        await websocket.send_json({"type": "status", "state": "paused"})
                    elif action == "resume":
                        run.resume()
                        await websocket.send_json({"type": "status", "state": "running"})
                    elif action == "cancel":
                        run.cancel()
                        await websocket.send_json({"type": "status", "state": "cancelled"})
                except (json.JSONDecodeError, AttributeError):
                    pass
            except asyncio.TimeoutError:
                continue

        # Send final event based on terminal state
        if run.status == SimulationStatus.COMPLETED:
            await websocket.send_json({
                "type": "simulation.completed",
                "simulation_id": sim_id,
            })
        elif run.status == SimulationStatus.CANCELLED:
            # Status already sent on cancel action; send final frame if available
            frames = run.get_frames()
            if frames:
                await websocket.send_json({
                    "type": "simulation.frame",
                    "simulation_id": sim_id,
                    "frame": _frame_to_schema(frames[-1]).model_dump(),
                })

    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(sim_id, websocket)
