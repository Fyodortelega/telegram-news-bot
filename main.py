import os
from telegram import Bot

TOKEN = os.getenv("TOKEN")
CHANNEL = os.getenv("CHANNEL")

print("BOT STARTED")

bot = Bot(token=TOKEN)
bot.send_message(chat_id=CHANNEL, text="✅ Бот работает через Render")
