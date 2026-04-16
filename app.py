import os
import html
import traceback
from datetime import datetime, timezone
from typing import Any

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

NEWS_API_URL = "https://newsapi.org/v2/everything"

# Українські тех/AI-джерела
UKRAINIAN_AI_DOMAINS = [
    "dev.ua",
    "dou.ua",
    "ain.ua",
]

# Ключові слова для пошуку AI-новин
AI_QUERY = (
    '("штучний інтелект" OR ШІ OR AI OR OpenAI OR Anthropic OR Gemini '
    'OR ChatGPT OR Copilot OR LLM OR "машинне навчання" OR нейромережі)'
)


def get_env(name: str, required: bool = True) -> str:
    value = os.environ.get(name, "").strip()
    if required and not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def get_env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise RuntimeError(f"Environment variable {name} must be an integer") from e


def get_config() -> dict[str, Any]:
    return {
        "NEWS_API_KEY": get_env("NEWS_API_KEY"),
        "TELEGRAM_BOT_TOKEN": get_env("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHAT_ID": get_env("TELEGRAM_CHAT_ID"),
        "RUN_SECRET": get_env("RUN_SECRET"),
        "PAGE_SIZE": get_env_int("PAGE_SIZE", 20),
        "MAX_ARTICLES": get_env_int("MAX_ARTICLES", 5),
    }


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)

    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def fetch_ai_news(news_api_key: str, page_size: int, max_articles: int) -> list[dict]:
    params = {
        "q": AI_QUERY,
        "domains": ",".join(UKRAINIAN_AI_DOMAINS),
        "searchIn": "title,description,content",
        "sortBy": "publishedAt",
        "language": "uk",
        "pageSize": page_size,
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

    articles: list[dict] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for item in data.get("articles", []):
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        description = (item.get("description") or "").strip()
        content = (item.get("content") or "").strip()
        published_at = (item.get("publishedAt") or "").strip()
        source = (item.get("source") or {}).get("name", "").strip()
        source_name = source or "Unknown source"

        if not title or not url:
            continue

        title_key = title.lower()
        if url in seen_urls or title_key in seen_titles:
            continue

        text_blob = " ".join([title.lower(), description.lower(), content.lower()])

        # Додатковий захист від нерелевантних новин
        if not any(
            keyword in text_blob
            for keyword in [
                "штучний інтелект",
                " ші",
                " ai",
                "openai",
                "anthropic",
                "gemini",
                "chatgpt",
                "copilot",
                "llm",
                "машинне навчання",
                "нейромереж",
            ]
        ):
            continue

        seen_urls.add(url)
        seen_titles.add(title_key)

        articles.append(
            {
                "title": title,
                "url": url,
                "source": source_name,
                "description": description,
                "published_at": published_at,
            }
        )

    articles.sort(key=lambda x: parse_date(x["published_at"]), reverse=True)
    return articles[:max_articles]


def format_message(articles: list[dict]) -> str:
    lines = [
        "<b>Останні новини про ШІ в українських медіа</b>",
        "",
    ]

    for index, article in enumerate(articles, start=1):
        title = html.escape(article["title"])
        source = html.escape(article["source"])
        url = html.escape(article["url"])
        published_at = html.escape(article["published_at"])
        description = html.escape(article["description"][:300]) if article["description"] else ""

        lines.append(f"{index}. <b>{title}</b>")
        lines.append(f"Джерело: {source}")
        if published_at:
            lines.append(f"Опубліковано: {published_at}")
        if description:
            lines.append(description)
        lines.append(f'<a href="{url}">Читати далі</a>')
        lines.append("")

    lines.append("#ШІ #новини #AI")
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
    return jsonify(
        {
            "ok": True,
            "message": "Service is running. Open /run?key=YOUR_SECRET to trigger posting.",
            "domains": UKRAINIAN_AI_DOMAINS,
        }
    )


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/run")
def run_bot():
    try:
        config = get_config()

        key = request.args.get("key", "").strip()
        if key != config["RUN_SECRET"]:
            return jsonify(
                {
                    "ok": False,
                    "error": "unauthorized",
                }
            ), 401

        articles = fetch_ai_news(
            news_api_key=config["NEWS_API_KEY"],
            page_size=config["PAGE_SIZE"],
            max_articles=config["MAX_ARTICLES"],
        )

        if not articles:
            return jsonify(
                {
                    "ok": True,
                    "posted": 0,
                    "message": "Не знайдено новин за заданими українськими джерелами",
                    "domains": UKRAINIAN_AI_DOMAINS,
                }
            )

        message = format_message(articles)
        telegram_result = send_to_telegram(
            config["TELEGRAM_BOT_TOKEN"],
            config["TELEGRAM_CHAT_ID"],
            message,
        )

        return jsonify(
            {
                "ok": True,
                "posted": len(articles),
                "domains": UKRAINIAN_AI_DOMAINS,
                "articles": articles,
                "telegram_result": telegram_result,
            }
        )

    except Exception as e:
        tb = traceback.format_exc()
        print("ERROR:", tb)
        return jsonify(
            {
                "ok": False,
                "error": str(e),
                "traceback": tb,
            }
        ), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)