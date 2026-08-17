import os
import logging
import asyncio
from google import genai
from google.genai import types
import config
import tools

logger = logging.getLogger("JarvisAgent")

JARVIS_SYSTEM_INSTRUCTION = """
You are J.A.R.V.I.S., the sophisticated, witty, polite, and hyper-intelligent AI personal assistant created for the user.
Address the user respectfully as 'Sir' (or their preferred title/name).
You possess comprehensive control over the user's Windows PC through your available tools.

Your capabilities include:
- Executing PowerShell commands & terminal tasks: `run_powershell`
- Screen capture: `take_screenshot`
- Launching apps, programs, websites, URLs: `open_application_or_url`
- Volume adjustments: `control_volume` (up, down, mute, unmute)
- Music/Media control: `control_media` (play_pause, next, prev, stop)
- PC security & lock: `lock_workstation`
- System metrics (CPU, RAM, Battery, Time): `get_system_status`
- Window management: `list_open_windows`, `focus_window`, `close_application`
- Clipboard control: `get_clipboard_text`, `set_clipboard_text`
- Desktop notifications: `show_desktop_notification`
- File searching & reading: `search_files`, `read_text_file`
- Sending files/documents/images from PC to Telegram: `send_file_to_telegram`
- Keyboard simulation: `press_hotkey_or_type`

Guidelines:
1. When the user requests an action on their PC, immediately execute the corresponding tool.
2. Keep spoken and text responses natural, polite, concise, and charismatic (e.g. 'Right away, sir', 'System report ready, sir').
3. Avoid overly verbose explanations unless asked.
"""

class JarvisAgent:
    def __init__(self):
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in .env")
        
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.chat_sessions = {}  # Map (user_id, model_name) -> chat session

    def _get_or_create_chat(self, user_id: int, model_name: str):
        config_obj = types.GenerateContentConfig(
            system_instruction=JARVIS_SYSTEM_INSTRUCTION,
            tools=tools.AVAILABLE_TOOLS,
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
        """Process text, voice audio, or image input from user and return response dict.
        
        Returns:
            {
                "text": str,
                "screenshot": str | None,
                "files_to_send": list[str],
                "error": str | None
            }
        """
        # Reset tool outputs
        tools.LAST_SCREENSHOT_PATH = None
        tools.PENDING_FILES_TO_SEND.clear()

        # Build message payload
        if audio_bytes:
            message_payload = [
                types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime),
                "Listen to my voice note instruction and fulfill it as Jarvis. Execute any necessary tools."
            ]
        elif image_bytes:
            caption = text or "Please inspect this image and assist me accordingly, sir."
            message_payload = [
                types.Part.from_bytes(data=image_bytes, mime_type=image_mime),
                caption
            ]
        elif text:
            message_payload = text
        else:
            return {
                "text": "I didn't receive any input, sir.",
                "screenshot": None,
                "files_to_send": [],
                "error": None
            }

        # List of models to try in fallback order
        models_to_try = [config.PRIMARY_MODEL] + [m for m in config.FALLBACK_MODELS if m != config.PRIMARY_MODEL]
        last_error = None

        for model_name in models_to_try:
            try:
                chat_key = f"{user_id}_{model_name}"
                if chat_key not in self.chat_sessions:
                    self.chat_sessions[chat_key] = self._get_or_create_chat(user_id, model_name)

                chat = self.chat_sessions[chat_key]
                response = chat.send_message(message_payload)

                reply_text = response.text or "Task executed, sir."
                return {
                    "text": reply_text,
                    "screenshot": tools.LAST_SCREENSHOT_PATH,
                    "files_to_send": list(tools.PENDING_FILES_TO_SEND),
                    "error": None
                }

            except Exception as e:
                logger.warning(f"Model '{model_name}' encountered error: {e}. Trying fallback...")
                last_error = e
                # Clean up problematic session
                chat_key = f"{user_id}_{model_name}"
                if chat_key in self.chat_sessions:
                    del self.chat_sessions[chat_key]
                
                # Small pause before fallback to alleviate short rate spikes
                await asyncio.sleep(0.5)

        return {
            "text": f"My apologies sir, I encountered an issue: {str(last_error)}",
            "screenshot": tools.LAST_SCREENSHOT_PATH,
            "files_to_send": list(tools.PENDING_FILES_TO_SEND),
            "error": str(last_error)
        }
