import asyncio
import json
import logging
import uuid
import base64
from typing import Dict, Any, Optional
import aiohttp
from aiohttp import web

logger = logging.getLogger("BridgeManager")

class BridgeManager:
    """Manages the real-time WebSocket connection between Railway Cloud and Local Windows PC."""
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.active_ws: Optional[web.WebSocketResponse] = None
        self.pc_info: Dict[str, Any] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}

    @property
    def is_connected(self) -> bool:
        return self.active_ws is not None and not self.active_ws.closed

    async def handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=45.0, max_msg_size=50 * 1024 * 1024)
        await ws.prepare(request)

        authenticated = False
        peer_name = request.remote

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
                        # If an older socket exists, close it
                        if self.active_ws and self.active_ws != ws and not self.active_ws.closed:
                            try:
                                await self.active_ws.close()
                            except Exception:
                                pass

                        self.active_ws = ws
                        self.pc_info = {
                            "hostname": data.get("hostname", "Windows PC"),
                            "os": data.get("os", "Windows"),
                            "connected_at": data.get("timestamp")
                        }
                        logger.info(f"✅ Local PC connected & authenticated: {self.pc_info['hostname']} ({peer_name})")
                        await ws.send_json({"type": "auth_ok", "message": "Bridge connected successfully."})

                    # Handle RPC Tool Response from PC
                    elif msg_type == "tool_response":
                        req_id = data.get("id")
                        if req_id and req_id in self.pending_requests:
                            fut = self.pending_requests.pop(req_id)
                            if not fut.done():
                                fut.set_result(data)

                    # Handle Ping
                    elif msg_type == "ping":
                        await ws.send_json({"type": "pong"})

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")

        finally:
            if self.active_ws == ws:
                self.active_ws = None
                self.pc_info = {}
                logger.info("⚠️ Local PC Bridge disconnected. PC is now marked OFFLINE.")
                # Cancel any pending requests
                for req_id, fut in list(self.pending_requests.items()):
                    if not fut.done():
                        fut.set_exception(ConnectionResetError("PC disconnected while executing task."))
                self.pending_requests.clear()

        return ws

    async def execute_tool_on_pc(self, tool_name: str, tool_args: Dict[str, Any], timeout: float = 60.0) -> Dict[str, Any]:
        """Send a tool execution command over WebSocket to the local PC and await response."""
        if not self.is_connected:
            # Give a brief 3-second grace period in case the client is auto-reconnecting
            for _ in range(6):
                await asyncio.sleep(0.5)
                if self.is_connected:
                    break

        if not self.is_connected:
            return {
                "status": "offline",
                "result": "Notice to Jarvis: The user's Windows PC is currently offline/disconnected. Inform the user politely that their PC is not reachable right now."
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
            await self.active_ws.send_json(payload)
            response = await asyncio.wait_for(fut, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            self.pending_requests.pop(req_id, None)
            return {
                "status": "error",
                "result": f"Error: Command '{tool_name}' timed out on the local PC after {timeout} seconds."
            }
        except Exception as e:
            self.pending_requests.pop(req_id, None)
            return {
                "status": "error",
                "result": f"Error executing '{tool_name}' via bridge: {str(e)}"
            }
