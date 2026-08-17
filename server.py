import asyncio
import io
import logging
import os
import sys
from aiohttp import web
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import config
from bridge_manager import BridgeManager
from cloud_agent import CloudJarvisAgent
from tts import text_to_speech

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("JarvisServer")

bridge_manager = None
cloud_agent = None

def check_authorization(update: Update) -> bool:
    """Check if the user is authorized to interact with Jarvis."""
    if not config.ALLOWED_USER_IDS:
        return True
    user_id = update.effective_user.id if update.effective_user else None
    return user_id in config.ALLOWED_USER_IDS

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    user_id = user.id
    pc_status = "🟢 Connected (Online)" if bridge_manager.is_connected else "🔴 Disconnected (Offline)"
    
    welcome_msg = (
        f"🎩 **Greetings, {user.first_name}! I am J.A.R.V.I.S.**\n\n"
        f"I am operating **24/7 in the cloud** and linked to your personal PC.\n\n"
        f"🖥️ **Windows PC Status:** {pc_status}\n"
        f"🔑 **Your Telegram ID:** `{user_id}`\n\n"
        f"🎙️ **Features:**\n"
        f"• **24/7 AI & Voice Notes**: Talk to me anytime — I answer in voice!\n"
        f"• **Remote PC Control**: When your PC is on, I can take screenshots, adjust volume, launch apps, and transfer files.\n"
        f"• **Offline Resilience**: When your PC is off, I continue chatting, reasoning, and assisting you 24/7 in the cloud.\n\n"
        f"Type `/help` for shortcuts or simply speak to me, sir."
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    pc_status = "🟢 Online" if bridge_manager.is_connected else "🔴 Offline"
    help_text = (
        f"🛠️ **J.A.R.V.I.S. Command & Voice Guide** (PC: {pc_status})\n\n"
        "**Quick Commands:**\n"
        "• `/status` - Check PC connectivity, CPU, RAM & cloud status\n"
        "• `/screenshot` - Capture current PC screen\n"
        "• `/lock` - Lock Windows PC\n"
        "• `/myid` - View your Telegram User ID\n\n"
        "**Voice & Chat Examples:**\n"
        "• *'What is the status of my workstation?'*\n"
        "• *'Open Spotify and skip to the next track'*\n"
        "• *'Search for *.pdf in Downloads'*\n"
        "• *'Send me invoice.pdf from Documents'*\n"
        "• *'Explain how quantum computing works'* (Works 24/7 even if PC is off!)"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    if bridge_manager.is_connected:
        await handle_message_content(update, context, text="Check system status of my PC.")
    else:
        await update.message.reply_text(
            "☁️ **J.A.R.V.I.S. Cloud**: 🟢 Online 24/7\n"
            "💻 **Windows PC**: 🔴 Offline / Disconnected\n\n"
            "Your PC bridge client is currently disconnected. Once you turn on your PC and run the bridge, PC controls will be active immediately.",
            parse_mode="Markdown"
        )

async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /screenshot command."""
    await handle_message_content(update, context, text="Take a screenshot of the computer screen.")

async def lock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /lock command."""
    await handle_message_content(update, context, text="Lock the workstation.")

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /myid command."""
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"🆔 Your Telegram User ID is: `{user_id}`\n"
        f"To lock Jarvis to your account only, add `ALLOWED_USER_IDS={user_id}` in Railway environment variables.",
        parse_mode="Markdown"
    )

async def handle_message_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str = None,
    audio_bytes: bytes = None,
    audio_mime: str = "audio/ogg",
    image_bytes: bytes = None,
    image_mime: str = "image/jpeg"
):
    """Generic message processor with voice, photo, and file reply support."""
    global cloud_agent
    user_id = update.effective_user.id

    if not check_authorization(update):
        await update.message.reply_text(
            f"⛔ **Access Denied**\n\nYour Telegram User ID is: `{user_id}`\n"
            f"Please add `{user_id}` to `ALLOWED_USER_IDS` in Railway environment variables.",
            parse_mode="Markdown"
        )
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Process through Cloud Jarvis Agent
    response_data = await cloud_agent.process_user_input(
        user_id=user_id,
        text=text,
        audio_bytes=audio_bytes,
        audio_mime=audio_mime,
        image_bytes=image_bytes,
        image_mime=image_mime
    )

    reply_text = response_data.get("text", "Task completed, sir.")
    screenshot_bytes = response_data.get("screenshot_bytes")
    files_to_send = response_data.get("files_to_send", [])

    # Send screenshot if received from PC
    if screenshot_bytes:
        try:
            photo_file = io.BytesIO(screenshot_bytes)
            photo_file.name = "screenshot.png"
            await update.message.reply_photo(photo=photo_file, caption="📸 Screenshot from your PC, sir.")
        except Exception as e:
            logger.error(f"Failed to send screenshot: {e}")

    # Send any files transferred from PC
    for f in files_to_send:
        try:
            doc_file = io.BytesIO(f["data"])
            doc_file.name = f.get("filename", "file.dat")
            await update.message.reply_document(document=doc_file, filename=doc_file.name)
        except Exception as e:
            logger.error(f"Failed to send transferred file: {e}")

    # Send text response immediately
    await update.message.reply_text(reply_text)

    # Send voice reply asynchronously in background if enabled
    if config.VOICE_REPLY_ENABLED and reply_text and len(reply_text.strip()) > 0:
        asyncio.create_task(_send_voice_note_background(context.bot, update.effective_chat.id, reply_text))

async def _send_voice_note_background(bot, chat_id: int, text: str):
    """Generate and send voice note asynchronously in the background so text response is not delayed."""
    try:
        voice_path = await text_to_speech(text)
        if voice_path and os.path.exists(voice_path):
            with open(voice_path, "rb") as voice_file:
                await bot.send_voice(chat_id=chat_id, voice=voice_file)
            try:
                os.remove(voice_path)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Background voice reply error: {e}")

async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /voice on | off toggle command."""
    args = context.args
    if args and args[0].lower() in ("on", "enable", "true", "yes"):
        config.VOICE_REPLY_ENABLED = True
        await update.message.reply_text("🔊 **Voice replies: ENABLED** (Jarvis will send audio voice notes)", parse_mode="Markdown")
    elif args and args[0].lower() in ("off", "disable", "false", "no"):
        config.VOICE_REPLY_ENABLED = False
        await update.message.reply_text("⚡ **Voice replies: DISABLED** (Jarvis will reply in instant text mode only)", parse_mode="Markdown")
    else:
        status = "ENABLED 🔊" if config.VOICE_REPLY_ENABLED else "DISABLED ⚡"
        await update.message.reply_text(
            f"🎙️ **Voice Reply Status:** {status}\n\n"
            "To change setting:\n"
            "• `/voice on` - Turn voice notes on\n"
            "• `/voice off` - Turn voice notes off (maximum speed)",
            parse_mode="Markdown"
        )

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /model command to view or switch Gemini model."""
    args = context.args
    if args:
        chosen = args[0].strip()
        config.PRIMARY_MODEL = chosen
        await update.message.reply_text(f"🚀 **Primary model set to:** `{chosen}`", parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"🧠 **Current Active Model:** `{config.PRIMARY_MODEL}`\n\n"
            "Fastest models:\n"
            "• `/model gemini-3.1-flash-lite` (Ultra fast, sub-second)\n"
            "• `/model gemini-3.5-flash` (Balanced, high intelligence)\n"
            "• `/model gemini-3.7-flash` (Maximum reasoning)",
            parse_mode="Markdown"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_message_content(update, context, text=update.message.text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        voice = update.message.voice
        voice_file = await context.bot.get_file(voice.file_id)
        audio_bytearray = await voice_file.download_as_bytearray()
        await handle_message_content(update, context, audio_bytes=bytes(audio_bytearray), audio_mime="audio/ogg")
    except Exception as e:
        logger.error(f"Voice error: {e}")
        await update.message.reply_text(f"Sorry sir, trouble processing voice: {str(e)}")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        audio = update.message.audio
        audio_file = await context.bot.get_file(audio.file_id)
        audio_bytearray = await audio_file.download_as_bytearray()
        mime = audio.mime_type or "audio/mp3"
        await handle_message_content(update, context, audio_bytes=bytes(audio_bytearray), audio_mime=mime)
    except Exception as e:
        logger.error(f"Audio error: {e}")
        await update.message.reply_text(f"Sorry sir, trouble processing audio: {str(e)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        img_bytearray = await photo_file.download_as_bytearray()
        caption = update.message.caption or "Please analyze this image, sir."
        await handle_message_content(update, context, text=caption, image_bytes=bytes(img_bytearray), image_mime="image/jpeg")
    except Exception as e:
        logger.error(f"Photo error: {e}")
        await update.message.reply_text(f"Sorry sir, trouble processing image: {str(e)}")

# --- AIOHTTP Web Server Endpoints ---

async def index_handler(request: web.Request):
    return web.Response(text="🎩 J.A.R.V.I.S. 24/7 Cloud Server is Online and Operational.")

async def health_handler(request: web.Request):
    return web.json_response({
        "status": "healthy",
        "service": "J.A.R.V.I.S. Cloud Bridge",
        "pc_online": bridge_manager.is_connected,
        "pc_info": bridge_manager.pc_info
    })

async def main():
    global bridge_manager, cloud_agent

    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment!")
        sys.exit(1)

    if not config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set in environment!")
        sys.exit(1)

    # 1. Initialize Bridge Manager & Cloud Agent
    bridge_manager = BridgeManager(secret_key=config.BRIDGE_SECRET_KEY)
    cloud_agent = CloudJarvisAgent(bridge_manager)

    # 2. Build Telegram Application
    tg_app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("start", start_command))
    tg_app.add_handler(CommandHandler("help", help_command))
    tg_app.add_handler(CommandHandler("status", status_command))
    tg_app.add_handler(CommandHandler("screenshot", screenshot_command))
    tg_app.add_handler(CommandHandler("lock", lock_command))
    tg_app.add_handler(CommandHandler("myid", myid_command))
    tg_app.add_handler(CommandHandler("voice", voice_command))
    tg_app.add_handler(CommandHandler("model", model_command))

    tg_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    tg_app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    tg_app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    tg_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # 3. Setup AIOHTTP Web App for WebSocket & Healthchecks
    web_app = web.Application()
    web_app.router.add_get("/", index_handler)
    web_app.router.add_get("/health", health_handler)
    web_app.router.add_get("/ws", bridge_manager.handle_ws)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=config.PORT)

    logger.info(f"⚡ Starting J.A.R.V.I.S. Cloud Web & WebSocket Server on port {config.PORT}...")
    await site.start()

    logger.info("🤖 Starting J.A.R.V.I.S. Telegram Bot polling...")
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()

    logger.info("✅ J.A.R.V.I.S. 24/7 Cloud Server is fully online and ready!")

    # Keep running forever
    try:
        while True:
            await asyncio.sleep(3600)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Stopping services...")
    finally:
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
