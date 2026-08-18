import asyncio
import json
import logging
import uuid
import base64
import time
from typing import Dict, Any, Optional, List
import aiohttp
from aiohttp import web

logger = logging.getLogger("BridgeManager")

class DeviceSession:
    def __init__(self, ws: web.WebSocketResponse, hostname: str, os_name: str, ip: str):
        self.ws = ws
        self.hostname = hostname
        self.os_name = os_name
        self.ip = ip
        self.connected_at = time.time()
        self.last_active = time.time()

class BridgeManager:
    """Manages multi-device real-time WebSocket connections between Railway Cloud and Local PCs/Laptops."""
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        # Dictionary of hostname -> DeviceSession
        self.devices: Dict[str, DeviceSession] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}

    @property
    def is_connected(self) -> bool:
        """Returns True if at least one device is currently online."""
        return any(d.ws is not None and not d.ws.closed for d in self.devices.values())

    @property
    def primary_device(self) -> Optional[DeviceSession]:
        """Returns the most recently connected active device."""
        active = [d for d in self.devices.values() if d.ws and not d.ws.closed]
        if not active:
            return None
        return max(active, key=lambda d: d.last_active)

    @property
    def pc_info(self) -> Dict[str, Any]:
        """Returns info of the primary active device for backward compatibility."""
        p = self.primary_device
        if p:
            return {
                "hostname": p.hostname,
                "os": p.os_name,
                "connected_at": p.connected_at,
                "ip": p.ip,
                "total_online_devices": len(self.get_online_devices())
            }
        return {}

    def get_online_devices(self) -> List[Dict[str, Any]]:
        """List all currently connected and online devices."""
        result = []
        for host, dev in list(self.devices.items()):
            if dev.ws and not dev.ws.closed:
                result.append({
                    "hostname": dev.hostname,
                    "os": dev.os_name,
                    "ip": dev.ip,
                    "connected_at": dev.connected_at
                })
        return result

    async def handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=45.0, max_msg_size=50 * 1024 * 1024)
        await ws.prepare(request)

        authenticated = False
        peer_name = request.remote
        assigned_hostname = None

        logger.info(f"Incoming connection from {peer_name}")

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except Exception:
                        continue

                    msg_type = data.get("type")

                    # Handle Authentication
                    if msg_type == "auth":
                        provided_secret = data.get("secret", "").strip()
                        if self.secret_key and provided_secret != self.secret_key:
                            logger.warning(f"Failed authentication attempt from {peer_name}")
                            await ws.send_json({"type": "auth_fail", "reason": "Invalid BRIDGE_SECRET_KEY"})
                            await ws.close()
                            break
                        
                        authenticated = True
                        assigned_hostname = data.get("hostname", f"Device-{peer_name}")
                        os_name = data.get("os", "Windows")

                        # If an older socket exists for the same hostname, close it
                        if assigned_hostname in self.devices:
                            old_dev = self.devices[assigned_hostname]
                            if old_dev.ws and old_dev.ws != ws and not old_dev.ws.closed:
                                try:
                                    await old_dev.ws.close()
                                except Exception:
                                    pass

                        self.devices[assigned_hostname] = DeviceSession(ws, assigned_hostname, os_name, peer_name)
                        logger.info(f"✅ Device connected & authenticated: {assigned_hostname} ({peer_name}). Total devices online: {len(self.get_online_devices())}")
                        await ws.send_json({"type": "auth_ok", "message": f"Bridge connected successfully as '{assigned_hostname}'."})

                    # Handle RPC Tool Response from PC
                    elif msg_type == "tool_response":
                        if assigned_hostname in self.devices:
                            self.devices[assigned_hostname].last_active = time.time()

                        req_id = data.get("id")
                        if req_id and req_id in self.pending_requests:
                            fut = self.pending_requests.pop(req_id)
                            if not fut.done():
                                fut.set_result(data)

                    # Handle Ping
                    elif msg_type == "ping":
                        if assigned_hostname in self.devices:
                            self.devices[assigned_hostname].last_active = time.time()
                        await ws.send_json({"type": "pong"})

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error from {assigned_hostname or peer_name}: {ws.exception()}")

        finally:
            if assigned_hostname and assigned_hostname in self.devices:
                if self.devices[assigned_hostname].ws == ws:
                    del self.devices[assigned_hostname]
                    logger.info(f"⚠️ Device '{assigned_hostname}' disconnected. Remaining online: {len(self.get_online_devices())}")
                    
                    # Cancel pending requests for this device if needed
                    for req_id, fut in list(self.pending_requests.items()):
                        if not fut.done():
                            fut.set_exception(ConnectionResetError(f"Device '{assigned_hostname}' disconnected."))
                    self.pending_requests.clear()

        return ws

    async def execute_tool_on_pc(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        target_device: Optional[str] = None,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """Send a tool execution command over WebSocket to a specific or primary connected PC and await response."""
        # Wait up to 3 seconds in case a reconnect is in progress
        if not self.is_connected:
            for _ in range(6):
                await asyncio.sleep(0.5)
                if self.is_connected:
                    break

        if not self.is_connected:
            return {
                "status": "offline",
                "result": "Notice to Jarvis: All user workstations/laptops are currently offline or disconnected. Inform the user politely."
            }

        # Select target device
        target = None
        if target_device and target_device in self.devices:
            dev = self.devices[target_device]
            if dev.ws and not dev.ws.closed:
                target = dev

        if not target:
            target = self.primary_device

        if not target or not target.ws or target.ws.closed:
            return {
                "status": "offline",
                "result": "Notice to Jarvis: The target device is no longer reachable."
            }

        req_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.pending_requests[req_id] = fut

        payload = {
            "type": "execute_tool",
            "id": req_id,
            "tool_name": tool_name,
            "args": tool_args
        }

        try:
            target.last_active = time.time()
            await target.ws.send_json(payload)
            response = await asyncio.wait_for(fut, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            self.pending_requests.pop(req_id, None)
            return {
                "status": "error",
                "result": f"Error: Command '{tool_name}' timed out on device '{target.hostname}' after {timeout} seconds."
            }
        except Exception as e:
            self.pending_requests.pop(req_id, None)
            return {
                "status": "error",
                "result": f"Error executing '{tool_name}' on '{target.hostname}': {str(e)}"
            }
