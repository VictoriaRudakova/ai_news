# AI News Telegram Bot

A small Flask-based service that collects the latest AI-related news from Ukrainian tech media and sends them to a Telegram chat.

The project uses NewsAPI to search for AI news, filters relevant articles, formats them into a readable message, and sends the result through the Telegram Bot API.

## About the Project

This project was created as a simple automation tool for tracking AI news.

The bot searches for news related to:

- Artificial Intelligence
- ШІ
- OpenAI
- ChatGPT
- Anthropic
- Gemini
- Copilot
- LLM
- Machine Learning
- Neural networks

The current version focuses on Ukrainian tech/media sources.

## Features

- Fetches AI-related news from NewsAPI
- Filters articles by keywords
- Uses Ukrainian tech domains as sources
- Removes duplicate articles
- Sorts news by publication date
- Sends formatted news to Telegram
- Has a manual trigger endpoint
- Can be deployed on Render

## Tech Stack

- Python 3
- Flask
- Requests
- Gunicorn
- NewsAPI
- Telegram Bot API
- Render

## Project Structure

```text
ai_news/
│
├── app.py              # Main Flask application and bot logic
├── requirements.txt    # Python dependencies
└── render.yaml         # Render deployment configuration
```

## How It Works

1. The service receives a request on the `/run` endpoint.
2. It checks the secret key from the request.
3. It sends a request to NewsAPI.
4. It searches for AI-related articles from selected Ukrainian sources.
5. It filters irrelevant or duplicate articles.
6. It formats the result into a Telegram message.
7. It sends the message to the configured Telegram chat.

## API Endpoints

### Home

```http
GET /
```

Returns basic information that the service is running.

### Health Check

```http
GET /health
```

Returns service health status.

Example response:

```json
{
  "ok": true
}
```

### Run Bot

```http
GET /run?key=YOUR_SECRET
```

Manually triggers news fetching and sends the message to Telegram.

The `key` value must match the `RUN_SECRET` environment variable.

## Environment Variables

The project requires the following environment variables:

| Variable | Description |
|---|---|
| `NEWS_API_KEY` | API key from NewsAPI |
| `TELEGRAM_BOT_TOKEN` | Token of the Telegram bot |
| `TELEGRAM_CHAT_ID` | ID of the Telegram chat where messages will be sent |
| `RUN_SECRET` | Secret key used to protect the manual trigger endpoint |
| `PAGE_SIZE` | Optional number of articles requested from NewsAPI |
| `MAX_ARTICLES` | Optional maximum number of articles sent to Telegram |

## Local Setup

1. Clone the repository:

```bash
git clone https://github.com/VictoriaRudakova/ai_news.git
```

2. Open the project folder:

```bash
cd ai_news
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set environment variables.

Example for Windows PowerShell:

```powershell
$env:NEWS_API_KEY="your_news_api_key"
$env:TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
$env:TELEGRAM_CHAT_ID="your_telegram_chat_id"
$env:RUN_SECRET="your_secret_key"
```

Example for macOS / Linux:

```bash
export NEWS_API_KEY="your_news_api_key"
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export TELEGRAM_CHAT_ID="your_telegram_chat_id"
export RUN_SECRET="your_secret_key"
```

5. Run the application:

```bash
python app.py
```

The service will start locally.

## Usage

Open the manual trigger endpoint in the browser:

```text
http://localhost:10000/run?key=your_secret_key
```

If everything is configured correctly, the bot will fetch AI news and send them to Telegram.

## Deployment on Render

The repository includes `render.yaml`, so the project can be deployed as a Render web service.

Required environment variables on Render:

- `NEWS_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `RUN_SECRET`

After deployment, the bot can be triggered manually:

```text
https://your-render-service-url.onrender.com/run?key=your_secret_key
```

## Example Telegram Message

```text
Останні новини про ШІ в українських медіа

1. Article title
Джерело: Source name
Опубліковано: 2026-06-11T10:00:00Z
Article description

Читати далі

#ШІ #новини #AI
```

## Current Status

The project is a simple manual-trigger AI news bot.

It does not run on a schedule by itself yet.  
To send news, the `/run` endpoint should be opened manually or triggered by an external scheduler.

## Future Improvements

Possible improvements:

- Add automatic scheduled posting
- Add more Ukrainian and international sources
- Add better article filtering
- Add summary generation with an LLM
- Add topic categories
- Add error notifications to Telegram
- Add tests for the main functions
- Add logging improvements
- Add Docker support
- Add GitHub Actions workflow
