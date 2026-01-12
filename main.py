import os
import asyncio
import requests
import xml.etree.ElementTree as ET
from telegram import Bot

TOKEN = os.getenv("TOKEN")
CHANNEL = os.getenv("CHANNEL")

if not TOKEN or not CHANNEL:
    print("❌ Переменные окружения пустые!")
    exit(1)

bot = Bot(token=TOKEN)

RSS_LIST = [
    "https://lenta.ru/rss"
]

POSTED_FILE = "posted.txt"

def load_posted():
    if not os.path.exists(POSTED_FILE):
        return set()
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_posted(url):
    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

async def check_and_post():
    posted_urls = load_posted()

    for rss_url in RSS_LIST:
        resp = requests.get(rss_url, timeout=10)
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:5]

        for item in items:
            title = item.findtext("title")
            link = item.findtext("link")

            if not title or not link or link in posted_urls:
                continue

            text = f"{title}\n{link}"

            image_url = None
            enclosure = item.find("enclosure")
            if enclosure is not None:
                image_url = enclosure.attrib.get("url")

            try:
                if image_url:
                    img = requests.get(image_url)
                    if img.status_code == 200:
                        await bot.send_photo(
                            chat_id=CHANNEL,
                            photo=img.content,
                            caption=text
                        )
                    else:
                        await bot.send_message(chat_id=CHANNEL, text=text)
                else:
                    await bot.send_message(chat_id=CHANNEL, text=text)

                save_posted(link)
                posted_urls.add(link)
                print("Опубликовано:", title)

            except Exception as e:
                print("Ошибка отправки:", e)

async def main_loop():
    if not os.path.exists("sent.flag"):
        await bot.send_message(
            chat_id=CHANNEL,
            text="✅ Бот запущен и работает 24/7 (Render Free)"
        )
        open("sent.flag", "w").close()

    while True:
        await check_and_post()
        await asyncio.sleep(600)  # каждые 10 минут

asyncio.run(main_loop())
