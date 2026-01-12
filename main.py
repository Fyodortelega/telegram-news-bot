import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import xml.etree.ElementTree as ET
from telegram import Bot

TOKEN = os.getenv("TOKEN")
CHANNEL = os.getenv("CHANNEL")
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=TOKEN)

RSS_LIST = [
    "https://lenta.ru/rss"
]

POSTED_FILE = "posted.txt"

# ---------- WEB SERVER (для Render) ----------

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()

# ---------- RSS BOT ----------

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

            if not title or not link or link in posted:
                continue

            text = f"{title}\n{link}"

            enclosure = item.find("enclosure")
            image_url = enclosure.attrib.get("url") if enclosure is not None else None

            try:
                if image_url:
                    img = requests.get(image_url)
                    if img.status_code == 200:
                        await bot.send_photo(CHANNEL, img.content, caption=text)
                    else:
                        await bot.send_message(CHANNEL, text)
                else:
                    await bot.send_message(CHANNEL, text)

                save_posted(link)
                posted.add(link)
                print("Опубликовано:", title)

            except Exception as e:
                print("Ошибка:", e)

async def bot_loop():
    if not os.path.exists("started.flag"):
        await bot.send_message(CHANNEL, "✅ Бот запущен и работает бесплатно 24/7")
        open("started.flag", "w").close()

    while True:
        await check_and_post()
        await asyncio.sleep(600)

# ---------- START ----------

if name == "main":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(bot_loop())
