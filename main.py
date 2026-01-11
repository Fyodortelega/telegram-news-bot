import os
import asyncio
from telegram import Bot

TOKEN = os.getenv("TOKEN")
CHANNEL = os.getenv("CHANNEL")

print("TOKEN:", TOKEN)
print("CHANNEL:", CHANNEL)

async def main():
    if not TOKEN or not CHANNEL:
        print("❌ Переменные окружения пустые!")
        return

    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=CHANNEL, text="✅ Бот работает через Render")
    await bot.session.close()

asyncio.run(main())
