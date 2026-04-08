import os
import html
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]   # наприклад: @my_ai_channel
RUN_SECRET = os.environ["RUN_SECRET"]

NEWS_API_URL = "https://newsapi.org/v2/everything"
TELEGRAM_SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def fetch_ai_news():
    if not NEWS_API_KEY:
        raise RuntimeError("NEWS_API_KEY is missing")

    now = datetime.now(timezone.utc)
    from_time = now - timedelta(hours=24)

    params = {
        "q": '(AI OR "artificial intelligence" OR OpenAI OR Anthropic OR Gemini OR LLM)',
        "language": "en",
        "sortBy": "publishedAt",
        "from": from_time.isoformat(),
        "pageSize": 10,
        "apiKey": NEWS_API_KEY,
    }

    resp = requests.get(NEWS_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    articles = []
    seen_titles = set()

    for item in data.get("articles", []):
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        source = (item.get("source") or {}).get("name", "").strip()
        description = (item.get("description") or "").strip()

        if not title or not url:
            continue

        normalized = title.lower()
        if normalized in seen_titles:
            continue
        seen_titles.add(normalized)

        articles.append({
            "title": title,
            "url": url,
            "source": source or "Unknown source",
            "description": description,
        })

    return articles[:3]


def format_message(articles):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "<b>AI news digest</b>",
        f"<i>Manual run: {html.escape(now)}</i>",
        "",
    ]

    for i, article in enumerate(articles, start=1):
        title = html.escape(article["title"])
        source = html.escape(article["source"])
        url = html.escape(article["url"])
        description = html.escape(article["description"][:180]) if article["description"] else ""

        lines.append(f"{i}. <b>{title}</b>")
        lines.append(f"Source: {source}")
        if description:
            lines.append(description)
        lines.append(f'<a href="{url}">Read more</a>')
        lines.append("")

    lines.append("#AI #news")
    return "\n".join(lines)


def send_to_telegram(text):
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    resp = requests.post(TELEGRAM_SEND_URL, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


@app.get("/")
def home():
    return jsonify({
        "ok": True,
        "message": "Service is running. Open /run?key=YOUR_SECRET to trigger posting."
    })


@app.get("/run")
def run_bot():
    key = request.args.get("key", "")
    if key != RUN_SECRET:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    try:
        articles = fetch_ai_news()

        if not articles:
            return jsonify({"ok": True, "posted": 0, "message": "No articles found"})

        text = format_message(articles)
        tg_result = send_to_telegram(text)

        return jsonify({
            "ok": True,
            "posted": len(articles),
            "articles": articles,
            "telegram_result": tg_result
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)