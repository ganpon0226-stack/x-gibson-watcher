import os
import json
import requests
import feedparser

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
# 監視したいアカウント名（例: GibsonJapan）
TARGET_USERNAME = "GibsonJapan"
STATE_FILE = "watched_tweets.json"
KEYWORDS = ["gibson", "ギブソン", "tak"]

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
        print("[WARNING] DISCORD_WEBHOOK_URL が設定されていません。")
        return
    payload = {
        "content": f"🎸 **Gibson関連ポスト**\n**{tweet['author']}**: {tweet['link']}\n```{tweet['text'][:200]}```"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def fetch_tweets_via_rss(username):
    # より安定している別のパブリックRSSプロキシ経由で取得
    rss_url = f"https://r.jina.ai/https://x.com/{username}"
    print(f"[DEBUG] 取得URL: {rss_url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(rss_url, headers=headers, timeout=15)
    
    parsed_tweets = []
    if response.status_code == 200:
        text_content = response.text
        # 簡易的にテキスト行を解析、またはそのまま解析対象にする
        # テキストの中にキーワードが含まれているかを直接判定できるようにリスト化します
        parsed_tweets.append({
            "id": username + "_timeline",
            "author": username,
            "text": text_content,
            "link": f"https://x.com/{username}"
        })
        
    return parsed_tweets
    
def main():
    print("=== [DEBUG] X Watcher (RSS Feed) 起動 ===")
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    try:
        print(f"[DEBUG] アカウント @{TARGET_USERNAME} のフィードを取得中...")
        tweets = fetch_tweets_via_rss(TARGET_USERNAME)
        print(f"[DEBUG] 取得成功！ 件数: {len(tweets)} 件")
        
        if tweets:
            print(f"[DEBUG] 最新ポスト: {tweets[0]['text'][:50]}...")

        new_seen_ids = list(seen_ids)
        
        for tweet in reversed(tweets):
            tweet_id = tweet["id"]
            text = tweet["text"]
            
            if tweet_id in seen_ids:
                continue
            
            text_lower = text.lower()
            if any(kw in text_lower for kw in KEYWORDS):
                print(f"[MATCH] キーワード検出！ 通知送信: {tweet['link']}")
                send_discord(tweet)
            
            new_seen_ids.append(tweet_id)
            
        state["seen_ids"] = new_seen_ids[-500:]
        
    except Exception as e:
        print(f"[ERROR] RSS取得または解析エラー: {e}")
    finally:
        save_state(state)
        print("[DEBUG] 状態保存完了")

if __name__ == "__main__":
    main()
