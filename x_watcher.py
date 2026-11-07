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
        print("[WARNING] DISCORD_WEBHOOK_URL が設定されていません。")
        return
    payload = {
        "content": f"🎸 **Gibson関連ポスト検出**\n**{tweet['author']}**: {tweet['link']}\n```{tweet['text'][:200]}```"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def fetch_tweets_via_proxy(username):
    url = f"https://r.jina.ai/https://x.com/{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers, timeout=15)
    
    parsed_tweets = []
    if response.status_code == 200:
        content = response.text
        # Markdown形式のリンク等からツイートのURLやテキストの断片を抽出
        # 簡易的に行ごとに分割してキーワードが含まれるブロックを個別パーツとして扱う
        blocks = content.split('\n\n')
        for i, block in enumerate(blocks):
            if len(block.strip()) > 10:
                # 一意なIDをハッシュやインデックスベースで生成
                t_id = f"{username}_{i}_{hash(block) % 1000000}"
                parsed_tweets.append({
                    "id": str(t_id),
                    "author": username,
                    "text": block.strip(),
                    "link": f"https://x.com/{username}"
                })
        
    return parsed_tweets

def main():
    print("=== [DEBUG] X Watcher (Proxy Parser) 起動 ===")
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    try:
        print(f"[DEBUG] アカウント @{TARGET_USERNAME} のデータを取得中...")
        tweets = fetch_tweets_via_proxy(TARGET_USERNAME)
        print(f"[DEBUG] 取得ブロック数: {len(tweets)} 件")

        new_seen_ids = list(seen_ids)
        
        for tweet in tweets:
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
        print(f"[ERROR] 取得または解析エラー: {e}")
    finally:
        save_state(state)
        print("[DEBUG] 状態保存完了")

if __name__ == "__main__":
    main()
