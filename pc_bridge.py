import asyncio
import base64
import json
import logging
import os
import platform
import socket
import sys
import time
import aiohttp

import config
import tools

# Ensure stdout/stderr work under pythonw
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge.log")
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_file_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PCBridgeClient")

# Mapping of tool names to functions in tools.py
TOOL_MAP = {
    "run_powershell": tools.run_powershell,
    "take_screenshot": tools.take_screenshot,
    "open_application_or_url": tools.open_application_or_url,
    "control_volume": tools.control_volume,
    "control_media": tools.control_media,
    "lock_workstation": tools.lock_workstation,
    "get_system_status": tools.get_system_status,
    "list_open_windows": tools.list_open_windows,
    "focus_window": tools.focus_window,
    "close_application": tools.close_application,
    "get_clipboard_text": tools.get_clipboard_text,
    "set_clipboard_text": tools.set_clipboard_text,
    "show_desktop_notification": tools.show_desktop_notification,
    "search_files": tools.search_files,
    "read_text_file": tools.read_text_file,
    "send_file_to_telegram": tools.send_file_to_telegram,
    "press_hotkey_or_type": tools.press_hotkey_or_type,
}

def execute_local_tool(tool_name: str, args: dict) -> dict:
    """Execute tool locally and gather results, screenshots, or files."""
    tools.LAST_SCREENSHOT_PATH = None
    tools.PENDING_FILES_TO_SEND.clear()

    fn = TOOL_MAP.get(tool_name)
    if not fn:
        return {"status": "error", "result": f"Unknown tool: {tool_name}"}

    try:
        # Execute tool
        result_text = fn(**args)
        
        screenshot_b64 = None
        if tools.LAST_SCREENSHOT_PATH and os.path.exists(tools.LAST_SCREENSHOT_PATH):
            try:
                with open(tools.LAST_SCREENSHOT_PATH, "rb") as sf:
                    screenshot_b64 = base64.b64encode(sf.read()).decode("utf-8")
                os.remove(tools.LAST_SCREENSHOT_PATH)
            except Exception as e:
                logger.error(f"Failed to read screenshot: {e}")

        file_b64 = None
        filename = None
        if tools.PENDING_FILES_TO_SEND:
            target_path = tools.PENDING_FILES_TO_SEND[0]
            if os.path.exists(target_path):
                try:
                    with open(target_path, "rb") as ff:
                        file_b64 = base64.b64encode(ff.read()).decode("utf-8")
                    filename = os.path.basename(target_path)
                except Exception as e:
                    logger.error(f"Failed to read file transfer: {e}")

        return {
            "status": "ok",
            "result": result_text,
            "screenshot_base64": screenshot_b64,
            "file_data_base64": file_b64,
            "filename": filename
        }
    except Exception as e:
        logger.error(f"Error executing {tool_name}: {e}")
        return {"status": "error", "result": f"Execution error: {str(e)}"}

async def run_client():
    railway_url = config.RAILWAY_URL
    if not railway_url:
        # Default local URL if testing locally
        railway_url = f"ws://localhost:{config.PORT}/ws"
        logger.warning(f"RAILWAY_URL not configured in .env. Defaulting to: {railway_url}")

    hostname = platform.node() or socket.gethostname() or "Windows PC"
    logger.info(f"⚡ J.A.R.V.I.S. PC Bridge Client starting for host: {hostname}")
    logger.info(f"Target Server: {railway_url}")

    reconnect_delay = 3

    while True:
        try:
            logger.info(f"Connecting to J.A.R.V.I.S. Cloud Bridge at {railway_url}...")
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    railway_url,
                    heartbeat=20.0,
                    max_msg_size=50 * 1024 * 1024
                ) as ws:
                    # 1. Send Authentication Handshake
                    auth_payload = {
                        "type": "auth",
                        "secret": config.BRIDGE_SECRET_KEY,
                        "hostname": hostname,
                        "os": "Windows",
                        "timestamp": time.time()
                    }
                    await ws.send_json(auth_payload)
                    logger.info("Sent auth handshake to server...")

                    reconnect_delay = 3  # Reset delay on successful connect

                    # 2. Process incoming server requests
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                            except Exception:
                                continue

                            msg_type = data.get("type")

                            if msg_type == "auth_ok":
                                logger.info("✅ Authenticated & Connected to J.A.R.V.I.S. Cloud 24/7 Server!")

                            elif msg_type == "auth_fail":
                                logger.error(f"❌ Server rejected authentication: {data.get('reason')}")
                                logger.error("Please ensure BRIDGE_SECRET_KEY matches on both PC and Railway.")
                                await asyncio.sleep(10)
                                break

                            elif msg_type == "execute_tool":
                                req_id = data.get("id")
                                tool_name = data.get("tool_name")
                                args = data.get("args", {})

                                logger.info(f"Executing cloud tool: {tool_name}")
                                # Execute in threadpool so blocking Windows APIs do not freeze the socket
                                tool_response = await asyncio.to_thread(execute_local_tool, tool_name, args)
                                tool_response["type"] = "tool_response"
                                tool_response["id"] = req_id

                                await ws.send_json(tool_response)
                                logger.info(f"Completed tool: {tool_name}")

                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            logger.warning("Connection closed by server.")
                            break

        except aiohttp.ClientConnectorError as e:
            logger.warning(f"Cloud server not reachable ({e}). Retrying in {reconnect_delay}s...")
        except Exception as e:
            logger.error(f"Bridge connection error: {e}. Retrying in {reconnect_delay}s...")

        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 1.5, 30)

def acquire_single_instance_lock():
    """Ensure only one instance of the PC bridge runs at a time."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 57788))
        return s
    except (OSError, socket.error):
        logger.warning("Another instance of J.A.R.V.I.S. PC Bridge is already running. Exiting.")
        sys.exit(0)

if __name__ == "__main__":
    _lock_socket = acquire_single_instance_lock()
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        logger.info("PC Bridge stopped by user.")
