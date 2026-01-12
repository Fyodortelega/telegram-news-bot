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

posted_urls = set()

async def fetch_and_post_once():
    for rss_url in RSS_LIST:
        try:
            resp = requests.get(rss_url, timeout=10)
            if resp.status_code != 200:
                print("Ошибка загрузки RSS")
                continue

            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:5]

            for item in items:
                title = item.findtext("title")
                link = item.findtext("link")

                if not title or not link or link in posted_urls:
                    continue

                text = f"{title}\n{link}"

                # Ищем картинку
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
                            print(f"Posted with image: {title}")
                        else:
                            await bot.send_message(chat_id=CHANNEL, text=text)
                    else:
                        await bot.send_message(chat_id=CHANNEL, text=text)

                except Exception as e:
                    print("Ошибка отправки:", e)

                posted_urls.add(link)

        except Exception as e:
            print("Ошибка RSS:", e)

async def main():
    # стартовое сообщение один раз
    if not os.path.exists("sent.flag"):
        await bot.send_message(chat_id=CHANNEL, text="✅ Бот запущен и публикует новости")
        open("sent.flag", "w").close()

    await fetch_and_post_once()

asyncio.run(main())
