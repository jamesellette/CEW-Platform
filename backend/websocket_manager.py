"""
WebSocket module for real-time lab monitoring in CEW Training Platform.
Provides live updates for lab status, container health, and resource usage.
"""
import asyncio
import json
import logging
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        # Map of lab_id -> list of WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}
        # Map of connection -> lab_id for cleanup
        self._connection_labs: dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, lab_id: str) -> None:
        """Accept a WebSocket connection for a specific lab."""
        await websocket.accept()
        async with self._lock:
            if lab_id not in self._connections:
                self._connections[lab_id] = []
            self._connections[lab_id].append(websocket)
            self._connection_labs[websocket] = lab_id
        logger.info(f"WebSocket connected for lab {lab_id}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            lab_id = self._connection_labs.pop(websocket, None)
            if lab_id and lab_id in self._connections:
                if websocket in self._connections[lab_id]:
                    self._connections[lab_id].remove(websocket)
                # Clean up empty lab entries
                if not self._connections[lab_id]:
                    del self._connections[lab_id]
        logger.info(f"WebSocket disconnected for lab {lab_id}")

    async def broadcast_to_lab(self, lab_id: str, message: dict) -> None:
        """Broadcast a message to all connections watching a specific lab."""
        async with self._lock:
            connections = self._connections.get(lab_id, []).copy()

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                await self.disconnect(connection)

    async def broadcast_all(self, message: dict) -> None:
        """Broadcast a message to all connections."""
        async with self._lock:
            all_connections = [
                conn for conns in self._connections.values() for conn in conns
            ]

        for connection in all_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                await self.disconnect(connection)

    def get_connected_labs(self) -> list[str]:
        """Get list of lab IDs with active connections."""
        return list(self._connections.keys())

    def get_connection_count(self, lab_id: Optional[str] = None) -> int:
        """Get the number of active connections."""
        if lab_id:
            return len(self._connections.get(lab_id, []))
        return sum(len(conns) for conns in self._connections.values())


class LabMonitor:
    """
    Background task for monitoring labs and broadcasting updates.
    Sends periodic updates about container health and resource usage.
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        update_interval: float = 5.0
    ):
        self.connection_manager = connection_manager
        self.update_interval = update_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the monitoring background task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Lab monitor started")

    async def stop(self) -> None:
        """Stop the monitoring background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Lab monitor stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop that sends periodic updates."""
        # Import here to avoid circular imports
        from orchestrator import orchestrator

        while self._running:
            try:
                # Get labs with active connections
                connected_labs = self.connection_manager.get_connected_labs()

                for lab_id in connected_labs:
                    lab = orchestrator.get_lab(lab_id)
                    if not lab:
                        continue

                    # Build update message
                    update = {
                        "type": "lab_update",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "lab_id": lab_id,
                        "status": lab.status.value,
                        "containers": []
                    }

                    # Get health and resource info for each container
                    try:
                        health = await orchestrator.get_container_health(lab_id)
                        resources = orchestrator.get_resource_usage(lab_id)

                        for container in lab.containers:
                            container_info = {
                                "hostname": container.hostname,
                                "status": container.status,
                                "health": health.get(container.hostname, {}),
                                "resources": resources.get(container.hostname, {})
                            }
                            update["containers"].append(container_info)

                    except Exception as e:
                        logger.error(f"Error getting lab {lab_id} metrics: {e}")

                    # Broadcast update
                    await self.connection_manager.broadcast_to_lab(lab_id, update)

                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.update_interval)


# Global instances
connection_manager = ConnectionManager()
lab_monitor = LabMonitor(connection_manager)


async def handle_lab_websocket(
    websocket: WebSocket,
    lab_id: str,
    username: str
) -> None:
    """
    Handle a WebSocket connection for lab monitoring.

    Args:
        websocket: The WebSocket connection
        lab_id: The lab ID to monitor
        username: The authenticated username
    """
    from orchestrator import orchestrator

    # Verify lab exists
    lab = orchestrator.get_lab(lab_id)
    if not lab:
        await websocket.close(code=4004, reason="Lab not found")
        return

    await connection_manager.connect(websocket, lab_id)

    try:
        # Send initial state
        health = await orchestrator.get_container_health(lab_id)
        resources = orchestrator.get_resource_usage(lab_id)

        initial_state = {
            "type": "initial_state",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lab_id": lab_id,
            "lab_status": lab.status.value,
            "scenario_name": lab.scenario_name,
            "docker_mode": lab.docker_mode,
            "containers": [
                {
                    "container_id": c.container_id,
                    "hostname": c.hostname,
                    "image": c.image,
                    "ip_address": c.ip_address,
                    "status": c.status,
                    "health": health.get(c.hostname, {}),
                    "resources": resources.get(c.hostname, {})
                }
                for c in lab.containers
            ],
            "networks": [
                {
                    "network_id": n.network_id,
                    "name": n.name,
                    "subnet": n.subnet,
                    "isolated": n.isolated
                }
                for n in lab.networks
            ]
        }
        await websocket.send_json(initial_state)

        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (ping/pong or commands)
                # 15 second timeout for better responsiveness
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=15.0
                )
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from lab {lab_id}")
    except Exception as e:
        logger.error(f"WebSocket error for lab {lab_id}: {e}")
    finally:
        await connection_manager.disconnect(websocket)
