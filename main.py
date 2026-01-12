import os
import asyncio
import random
import threading
import time
import hashlib
import feedparser
import requests
from flask import Flask
from telegram import Bot
from bs4 import BeautifulSoup

# ================= НАСТРОЙКИ =================

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL = os.environ.get("CHANNEL_ID")

RSS_FEEDS = [
    "https://www.vedomosti.ru/rss/news",
    "https://life.ru/xml/news",
    "https://www.gazeta.ru/export/rss",
    "https://lenta.ru/rss",
]

MIN_DELAY = 10   # 5 минут
MAX_DELAY = 100   # 15 минут

posted_hashes = set()

# ================= TELEGRAM =================

bot = Bot(token=TOKEN)

# ================= FLASK ====================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

# ================= УТИЛИТЫ ==================

def hash_title(title: str) -> str:
    return hashlib.md5(title.lower().encode()).hexdigest()

def clean_text(text: str) -> str | None:
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text(" ", strip=True)

    trash_words = [
        "Реклама",
        "Фото:",
        "Источник:",
        "Читайте также",
        "Подписывайтесь",
    ]

    for t in trash_words:
        text = text.replace(t, "")

    text = text.strip()

    if len(text) < 80:
        return None

    # НЕ обрываем предложения
    sentences = text.split(". ")
    result = ""

    for s in sentences:
        if len(result) + len(s) <= 600:
            result += s + ". "
        else:
            break

    return result.strip()

# ============ ПАРСИНГ СТРАНИЦ ===============

def fetch_text_from_page(url: str) -> str | None:
    try:
        r = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        soup = BeautifulSoup(r.text, "html.parser")

        # РИА
        if "ria.ru" in url:
            blocks = soup.select("div.article__body p")

        # Коммерсант
        elif "kommersant.ru" in url:
            blocks = soup.select("div.article_text_wrapper p")

        # ТАСС
        elif "tass.ru" in url:
            blocks = soup.select("div.text-block p")

        else:
            blocks = soup.find_all("p")

        text = ""
        for p in blocks:
            t = p.get_text(strip=True)

            if not t:
                continue
            if any(x in t for x in ["Реклама", "Фото:", "ТАСС,"]):
                continue

            if len(text) + len(t) > 700:
                break

            text += t + " "

        return text.strip() if len(text) > 80 else None

    except Exception as e:
        print("Ошибка парсинга страницы:", e)
        return None

# ============ ПОЛУЧЕНИЕ ТЕКСТА ===============

def get_entry_text(entry):
    # 1️⃣ пробуем RSS
    if hasattr(entry, "content"):
        text = clean_text(entry.content[0].value)
        if text:
            return text

    if entry.get("summary"):
        text = clean_text(entry.summary)
        if text:
            return text

    # 2️⃣ идём на сайт
    link = entry.get("link")
    if link:
        return fetch_text_from_page(link)

    return None

# ================= ЭМОДЗИ ===================

def pick_emoji(title: str) -> str:
    t = title.lower()
    if "срочно" in t or "экстр" in t:
        return "🚨"
    if "кримин" in t or "убийств" in t:
        return "🚔"
    if "снег" in t or "зима" in t:
        return "☃️"
    if "эконом" in t:
        return "💰"
    return "📰"

# ============ ОСНОВНОЙ ЦИКЛ ==================

async def rss_loop():
    print("Бот запущен")

    while True:
        random.shuffle(RSS_FEEDS)

        for feed_url in RSS_FEEDS:
            feed = feedparser.parse(feed_url)

for entry in feed.entries:
    title = entry.get("title")
    link = entry.get("link")

    if not title or not link:
        continue

    title_hash = hash_title(title)
    if title_hash in posted_hashes:
        continue

    text = None
    try:
        text = get_entry_text(entry)
    except Exception as e:
        print("Ошибка получения текста:", e)

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

        posted_hashes.add(title_hash)
        print("Опубликовано:", title)

    except Exception as e:
        print("Ошибка отправки:", e)
        continue

    delay = random.randint(MIN_DELAY, MAX_DELAY)
    await asyncio.sleep(delay)

    await asyncio.sleep(60)

def start_bot():
    asyncio.run(rss_loop())

# ================= ЗАПУСК ===================

if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
