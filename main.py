import os
import json
import random
import requests
import tweepy
import datetime
import uuid  # For unique ID
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

# --- 1. CONFIGURATION ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")

HISTORY_FILE = "posted_news.txt"

# --- 2. AI SUMMARIZER ---
def get_ai_summary(title, description):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"Summarize in 2 sentences for a news brand: {title}. Context: {description}"
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ AI failed: {e}")
        return description[:250] if description else "Latest update from Infochowk."

# --- 3. DEDUPLICATION ---
def has_been_posted(news_url):
    if not os.path.exists(HISTORY_FILE): return False
    with open(HISTORY_FILE, "r") as f:
        return news_url in f.read().splitlines()

def mark_as_posted(news_url):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{news_url}\n")

# --- 4. NEWS FETCH ---
def fetch_news():
    search_queries = [
        {"type": "top", "params": {"country": "in", "category": "technology"}},
        {"type": "top", "params": {"country": "in", "category": "general"}},
        {"type": "everything", "params": {"q": "(AI OR tesla OR space OR crypto)", "language": "en", "sortBy": "relevancy"}}
    ]
    for query in search_queries:
        endpoint = "top-headlines" if query["type"] == "top" else "everything"
        url = f"https://newsapi.org/v2/{endpoint}"
        try:
            params = query["params"].copy()
            params["apiKey"] = NEWS_API_KEY
            res = requests.get(url, params=params).json()
            if res.get("status") == "ok":
                articles = res.get("articles", [])
                random.shuffle(articles)
                for article in articles:
                    if not has_been_posted(article['url']) and article.get('urlToImage') and article.get('description'):
                        article['is_india'] = query["params"].get("country") == "in"
                        return article
        except Exception as e:
            print(f"⚠️ Stage failed: {e}")
    return None

# --- 5. BROADCAST ---
def broadcast(article):
    title = article['title']
    link = article['url']
    img = article['urlToImage']
    src = article['source']['name']
    ai_summary = get_ai_summary(title, article['description'])
    
    # --- TELEGRAM ---
    badge = "🇮🇳 <b>INDIA UPDATE</b>" if article.get('is_india') else "🌎 <b>GLOBAL TRENDING</b>"
    tg_text = f"{badge}\n🔥 <b>{title.upper()}</b>\n📰 <b>Source:</b> {src}\n━━━━━━━━━━━━━━━━━━\n\n🎙 <i>{ai_summary}</i>"
    markup = {"inline_keyboard": [[{"text": "📖 Read Full Story", "url": link}]]}
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto", data={
            'chat_id': TG_CHAT_ID, 'photo': img, 'caption': tg_text,
            'parse_mode': 'HTML', 'reply_markup': json.dumps(markup)
        })
        print("✅ Telegram: Success")
    except Exception as e: print(f"❌ Telegram Error: {e}")

    # --- X THREAD ---
    try:
        client = tweepy.Client(
            consumer_key=X_API_KEY, consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET
        )
        
        # Unique ID prevents 403 Duplicate Content errors
        unique_id = str(uuid.uuid4())[:4]
        timestamp = datetime.datetime.now().strftime("%H:%M")
        
        # Main Tweet (Limit headline to fit)
        tweet_1_text = f"🚨 {title[:200]}\n\n📰 Source: {src}\n🕒 {timestamp} | ID: {unique_id}"
        t1 = client.create_tweet(text=tweet_1_text)
        
        # Reply Tweet
        client.create_tweet(
            text=f"🎙 Summary: {ai_summary[:200]}\n\n🔗 Read: {link}",
            in_reply_to_tweet_id=t1.data['id']
        )
        print("✅ X: Thread Success")
    except Exception as e:
        print(f"❌ X Error: {e}")

if __name__ == "__main__":
    print("🛰️ Infochowk Engine Online...")
    news = fetch_news()
    if news:
        broadcast(news)
        mark_as_posted(news['url'])
    else: print("📭 No fresh stories found.")
