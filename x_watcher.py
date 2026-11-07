import os
import json
import requests
from ntscraper import Nitter

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
X_AUTH_TOKEN = os.environ.get("X_AUTH_TOKEN")
STATE_FILE = "watched_tweets.json"
KEYWORDS = ["gibson", "ギブソン"]

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"seen_ids": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_discord(tweet):
    payload = {
        "content": f"🎸 **Gibson新着ポスト**\n**{tweet['author']}**: {tweet['link']}\n```{tweet['text'][:200]}```"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def main():
    print("=== [DEBUG] X Watcher 起動 ===")
    
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    scraper = Nitter(log_level=1)
    
    try:
        print("[DEBUG] ツイート検索を試行中...")
        # ntscraperの検索機能を使って「gibson」や店舗関連の最新ポストを横断検索するアプローチ
        # （※リスト直指定ではなくキーワード横断で効率よく拾う形に変更）
        tweets_data = scraper.get_tweets("gibson", mode="term", number=30)
        
        tweets = tweets_data.get("tweets", [])
        print(f"[DEBUG] 取得成功！ 取得件数: {len(tweets)} 件")

        new_seen_ids = list(seen_ids)
        
        for tweet in reversed(tweets):
            tweet_id = tweet.get("link")
            text = tweet.get("text", "")
            
            if tweet_id in seen_ids:
                continue
            
            text_lower = text.lower()
            if any(kw in text_lower for kw in KEYWORDS):
                print(f"[MATCH] キーワードヒット！ 通知送信: {tweet_id}")
                send_discord({
                    "author": tweet.get("user", {}).get("name", "店舗"),
                    "link": tweet_id,
                    "text": text
                })
            
            new_seen_ids.append(tweet_id)
        
        state["seen_ids"] = new_seen_ids[-500:]
        save_state(state)
        print("[DEBUG] 状態ファイル保存完了")

    except Exception as e:
        print(f"[ERROR] 処理中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
