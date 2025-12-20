import os
import json
import requests
import tweepy
from dotenv import load_dotenv

# Force reload environment variables for local testing
load_dotenv(override=True)

# --- 1. CONFIGURATION ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# X Credentials (OAuth 1.0a User Context)
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")

HISTORY_FILE = "posted_news.txt"

# --- 2. DEDUPLICATION LOGIC ---
def has_been_posted(news_url):
    """Checks if the URL is already in the history file."""
    if not os.path.exists(HISTORY_FILE):
        return False
    with open(HISTORY_FILE, "r") as f:
        return news_url in f.read().splitlines()

def mark_as_posted(news_url):
    """Adds the URL to the history file to prevent double-posting."""
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{news_url}\n")

# --- 3. NEWS FETCHING ---
def fetch_news():
    """Fetches the latest technology news from India or globally."""
    endpoints = [
        f"https://newsapi.org/v2/top-headlines?country=in&category=technology&apiKey={NEWS_API_KEY}",
        f"https://newsapi.org/v2/everything?q=technology&language=en&sortBy=publishedAt&pageSize=5&apiKey={NEWS_API_KEY}"
    ]
    
    for url in endpoints:
        try:
            res = requests.get(url).json()
            if res.get("status") == "ok" and res.get("totalResults", 0) > 0:
                for article in res["articles"]:
                    if not has_been_posted(article['url']):
                        return article
        except Exception as e:
            print(f"⚠️ Fetch Error: {e}")
            continue
    return None

# --- 4. BROADCASTING ---
def broadcast(title, link, desc):
    """Sends the news to Telegram (with Button) and X (OAuth 1.0a)."""
    
    # --- A. TELEGRAM (HTML + Inline Button) ---
    tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    
    # Professional Template
    tg_text = (
        f"🔥 <b>{title.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🎙 <i>{desc[:280]}...</i>\n\n"
        f"📡 @Infochowk #TechNews"
    )
    
    # Inline "Read More" Button
    reply_markup = {
        "inline_keyboard": [[
            {"text": "📖 Read Full Story", "url": link}
        ]]
    }
    
    tg_payload = {
        'chat_id': TG_CHAT_ID,
        'text': tg_text,
        'parse_mode': 'HTML',
        'reply_markup': json.dumps(reply_markup)
    }
    
    try:
        requests.post(tg_url, data=tg_payload)
        print("✅ Telegram: Posted with Template")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

    # --- B. X (Twitter) ---
    try:
        client = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_SECRET
        )
        
        # Simple text for X (no HTML allowed)
        x_text = f"🚨 {title}\n\nRead more: {link}\n\n#Infochowk #Tech"
        client.create_tweet(text=x_text)
        print("✅ X: Posted Successfully")
    except Exception as e:
        print(f"❌ X Error: {e}")

# --- 5. MAIN EXECUTION ---
if __name__ == "__main__":
    print("🛰️ Infochowk Engine Scanning for News...")
    article = fetch_news()
    
    if article:
        print(f"📰 New Story: {article['title']}")
        broadcast(
            article['title'], 
            article['url'], 
            article['description'] or "Stay updated with the latest in tech."
        )
        mark_as_posted(article['url'])
    else:
        print("📭 No new updates found at this time.")
