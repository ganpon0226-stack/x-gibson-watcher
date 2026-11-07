import os
import json
import feedparser
import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
# 監視したい店舗アカウント（例：GibsonJapan や 楽器店のアカウント）
TARGET_USERNAME = "GibsonJapan" 
STATE_FILE = "watched_tweets.json"
KEYWORDS = ["gibson", "ギブソン", "tak", "レスポール", "les paul"]

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"seen_ids": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_discord(tweet):
    if not DISCORD_WEBHOOK_URL:
        return
    payload = {
        "content": f"🚨 **【最速検知】新着ポスト検出**\n**@{tweet['author']}**: {tweet['link']}\n```{tweet['text'][:250]}```"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def fetch_tweets_via_rsshub(username):
    # RSSHub等の公開パブリックインスタンスを利用して、純粋なツイートRSSを取得
    # これによりプロフィールや余計なヘッダーが一切入らなくなります
    rss_url = f"https://rsshub.app/twitter/user/{username}"
    print(f"[DEBUG] RSS取得URL: {rss_url}")
    
    feed = feedparser.parse(rss_url)
    parsed_tweets = []
    
    for entry in feed.entries:
        # ツイートのユニークIDとリンク、本文をダイレクトに取得
        t_id = entry.get("id", entry.get("link", ""))
        text = entry.get("title", entry.get("summary", ""))
        link = entry.get("link", "")
        
        if t_id and text:
            parsed_tweets.append({
                "id": t_id,
                "author": username,
                "text": text,
                "link": link
            })
            
    return parsed_tweets

def main():
    print("=== [DEBUG] X Watcher (RSSHub Direct Matcher) 起動 ===")
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    try:
        tweets = fetch_tweets_via_rsshub(TARGET_USERNAME)
        print(f"[DEBUG] 取得したツイート数: {len(tweets)} 件")
        
        new_seen_ids = list(seen_ids)
        
        for tweet in tweets:
            tweet_id = tweet["id"]
            if tweet_id in seen_ids:
                continue
            
            text_lower = tweet["text"].lower()
            if any(kw in text_lower for kw in KEYWORDS):
                print(f"[MATCH] キーワード検出！ 通知送信: {tweet['link']}")
                send_discord(tweet)
            
            new_seen_ids.append(tweet_id)
            
        state["seen_ids"] = new_seen_ids[-500:]
    except Exception as e:
        print(f"[ERROR] 取得または解析エラー: {e}")
    finally:
        save_state(state)
        print("[DEBUG] 状態保存完了")

if __name__ == "__main__":
    main()
