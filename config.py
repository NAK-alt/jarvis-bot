import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ALLOWED_USER_IDS_RAW = os.getenv("ALLOWED_USER_IDS", "").strip()

# Parse allowed user IDs (comma-separated integers)
ALLOWED_USER_IDS = []
if ALLOWED_USER_IDS_RAW:
    for uid in ALLOWED_USER_IDS_RAW.split(","):
        uid = uid.strip()
        if uid.isdigit():
            ALLOWED_USER_IDS.append(int(uid))

# Voice Settings (Microsoft Edge-TTS)
VOICE_NAME = os.getenv("VOICE_NAME", "en-GB-RyanNeural")
VOICE_REPLY_ENABLED = os.getenv("VOICE_REPLY_ENABLED", "true").lower() in ("true", "1", "yes")

# Gemini Models with fallbacks (Speed-optimized)
PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
FALLBACK_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.7-flash",
    "gemini-3-flash-preview",
]

# Bridge & Cloud Configuration (Railway)
PORT = int(os.getenv("PORT", "8080"))
BRIDGE_SECRET_KEY = os.getenv("BRIDGE_SECRET_KEY", "jarvis-secret-key-change-me").strip()
RAILWAY_URL = os.getenv("RAILWAY_URL", "").strip()  # e.g., "wss://your-app.up.railway.app/ws"
