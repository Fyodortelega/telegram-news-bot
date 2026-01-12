import os
import asyncio
import random
import threading
import time
import feedparser
from flask import Flask
from telegram import Bot
from bs4 import BeautifulSoup

# ================== НАСТРОЙКИ ==================

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL = os.environ.get("CHANNEL_ID")

RSS_FEEDS = [
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://tass.ru/rss/v2.xml",
    "https://lenta.ru/rss",
]

MIN_DELAY = 300   # 5 минут
MAX_DELAY = 900   # 15 минут

posted_links = set()

# ================== TELEGRAM ==================

bot = Bot(token=TOKEN)

# ================== FLASK ==================

app = Flask(name)

@app.route("/")
def home():
    return "Bot is running"

# ================== ТЕКСТ ==================

def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    trash = [
        "Реклама",
        "Фото:",
        "Источник:",
        "Читайте также",
    ]

    for t in trash:
        text = text.replace(t, "")

    text = text.strip()

    if len(text) < 50:
        return None

    # не обрываем предложение
    sentences = text.split(". ")
    result = ""
    for s in sentences:
        if len(result) + len(s) < 600:
            result += s + ". "
        else:
            break

    return result.strip()

def get_entry_text(entry):
    if hasattr(entry, "content"):
        return clean_text(entry.content[0].value)
    if entry.get("summary"):
        return clean_text(entry.summary)
    if entry.get("description"):
        return clean_text(entry.description)
    return None

# ================== ЭМОДЗИ ==================

def pick_emoji(title):
    t = title.lower()
    if "срочно" in t or "экстр" in t:
        return "🚨"
    if "кримин" in t or "убийств" in t:
        return "🚔"
    if "снег" in t or "зима" in t:
        return "☃️"
    return "📰"

# ================== ОСНОВНАЯ ЛОГИКА ==================

async def rss_loop():
    while True:
        random.shuffle(RSS_FEEDS)

        for feed_url in RSS_FEEDS:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                title = entry.get("title")
                link = entry.get("link")

                if not title or not link or link in posted_links:
                    continue

                text = get_entry_text(entry)
                if not text:
                    continue

                emoji = pick_emoji(title)

                message = (
                    f"{emoji} <b>{title}</b>\n\n"
                    f"{text}\n\n"
                    f"<i>Источник:</i> {link}"
                )

                try:
                    await bot.send_message(
                        chat_id=CHANNEL,
                        text=message,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
                    posted_links.add(link)
                    print("Опубликовано:", title)
                except Exception as e:
                    print("Ошибка отправки:", e)

                delay = random.randint(MIN_DELAY, MAX_DELAY)
                await asyncio.sleep(delay)

        await asyncio.sleep(60)

def start_bot():
    asyncio.run(rss_loop())

# ================== ЗАПУСК ==================

if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
