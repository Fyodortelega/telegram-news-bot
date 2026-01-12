import os
import asyncio
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import xml.etree.ElementTree as ET
from telegram import Bot
import re

# ================= НАСТРОЙКИ =================

TOKEN = os.getenv("TOKEN")
CHANNEL = os.getenv("CHANNEL")
PORT = int(os.getenv("PORT", 10000))

RSS_LIST = [
    "https://lenta.ru/rss"
]

POSTED_FILE = "posted.txt"

bot = Bot(token=TOKEN)

# ================= WEB SERVER (для Render) =================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"News bot is running")

def run_server():
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

# ================= ДИЗАЙН =================

def pick_emoji(title):
    t = title.lower()

    if any(w in t for w in ["срочно", "экстр", "важно"]):
        return "🚨⚡"
    if any(w in t for w in ["убийств", "дтп", "пожар", "взрыв", "криминал"]):
        return "🚔🚨"
    if any(w in t for w in ["снег", "зима", "мороз", "метель"]):
        return "☃️❄️"
    if any(w in t for w in ["путин", "закон", "дума", "правительств"]):
        return "🏛"
    if any(w in t for w in ["сша", "европа", "мир", "украин"]):
        return "🌍"

    return "📰"

def pick_hashtags(title):
    t = title.lower()
    tags = []

    if any(w in t for w in ["срочно", "экстр"]):
        tags.append("#срочно")
    if any(w in t for w in ["снег", "зима"]):
        tags.append("#погода")
    if any(w in t for w in ["убийств", "дтп", "пожар", "криминал"]):
        tags.append("#криминал")
    if any(w in t for w in ["путин", "дума", "закон"]):
        tags.append("#политика")
    if any(w in t for w in ["мир", "сша", "европа"]):
        tags.append("#мир")

    if not tags:
        tags.append("#новости")

    return " ".join(tags)

# ================= RSS =================

def load_posted():
    if not os.path.exists(POSTED_FILE):
        return set()
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_posted(url):
    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

async def check_and_post():
    posted = load_posted()

    for rss in RSS_LIST:
        resp = requests.get(rss, timeout=10)
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:5]

        for item in items:
            title = item.findtext("title")
            link = item.findtext("link")
            description = item.findtext("description") or ""

            if description:
                # удаляем HTML теги
                description = re.sub("<[^<]+?>", "", description)
                if len(description) > 300:
                    description = description[:300] + "..."

            if not title or not link or link in posted:
                continue

            emoji = pick_emoji(title)
            tags = pick_hashtags(title)
            time_now = datetime.now().strftime("%H:%M")

            text = (
                f"{emoji} <b>{title}</b>\n\n"
                f"{description}\n\n"
                f"🕒 {time_now}\n"
                f"Источник: <a href=\"{link}\">ссылка</a>\n\n"
                f"{tags}"
            )

            enclosure = item.find("enclosure")
            image_url = enclosure.attrib.get("url") if enclosure is not None else None

            try:
                if image_url:
                    img = requests.get(image_url)
                    if img.status_code == 200:
                        await bot.send_photo(
                            CHANNEL,
                            img.content,
                            caption=text,
                            parse_mode="HTML"
                            )
                    else:
                        await bot.send_message(
                            CHANNEL,
                            text,
                            parse_mode="HTML",
                            disable_web_page_preview=True
                        )
                else:
                    await bot.send_message(
                        CHANNEL,
                        text,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )

                save_posted(link)
                posted.add(link)
                print("Опубликовано:", title)

            except Exception as e:
                print("Ошибка:", e)

# ================= LOOP =================

async def bot_loop():
    if not os.path.exists("started.flag"):
        await bot.send_message(
            CHANNEL,
            "✅ Новостной бот запущен и работает автоматически"
        )
        open("started.flag", "w").close()

    while True:
        await check_and_post()
        await asyncio.sleep(600)  # каждые 10 минут

# ================= START =================

if name == "main":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(bot_loop())
