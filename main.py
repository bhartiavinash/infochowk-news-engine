import os
import json
import requests
import tweepy
from dotenv import load_dotenv

# Force reload environment variables
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
    if not os.path.exists(HISTORY_FILE): return False
    with open(HISTORY_FILE, "r") as f:
        return news_url in f.read().splitlines()

def mark_as_posted(news_url):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{news_url}\n")

# --- 3. NEWS FETCHING ---
def fetch_news():
    """Fetches news and returns the first unposted article with an image."""
    endpoints = [
        f"https://newsapi.org/v2/top-headlines?country=in&category=technology&apiKey={NEWS_API_KEY}",
        f"https://newsapi.org/v2/everything?q=technology&language=en&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
    ]
    
    for url in endpoints:
        try:
            res = requests.get(url).json()
            if res.get("status") == "ok":
                for article in res.get("articles", []):
                    # We prefer articles that have an image for the new layout
                    if not has_been_posted(article['url']) and article.get('urlToImage'):
                        return article
        except Exception as e:
            print(f"⚠️ Fetch Error: {e}")
    return None

# --- 4. BROADCASTING ---
def broadcast(title, link, desc, image_url):
    """Sends news as a Photo with Caption to Telegram and Text to X."""
    
    # --- A. TELEGRAM (Photo + Caption + Button) ---
    tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    
    # Styled HTML Caption
    caption = (
        f"🚨 <b>{title.upper()}</b>\n\n"
        f"🎙 <i>{desc[:250]}...</i>\n\n"
        f"📡 @Infochowk #TechNews"
    )
    
    # Inline keyboard for the button
    reply_markup = {
        "inline_keyboard": [[
            {"text": "📖 Read Full Story", "url": link}
        ]]
    }
    
    tg_payload = {
        'chat_id': TG_CHAT_ID,
        'photo': image_url, # Sends the image URL directly
        'caption': caption,
        'parse_mode': 'HTML',
        'reply_markup': json.dumps(reply_markup)
    }
    
    try:
        tg_res = requests.post(tg_url, data=tg_payload)
        if tg_res.status_code == 200:
            print("✅ Telegram: Photo Post Successful")
        else:
            # Fallback to text message if image fails
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          data={'chat_id': TG_CHAT_ID, 'text': caption, 'parse_mode': 'HTML'})
            print("⚠️ Telegram: Image failed, sent text fallback")
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
        x_text = f"🚨 {title}\n\nRead more: {link}\n\n#Infochowk #Tech"
        client.create_tweet(text=x_text) # Simple text post for X
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
            article['description'] or "Check out the latest tech news.",
            article['urlToImage']
        )
        mark_as_posted(article['url'])
    else:
        print("📭 No new updates with images found.")
