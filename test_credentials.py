import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

async def test():
    print("Testing Telegram Bot Token...")
    try:
        from telegram import Bot
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        bot = Bot(token)
        me = await bot.get_me()
        print(f"✅ Telegram Connected: @{me.username} ({me.first_name})")
    except Exception as e:
        print(f"❌ Telegram Token Error: {e}")

    print("\nTesting Gemini API Key...")
    try:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-3.7-flash",
            contents="Say 'Jarvis online!'"
        )
        print(f"✅ Gemini Response: {resp.text.strip()}")
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
