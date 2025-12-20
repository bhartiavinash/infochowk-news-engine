import os
import requests
import tweepy
from dotenv import load_dotenv

load_dotenv(override=True)

# --- CONFIG ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")

HISTORY_FILE = "posted_news.txt"

def has_been_posted(news_url):
    if not os.path.exists(HISTORY_FILE): return False
    with open(HISTORY_FILE, "r") as f:
        return news_url in f.read().splitlines()

def mark_as_posted(news_url):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{news_url}\n")

def fetch_news():
    # Primary: Tech News; Fallback: General Business
    endpoints = [
        f"https://newsapi.org/v2/top-headlines?country=in&category=technology&apiKey={NEWS_API_KEY}",
        f"https://newsapi.org/v2/everything?q=technology&language=en&sortBy=publishedAt&pageSize=5&apiKey={NEWS_API_KEY}"
    ]
    for url in endpoints:
        res = requests.get(url).json()
        if res.get("status") == "ok" and res.get("totalResults", 0) > 0:
            for article in res["articles"]:
                if not has_been_posted(article['url']):
                    return article
    return None

def broadcast(title, link, desc):
    # Telegram Post
    tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    tg_text = f"🚨 <b>{title}</b>\n\n{desc[:200]}...\n\n🔗 <a href='{link}'>Full Story</a>"
    requests.post(tg_url, data={'chat_id': TG_CHAT_ID, 'text': tg_text, 'parse_mode': 'HTML'})
    
    # X Post (OAuth 1.0a User Context)
    try:
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET,
                               access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        client.create_tweet(text=f"🚨 {title}\n\nRead more: {link}\n\n#Infochowk #Tech")
        print("✅ Success: Broadcasted to X and Telegram")
    except Exception as e:
        print(f"❌ X Error: {e}")

if __name__ == "__main__":
    article = fetch_news()
    if article:
        broadcast(article['title'], article['url'], article['description'] or "")
        mark_as_posted(article['url'])
    else:
        print("📭 No new news found.")
