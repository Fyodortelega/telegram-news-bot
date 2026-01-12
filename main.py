import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import xml.etree.ElementTree as ET
from telegram import Bot
from bs4 import BeautifulSoup

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("TOKEN")
CHANNEL = os.getenv("CHANNEL")
PORT = int(os.getenv("PORT", 10000))

RSS_LIST = ["https://lenta.ru/rss"]
POSTED_FILE = "posted.txt"

bot = Bot(token=TOKEN)

# ================= WEB SERVER =================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"News bot is running")

def run_server():
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

# ================= КАТЕГОРИИ =================
CATEGORIES = {
    "срочно": {"emoji": "🚨⚡", "tag": "#срочно"},
    "криминал": {"emoji": "🚔", "tag": "#криминал"},
    "погода": {"emoji": "☃️❄️", "tag": "#погода"},
    "политика": {"emoji": "🏛", "tag": "#политика"},
    "мир": {"emoji": "🌍", "tag": "#мир"}
}

# ================= RSS =================
def load_posted():
    if not os.path.exists(POSTED_FILE):
        return set()
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_posted(url):
    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

# ================= ПАРСИНГ СТРАНИЦЫ =================
def get_summary_from_page(url, max_chars=300):
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")

        # основной текст новости
        content = soup.find("div", class_="topic__content")
        if not content:
            paragraphs = soup.find_all("p")
        else:
            paragraphs = content.find_all("p")

        text = ""
        for p in paragraphs:
            sentence = p.get_text().strip()

            # фильтруем ненужные абзацы
            lower = sentence.lower()
            if any(x in lower for x in [
                "реклама", "фото", "видео", "ссылка", "читайте также", "подпись к фото"
            ]):
                continue

            # добавляем предложение, только если оно полностью умещается
            if len(text) + len(sentence) + 1 > max_chars:
                break
            if sentence:
                if text:
                    text += " "
                text += sentence

        return text.strip()
    except Exception as e:
        print("Ошибка при парсинге страницы:", e)
        return ""

def categorize(title):
    t = title.lower()
    for keyword, data in CATEGORIES.items():
        if keyword in t:
            emoji = data["emoji"]
            tag = data["tag"]
            if keyword == "срочно":
                title = "⚡ " + title
            return emoji, tag, title
    return "📰", "#новости", title

# ================= ПУБЛИКАЦИЯ =================
async def check_and_post():
    posted = load_posted()
    for rss in RSS_LIST:
        try:
            resp = requests.get(rss, timeout=10)
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:5]
        except Exception as e:
            print("Ошибка RSS:", e)
            continue

        for item in items:
            title = item.findtext("title")
            link = item.findtext("link")

            if not title or not link or link in posted:
                continue

            description = get_summary_from_page(link)
            emoji, tag, title = categorize(title)

            text = (
                f"{emoji} <b>{title}</b>\n\n"
                f"{description}\n\n"
                f"Источник: <a href=\"{link}\">ссылка</a>\n\n"
                f"{tag}"
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
                print("Ошибка отправки:", e)

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
        await asyncio.sleep(600)

# ================= START =================
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(bot_loop())
