import os
import json
import requests
import tweepy
from google_genai import genai  # NEW: Modern GenAI SDK
from dotenv import load_dotenv

load_dotenv(override=True)

# --- CONFIGURATION ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# X Credentials (OAuth 1.0a)
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")

HISTORY_FILE = "posted_news.txt"

# --- AI SUMMARIZER (Updated for google-genai) ---
def get_ai_summary(title, description):
    """Uses the latest Google GenAI SDK and Gemini 3 Flash."""
    try:
        # Initialize the new stateless client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = (
            f"Summarize this news in 2 engaging sentences for social media.\n"
            f"Title: {title}\n"
            f"Context: {description}"
        )
        
        # New API call structure
        response = client.models.generate_content(
            model='gemini-3-flash', # Latest high-speed frontier model
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ AI Summary failed: {e}")
        return description[:250] if description else "Latest tech update from Infochowk."

# --- DEDUPLICATION ---
def has_been_posted(news_url):
    if not os.path.exists(HISTORY_FILE): return False
    with open(HISTORY_FILE, "r") as f:
        return news_url in f.read().splitlines()

def mark_as_posted(news_url):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{news_url}\n")

# --- NEWS FETCHING ---
def fetch_news():
    url = f"https://newsapi.org/v2/top-headlines?country=in&category=technology&apiKey={NEWS_API_KEY}"
    try:
        res = requests.get(url).json()
        if res.get("status") == "ok":
            for article in res.get("articles", []):
                # We need a URL and an Image for the pro layout
                if not has_been_posted(article['url']) and article.get('urlToImage'):
                    return article
    except Exception as e:
        print(f"❌ Fetch Error: {e}")
    return None

# --- BROADCASTING ---
def broadcast(article):
    title = article['title']
    link = article['url']
    image_url = article['urlToImage']
    source = article['source']['name']
    
    # 1. Generate AI Content
    ai_summary = get_ai_summary(title, article['description'])

    # 2. TELEGRAM (Photo + AI Summary + Source Badge)
    tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    caption = (
        f"🚨 <b>{title.upper()}</b>\n"
        f"📰 <b>Source:</b> {source}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🎙 <i>{ai_summary}</i>\n\n"
        f"📡 @Infochowk #TechNews"
    )
    reply_markup = {"inline_keyboard": [[{"text": "📖 Read Full Story", "url": link}]]}
    
    try:
        requests.post(tg_url, data={
            'chat_id': TG_CHAT_ID,
            'photo': image_url,
            'caption': caption,
            'parse_mode': 'HTML',
            'reply_markup': json.dumps(reply_markup)
        })
        print("✅ Telegram: Posted Successfully")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

    # 3. X THREADING (Headline -> AI Summary -> Link)
    try:
        client = tweepy.Client(
            consumer_key=X_API_KEY, consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET
        )
        
        # Tweet 1: Headline & Source
        t1 = client.create_tweet(text=f"🚨 BREAKING: {title}\n\n📰 Source: {source}")
        
        # Tweet 2: AI Summary & Link (Threaded)
        client.create_tweet(
            text=f"🎙 Summary: {ai_summary}\n\n🔗 Read more: {link} #Infochowk",
            in_reply_to_tweet_id=t1.data['id']
        )
        print("✅ X: Thread Posted Successfully")
    except Exception as e:
        print(f"❌ X Error: {e}")

if __name__ == "__main__":
    print("🛰️ Infochowk Engine Starting...")
    news = fetch_news()
    if news:
        broadcast(news)
        mark_as_posted(news['url'])
    else:
        print("📭 No new stories found.")
