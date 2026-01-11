import os
import asyncio
import feedparser
import requests
from telegram import Bot, InputFile

TOKEN = os.getenv("TOKEN")
CHANNEL = os.getenv("CHANNEL")

# Проверяем переменные
if not TOKEN or not CHANNEL:
    print("❌ Переменные окружения пустые!")
    exit(1)

bot = Bot(token=TOKEN)

# Список RSS-каналов
RSS_LIST = [
    "https://lenta.ru/rss",  # добавляй сюда другие RSS по желанию
]

# Для предотвращения дублирования постов
posted_urls = set()

async def fetch_and_post():
    while True:
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

        await asyncio.sleep(600)  # проверяем каждые 10 минут

async def main():
    # Только один запуск для первого сообщения
    if not os.path.exists("sent.flag"):
        await bot.send_message(chat_id=CHANNEL, text="✅ Бот запущен и готов к автопостингу!")
        with open("sent.flag", "w") as f:
            f.write("sent")

    await fetch_and_post()
    await bot.session.close()

asyncio.run(main())
