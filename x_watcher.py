import os
import json
import requests
import re

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
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
        return
    payload = {
        "content": f"🎸 **Gibson関連ポスト検出**\n**{tweet['author']}**: {tweet['link']}\n```{tweet['text'][:200]}```"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def fetch_tweets_via_proxy(username):
    url = f"https://r.jina.ai/https://x.com/{username}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    
    parsed_tweets = []
    if response.status_code == 200:
        content = response.text
        
        # ツイートのステータスURL（/status/数字）を抽出する正規表現
        status_pattern = rf"https://x\.com/{username}/status/(\d+)"
        
        # ページ内のブロックごとに解析
        blocks = content.split('\n\n')
        for block in blocks:
            match = re.search(status_pattern, block)
            if match:
                tweet_id = match.group(1)
                tweet_link = f"https://x.com/{username}/status/{tweet_id}"
                
                # ヘッダーやナビゲーションを除外し、ツイート文が含まれるブロックのみ採用
                clean_text = block.strip()
                parsed_tweets.append({
                    "id": tweet_id,
                    "author": username,
                    "text": clean_text,
                    "link": tweet_link
                })
                
    return parsed_tweets

def main():
    print("=== [DEBUG] X Watcher (Tweet Status Matcher) 起動 ===")
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    try:
        tweets = fetch_tweets_via_proxy(TARGET_USERNAME)
        print(f"[DEBUG] 抽出された有効なツイート数: {len(tweets)} 件")
        
        new_seen_ids = list(seen_ids)
        
        for tweet in tweets:
            tweet_id = tweet["id"]
            if tweet_id in seen_ids:
                continue
            
            text_lower = tweet["text"].lower()
            if any(kw in text_lower for kw in KEYWORDS):
                print(f"[MATCH] ポスト検出！ 通知送信: {tweet['link']}")
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
