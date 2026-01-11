import os
import asyncio
import feedparser
import requests
from fastapi import FastAPI
from telegram import Bot

TOKEN = os.getenv("TOKEN")
CHANNEL = os.getenv("CHANNEL")

if not TOKEN or not CHANNEL:
    print("❌ Переменные окружения пустые!")
    exit(1)

bot = Bot(token=TOKEN)
app = FastAPI()

RSS_LIST = [
    "https://lenta.ru/rss"
]

posted_urls = set()

async def fetch_and_post_once():
    for rss_url in RSS_LIST:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:5]:
            if entry.link in posted_urls:
                continue

            text = f"{entry.title}\n{entry.link}"

            # Попытка получить картинку
            image_url = None
            if 'media_content' in entry:
                image_url = entry.media_content[0]['url']
            elif 'media_thumbnail' in entry:
                image_url = entry.media_thumbnail[0]['url']

            try:
                if image_url:
                    resp = requests.get(image_url)
                    if resp.status_code == 200:
                        await bot.send_photo(
                            chat_id=CHANNEL,
                            photo=resp.content,
                            caption=text
                        )
                        print(f"Posted with image: {entry.title}")
                    else:
                        await bot.send_message(chat_id=CHANNEL, text=text)
                        print(f"Posted without image: {entry.title}")
                else:
                    await bot.send_message(chat_id=CHANNEL, text=text)
                    print(f"Posted without image: {entry.title}")
            except Exception as e:
                print(f"Error posting: {e}")

            posted_urls.add(entry.link)

@app.on_event("startup")
async def startup_event():
    # отправляем стартовое сообщение один раз
    if not os.path.exists("sent.flag"):
        await bot.send_message(chat_id=CHANNEL, text="✅ Бот запущен через Render Web Service!")
        with open("sent.flag", "w") as f:
            f.write("sent")
    # делаем первый пост RSS один раз
    await fetch_and_post_once()

@app.get("/")
async def root():
    return {"status": "Bot is running"}

# Для Render Web Service
if name == "main":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
