import logging
import asyncio
import base64
import os
import tempfile
import time
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
import config
from bridge_manager import BridgeManager

logger = logging.getLogger("CloudJarvisAgent")

JARVIS_CLOUD_SYSTEM_INSTRUCTION = """
You are J.A.R.V.I.S., the sophisticated, witty, polite, and hyper-intelligent AI personal assistant created for the user.
Address the user respectfully as 'Sir' (or their preferred title/name).

You operate 24/7 in the cloud and are connected to the user's Windows PC via a secure real-time bridge.

Capabilities:
1. When the user asks for general assistance, questions, analysis, image inspection, code, or conversational tasks:
   - Handle them directly in the cloud with your high intelligence.
2. When the user requests an action on their Windows PC (open apps, volume, media, screenshot, system metrics, terminal commands, files, lock workstation):
   - Immediately invoke the appropriate tool.
3. If the tool indicates that the user's PC is currently offline/disconnected:
   - Politely inform the user that their workstation is currently offline (e.g. 'Your Windows workstation is currently offline, sir. Once powered on and connected, I can perform that for you.').
4. Keep spoken and text responses natural, charismatic, sharp, and concise.
"""

class CloudJarvisAgent:
    def __init__(self, bridge_manager: BridgeManager):
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in environment or .env")

        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.bridge = bridge_manager
        self.chat_sessions: Dict[str, Any] = {}
        
        # State tracked per request
        self.last_screenshot_bytes: Optional[bytes] = None
        self.last_files_to_send: List[Dict[str, Any]] = []

    def _build_tools_list(self):
        """Define Python callable tools for Gemini Automatic Function Calling (AFC)."""

        def run_powershell(command: str) -> str:
            """Execute a Windows PowerShell command on the user's PC."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("run_powershell", {"command": command}))
            return res.get("result", "Execution failed.")

        def take_screenshot() -> str:
            """Capture a screenshot of the user's active PC screen."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("take_screenshot", {}))
            if res.get("screenshot_base64"):
                try:
                    self.last_screenshot_bytes = base64.b64decode(res["screenshot_base64"])
                except Exception as e:
                    logger.error(f"Failed to decode screenshot base64: {e}")
            return res.get("result", "Screenshot captured.")

        def open_application_or_url(target: str) -> str:
            """Open an application, URL, or program on the user's PC."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("open_application_or_url", {"target": target}))
            return res.get("result", f"Attempted to open {target}.")

        def control_volume(action: str) -> str:
            """Adjust Windows audio volume (up, down, mute, unmute)."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("control_volume", {"action": action}))
            return res.get("result", "Volume adjusted.")

        def control_media(action: str) -> str:
            """Control media playback (play_pause, next, prev, stop)."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("control_media", {"action": action}))
            return res.get("result", "Media playback updated.")

        def lock_workstation() -> str:
            """Lock the user's Windows PC."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("lock_workstation", {}))
            return res.get("result", "Workstation locked.")

        def get_system_status() -> str:
            """Get real-time CPU, RAM, battery, uptime, and date/time of the PC."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("get_system_status", {}))
            return res.get("result", "System status retrieved.")

        def list_open_windows() -> str:
            """List all active open application windows on the PC."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("list_open_windows", {}))
            return res.get("result", "Windows listed.")

        def focus_window(window_title: str) -> str:
            """Bring a specific application window to the foreground."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("focus_window", {"window_title": window_title}))
            return res.get("result", f"Focus shifted to {window_title}.")

        def close_application(process_name: str) -> str:
            """Close or terminate an application by process name."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("close_application", {"process_name": process_name}))
            return res.get("result", f"Closed {process_name}.")

        def get_clipboard_text() -> str:
            """Read current text from Windows clipboard."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("get_clipboard_text", {}))
            return res.get("result", "Clipboard read.")

        def set_clipboard_text(text: str) -> str:
            """Copy text onto the Windows clipboard."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("set_clipboard_text", {"text": text}))
            return res.get("result", "Copied to clipboard.")

        def show_desktop_notification(title: str, message: str) -> str:
            """Display a desktop notification toast on the PC."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("show_desktop_notification", {"title": title, "message": message}))
            return res.get("result", "Notification displayed.")

        def search_files(query: str, root_folder: str = "") -> str:
            """Search for files matching a pattern on the PC (Downloads, Documents, Desktop, etc.)."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("search_files", {"query": query, "root_folder": root_folder}))
            return res.get("result", "File search complete.")

        def read_text_file(file_path: str, max_lines: int = 60) -> str:
            """Read lines from a text/code document on the PC."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("read_text_file", {"file_path": file_path, "max_lines": max_lines}))
            return res.get("result", "File read.")

        def send_file_to_telegram(file_path: str) -> str:
            """Transfer a document, photo, or file from the PC to the user on Telegram."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("send_file_to_telegram", {"file_path": file_path}))
            if res.get("file_data_base64"):
                try:
                    self.last_files_to_send.append({
                        "filename": res.get("filename", os.path.basename(file_path)),
                        "data": base64.b64decode(res["file_data_base64"])
                    })
                except Exception as e:
                    logger.error(f"Failed to decode file base64: {e}")
            return res.get("result", f"File '{os.path.basename(file_path)}' prepared for transfer.")

        def press_hotkey_or_type(text: str = "", hotkey: str = "") -> str:
            """Type keyboard text or press keyboard shortcuts on PC."""
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self.bridge.execute_tool_on_pc("press_hotkey_or_type", {"text": text, "hotkey": hotkey}))
            return res.get("result", "Keyboard action executed.")

        def check_pc_status() -> str:
            """Check if the user's PC is currently online or offline."""
            if self.bridge.is_connected:
                info = self.bridge.pc_info
                return f"🟢 PC is ONLINE (Host: {info.get('hostname', 'Windows PC')}, OS: {info.get('os', 'Windows')})."
            return "🔴 PC is currently OFFLINE / disconnected."

        return [
            run_powershell,
            take_screenshot,
            open_application_or_url,
            control_volume,
            control_media,
            lock_workstation,
            get_system_status,
            list_open_windows,
            focus_window,
            close_application,
            get_clipboard_text,
            set_clipboard_text,
            show_desktop_notification,
            search_files,
            read_text_file,
            send_file_to_telegram,
            press_hotkey_or_type,
            check_pc_status,
        ]

    def _get_or_create_chat(self, user_id: int, model_name: str):
        tools = self._build_tools_list()
        config_obj = types.GenerateContentConfig(
            system_instruction=JARVIS_CLOUD_SYSTEM_INSTRUCTION,
            tools=tools,
            temperature=0.7,
        )
        return self.client.chats.create(model=model_name, config=config_obj)

    async def process_user_input(
        self,
        user_id: int,
        text: str = None,
        audio_bytes: bytes = None,
        audio_mime: str = "audio/ogg",
        image_bytes: bytes = None,
        image_mime: str = "image/jpeg"
    ) -> dict:
        """Process user message in the cloud and coordinate with local PC if needed."""
        self.last_screenshot_bytes = None
        self.last_files_to_send.clear()

        # Build payload
        if audio_bytes:
            message_payload = [
                types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime),
                "Listen to my voice note instruction and fulfill it as Jarvis. Execute any necessary tools."
            ]
        elif image_bytes:
            caption = text or "Please analyze this image and assist me accordingly, sir."
            message_payload = [
                types.Part.from_bytes(data=image_bytes, mime_type=image_mime),
                caption
            ]
        elif text:
            message_payload = text
        else:
            return {
                "text": "I didn't receive any input, sir.",
                "screenshot_bytes": None,
                "files_to_send": [],
                "error": None
            }

        models_to_try = [config.PRIMARY_MODEL] + [m for m in config.FALLBACK_MODELS if m != config.PRIMARY_MODEL]
        last_error = None

        for model_name in models_to_try:
            try:
                chat_key = f"{user_id}_{model_name}"
                if chat_key not in self.chat_sessions:
                    self.chat_sessions[chat_key] = self._get_or_create_chat(user_id, model_name)

                chat = self.chat_sessions[chat_key]
                # Run the blocking send_message in thread pool to avoid blocking asyncio event loop
                response = await asyncio.to_thread(chat.send_message, message_payload)

                reply_text = response.text or "Task executed, sir."
                return {
                    "text": reply_text,
                    "screenshot_bytes": self.last_screenshot_bytes,
                    "files_to_send": list(self.last_files_to_send),
                    "error": None
                }

            except Exception as e:
                logger.warning(f"Model '{model_name}' encountered error: {e}. Trying fallback...")
                last_error = e
                chat_key = f"{user_id}_{model_name}"
                if chat_key in self.chat_sessions:
                    del self.chat_sessions[chat_key]
                await asyncio.sleep(0.5)

        return {
            "text": f"My apologies sir, I encountered an issue: {str(last_error)}",
            "screenshot_bytes": self.last_screenshot_bytes,
            "files_to_send": list(self.last_files_to_send),
            "error": str(last_error)
        }
