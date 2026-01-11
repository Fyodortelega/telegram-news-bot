import os
import asyncio
import requests
from bs4 import BeautifulSoup
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
                print(f"Ошибка загрузки RSS: {rss_url}")
                continue

            # Используем lxml для XML
            soup = BeautifulSoup(resp.content, "lxml-xml")
            items = soup.find_all("item")[:5]

            for item in items:
                link = item.find("link").text
                title = item.find("title").text

                if link in posted_urls:
                    continue

                text = f"{title}\n{link}"

                # Попытка получить картинку
                image_url = None
                enclosure = item.find("enclosure")
                if enclosure and enclosure.get("type", "").startswith("image"):
                    image_url = enclosure.get("url")

                try:
                    if image_url:
                        img_resp = requests.get(image_url)
                        if img_resp.status_code == 200:
                            await bot.send_photo(
                                chat_id=CHANNEL,
                                photo=img_resp.content,
                                caption=text
                            )
                            print(f"Posted with image: {title}")
                        else:
                            await bot.send_message(chat_id=CHANNEL, text=text)
                            print(f"Posted without image: {title}")
                    else:
                        await bot.send_message(chat_id=CHANNEL, text=text)
                        print(f"Posted without image: {title}")
                except Exception as e:
                    print(f"Ошибка публикации: {e}")

                posted_urls.add(link)
        except Exception as e:
            print(f"Ошибка при обработке RSS: {e}")

async def main():
    # стартовое сообщение
    if not os.path.exists("sent.flag"):
        await bot.send_message(chat_id=CHANNEL, text="✅ Бот запущен через Render Web Service!")
        with open("sent.flag", "w") as f:
            f.write("sent")

    await fetch_and_post_once()
    # больше не нужно закрывать bot.session

asyncio.run(main())
