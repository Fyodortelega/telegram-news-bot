import os
from telegram import Bot

TOKEN = os.getenv("TOKEN")
CHANNEL = os.getenv("CHANNEL")

print("TOKEN:", TOKEN)
print("CHANNEL:", CHANNEL)

bot = Bot(token=TOKEN)
bot.send_message(chat_id=CHANNEL, text="✅ Бот успешно запущен")
