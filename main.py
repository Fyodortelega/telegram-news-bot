import os
import asyncio
from telegram import Bot

TOKEN = os.getenv("TOKEN")
CHANNEL = os.getenv("CHANNEL")

async def main():
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=CHANNEL, text="✅ Бот работает через Render")

asyncio.run(main())
