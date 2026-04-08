import os
import html
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ===== ENV VARS =====
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
RUN_SECRET = os.environ.get("RUN_SECRET", "")

NEWS_API_URL = "https://newsapi.org/v2/everything"
TELEGRAM_SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def validate_env():
    missing = []

    if not NEWS_API_KEY:
        missing.append("NEWS_API_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if not RUN_SECRET:
        missing.append("RUN_SECRET")

    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")


def fetch_ai_news():
    params = {
        "q": '(AI OR "artificial intelligence" OR OpenAI OR Anthropic OR Gemini OR LLM OR "machine learning")',
        "sortBy": "publishedAt",
        "pageSize": 10,
        "apiKey": NEWS_API_KEY,
    }

    response = requests.get(NEWS_API_URL, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    print("NEWSAPI RAW RESPONSE:", data)

    if data.get("status") != "ok":
        raise RuntimeError(f"News API error: {data}")

    articles = []
    seen_titles = set()

    for item in data.get("articles", []):
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        source = (item.get("source") or {}).get("name", "").strip()
        description = (item.get("description") or "").strip()

        if not title or not url:
            continue

        normalized_title = title.lower()
        if normalized_title in seen_titles:
            continue
        seen_titles.add(normalized_title)

        articles.append({
            "title": title,
            "url": url,
            "source": source or "Unknown source",
            "description": description,
        })

    return articles[:3]


def format_message(articles):
    lines = [
        "<b>AI news digest</b>",
        "",
    ]

    for index, article in enumerate(articles, start=1):
        title = html.escape(article["title"])
        source = html.escape(article["source"])
        url = html.escape(article["url"])
        description = html.escape(article["description"][:200]) if article["description"] else ""

        lines.append(f"{index}. <b>{title}</b>")
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

    response = requests.post(TELEGRAM_SEND_URL, json=payload, timeout=30)
    response.raise_for_status()

    data = response.json()
    print("TELEGRAM RAW RESPONSE:", data)

    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")

    return data


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
        return jsonify({
            "ok": False,
            "error": "unauthorized"
        }), 401

    try:
        validate_env()
        articles = fetch_ai_news()

        if not articles:
            return jsonify({
                "ok": True,
                "posted": 0,
                "message": "No articles found"
            })

        message = format_message(articles)
        telegram_result = send_to_telegram(message)

        return jsonify({
            "ok": True,
            "posted": len(articles),
            "articles": articles,
            "telegram_result": telegram_result
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)