import logging
import os
import sys
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
from agent import JarvisAgent
from tts import text_to_speech

# Ensure stdout and stderr exist even in headless / pythonw / background environments
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.log")
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_file_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("JarvisBot")

agent = None

def check_authorization(update: Update) -> bool:
    """Check if the user is authorized to interact with Jarvis."""
    if not config.ALLOWED_USER_IDS:
        # If no user ID is locked yet, allow and print info
        return True
    user_id = update.effective_user.id if update.effective_user else None
    return user_id in config.ALLOWED_USER_IDS

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    user_id = user.id
    
    welcome_msg = (
        f"🎩 **Greetings, {user.first_name}! I am J.A.R.V.I.S.**\n\n"
        f"Your personal AI assistant is online and connected to your Windows PC.\n\n"
        f"🔑 **Your Telegram User ID:** `{user_id}`\n\n"
        f"🎙️ **Features & Commands:**\n"
        f"• **Voice Notes & Audio**: Send voice messages anytime — I listen and respond in voice!\n"
        f"• **PC Control**: Open apps, adjust volume, control music, check CPU/RAM stats, lock PC.\n"
        f"• **Multimodal Vision**: Send photos/screenshots to analyze.\n"
        f"• **File Transfers**: Ask me to search or send files from your PC.\n"
        f"• **Terminal Execution**: Execute custom PowerShell tasks seamlessly.\n\n"
        f"Type `/help` for shortcut commands or simply talk to me!"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "🛠️ **J.A.R.V.I.S. Command & Voice Guide**\n\n"
        "**Quick Commands:**\n"
        "• `/status` - Get live PC CPU, RAM, battery & time\n"
        "• `/screenshot` - Take & send a desktop screenshot\n"
        "• `/lock` - Lock Windows PC immediately\n"
        "• `/myid` - View your Telegram User ID\n\n"
        "**Natural Language & Voice Examples:**\n"
        "• *'Open Spotify and turn the volume up'* \n"
        "• *'What windows are currently open?'*\n"
        "• *'Copy \"meeting notes link\" to my clipboard'*\n"
        "• *'Search for *.pdf files in Downloads'*\n"
        "• *'Show desktop notification saying \"Coffee break!\"'* \n"
        "• *'Send me invoice.pdf from Documents'*"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return user's Telegram ID."""
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"🆔 Your Telegram User ID is: `{user_id}`\n"
        f"To lock Jarvis to your account only, add `ALLOWED_USER_IDS={user_id}` in `.env`.",
        parse_mode="Markdown"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick status shortcut."""
    await handle_message_content(update, context, text="Give me a quick system status report.")

async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick screenshot shortcut."""
    await handle_message_content(update, context, text="Take a screenshot of the computer screen.")

async def lock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick lock workstation shortcut."""
    await handle_message_content(update, context, text="Lock the workstation immediately.")

async def handle_message_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str = None,
    audio_bytes: bytes = None,
    audio_mime: str = "audio/ogg",
    image_bytes: bytes = None,
    image_mime: str = "image/jpeg"
):
    """Generic handler for processing user input and sending text, voice, screenshot, and files."""
    global agent
    user_id = update.effective_user.id
    
    if not check_authorization(update):
        await update.message.reply_text(
            f"⛔ **Access Denied**\n\nYour Telegram User ID is: `{user_id}`\n"
            f"Please add `{user_id}` to `ALLOWED_USER_IDS` in your `.env` configuration.",
            parse_mode="Markdown"
        )
        return

    # Notify user that Jarvis is working
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Process through Jarvis Agent
    response_data = await agent.process_user_input(
        user_id=user_id,
        text=text,
        audio_bytes=audio_bytes,
        audio_mime=audio_mime,
        image_bytes=image_bytes,
        image_mime=image_mime
    )
    
    reply_text = response_data.get("text", "Task completed, sir.")
    screenshot_path = response_data.get("screenshot")
    files_to_send = response_data.get("files_to_send", [])

    # Send screenshot if captured
    if screenshot_path and os.path.exists(screenshot_path):
        try:
            with open(screenshot_path, "rb") as photo:
                await update.message.reply_photo(photo=photo, caption="📸 Screen capture, sir.")
            os.remove(screenshot_path)
        except Exception as e:
            logger.error(f"Failed to send screenshot: {e}")

    # Send any requested files/documents
    for file_path in files_to_send:
        if os.path.exists(file_path):
            try:
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
                with open(file_path, "rb") as doc:
                    await update.message.reply_document(document=doc, filename=os.path.basename(file_path))
            except Exception as e:
                logger.error(f"Failed to send document '{file_path}': {e}")
                await update.message.reply_text(f"⚠️ Could not transfer file: {str(e)}")

    # Send text response
    await update.message.reply_text(reply_text)

    # Send Voice Reply if enabled
    if config.VOICE_REPLY_ENABLED and reply_text:
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.RECORD_VOICE)
            voice_audio_path = await text_to_speech(reply_text)
            if voice_audio_path and os.path.exists(voice_audio_path):
                with open(voice_audio_path, "rb") as voice_file:
                    await update.message.reply_voice(voice=voice_file)
                os.remove(voice_audio_path)
        except Exception as e:
            logger.error(f"Failed to send voice reply: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    text = update.message.text
    await handle_message_content(update, context, text=text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice notes."""
    try:
        voice = update.message.voice
        voice_file = await context.bot.get_file(voice.file_id)
        audio_bytearray = await voice_file.download_as_bytearray()
        await handle_message_content(update, context, audio_bytes=bytes(audio_bytearray), audio_mime="audio/ogg")
    except Exception as e:
        logger.error(f"Error handling voice message: {e}")
        await update.message.reply_text(f"Sorry sir, I had trouble processing your voice note: {str(e)}")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming audio files."""
    try:
        audio = update.message.audio
        audio_file = await context.bot.get_file(audio.file_id)
        audio_bytearray = await audio_file.download_as_bytearray()
        mime = audio.mime_type or "audio/mp3"
        await handle_message_content(update, context, audio_bytes=bytes(audio_bytearray), audio_mime=mime)
    except Exception as e:
        logger.error(f"Error handling audio file: {e}")
        await update.message.reply_text(f"Sorry sir, I had trouble processing your audio file: {str(e)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming images/photos."""
    try:
        photo = update.message.photo[-1]  # Highest resolution
        photo_file = await context.bot.get_file(photo.file_id)
        img_bytearray = await photo_file.download_as_bytearray()
        caption = update.message.caption or "Please analyze this image, sir."
        await handle_message_content(update, context, text=caption, image_bytes=bytes(img_bytearray), image_mime="image/jpeg")
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text(f"Sorry sir, I had trouble inspecting the image: {str(e)}")

def main():
    try:
        global agent
        if not config.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN is not set in .env!")
            sys.exit(1)

        if not config.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set in .env!")
            sys.exit(1)

        logger.info("⚡ Initializing J.A.R.V.I.S. Telegram Bridge...")
        agent = JarvisAgent()

        application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

        # Commands
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("myid", myid_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("screenshot", screenshot_command))
        application.add_handler(CommandHandler("lock", lock_command))

        # Messages
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

        logger.info("🤖 J.A.R.V.I.S. is now running and listening on Telegram!")
        application.run_polling(stop_signals=None)
    except Exception as e:
        logger.exception(f"Fatal error in J.A.R.V.I.S. runtime: {e}")

if __name__ == "__main__":
    main()
