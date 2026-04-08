import os
import html
import traceback
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

NEWS_API_URL = "https://newsapi.org/v2/everything"


def get_env(name: str, required: bool = True) -> str:
    value = os.environ.get(name, "").strip()
    if required and not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def get_config():
    return {
        "NEWS_API_KEY": get_env("NEWS_API_KEY"),
        "TELEGRAM_BOT_TOKEN": get_env("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHAT_ID": get_env("TELEGRAM_CHAT_ID"),
        "RUN_SECRET": get_env("RUN_SECRET"),
    }


def fetch_ai_news(news_api_key: str) -> list[dict]:
    params = {
        "q": '(AI OR "artificial intelligence" OR OpenAI OR Anthropic OR Gemini OR LLM OR "machine learning")',
        "sortBy": "publishedAt",
        "pageSize": 10,
        "apiKey": news_api_key,
    }

    response = requests.get(NEWS_API_URL, params=params, timeout=30)

    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text}

    print("NEWS STATUS:", response.status_code)
    print("NEWS RAW RESPONSE:", data)

    if response.status_code != 200:
        raise RuntimeError(f"News API error: {data}")

    if data.get("status") != "ok":
        raise RuntimeError(f"News API returned bad status: {data}")

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


def format_message(articles: list[dict]) -> str:
    lines = [
        "<b>AI news digest</b>",
        "",
    ]

    for index, article in enumerate(articles, start=1):
        title = html.escape(article["title"])
        source = html.escape(article["source"])
        url = html.escape(article["url"])
        description = html.escape(article["description"][:220]) if article["description"] else ""

        lines.append(f"{index}. <b>{title}</b>")
        lines.append(f"Source: {source}")
        if description:
            lines.append(description)
        lines.append(f'<a href="{url}">Read more</a>')
        lines.append("")

    lines.append("#AI #news")
    return "\n".join(lines)


def send_to_telegram(bot_token: str, chat_id: str, text: str) -> dict:
    telegram_send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    response = requests.post(telegram_send_url, json=payload, timeout=30)

    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text}

    print("TELEGRAM STATUS:", response.status_code)
    print("TELEGRAM RAW RESPONSE:", data)

    if response.status_code != 200:
        raise RuntimeError(f"Telegram API error: {data}")

    if not data.get("ok"):
        raise RuntimeError(f"Telegram API returned bad status: {data}")

    return data


@app.get("/")
def home():
    return jsonify({
        "ok": True,
        "message": "Service is running. Open /run?key=YOUR_SECRET to trigger posting."
    })


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/run")
def run_bot():
    try:
        config = get_config()

        key = request.args.get("key", "").strip()
        if key != config["RUN_SECRET"]:
            return jsonify({
                "ok": False,
                "error": "unauthorized"
            }), 401

        articles = fetch_ai_news(config["NEWS_API_KEY"])

        if not articles:
            return jsonify({
                "ok": True,
                "posted": 0,
                "message": "No articles found"
            })

        message = format_message(articles)
        telegram_result = send_to_telegram(
            config["TELEGRAM_BOT_TOKEN"],
            config["TELEGRAM_CHAT_ID"],
            message,
        )

        return jsonify({
            "ok": True,
            "posted": len(articles),
            "articles": articles,
            "telegram_result": telegram_result,
        })

    except Exception as e:
        tb = traceback.format_exc()
        print("ERROR:", tb)
        return jsonify({
            "ok": False,
            "error": str(e),
            "traceback": tb,
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)