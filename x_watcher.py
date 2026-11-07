import os
import json
import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
TARGET_USERNAME = "GibsonJapan"
STATE_FILE = "watched_tweets.json"
KEYWORDS = ["gibson", "ギブソン", "tak"]

# プロフィールの定型文などを除外するためのキーワード
EXCLUDE_WORDS = [
    "1894年の創業から",
    "世界的世界的ギターブランド",
    "公式アカウント",
    "profile_images",
    "profile_banners",
    "Markdown Content:",
    "URL Source:"
]

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
        "content": f"🎸 **Gibson新着ポスト検出**\n**{tweet['author']}**: {tweet['link']}\n```{tweet['text'][:200]}```"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def fetch_tweets_via_proxy(username):
    url = f"https://r.jina.ai/https://x.com/{username}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    
    parsed_tweets = []
    if response.status_code == 200:
        content = response.text
        blocks = content.split('\n\n')
        
        for block in blocks:
            clean_text = block.strip()
            
            # 短すぎるものや除外ワードが含まれるものはスキップ
            if len(clean_text) < 30:
                continue
            if any(exc in clean_text for exc in EXCLUDE_WORDS):
                continue
                
            # ブログやツイートの塊ごとに固有IDを生成
            t_id = f"{username}_{abs(hash(clean_text)) % 100000000}"
            parsed_tweets.append({
                "id": str(t_id),
                "author": username,
                "text": clean_text,
                "link": f"https://x.com/{username}"
            })
                
    return parsed_tweets

def main():
    print("=== [DEBUG] X Watcher (Flexible Block Matcher) 起動 ==.")
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    try:
        tweets = fetch_tweets_via_proxy(TARGET_USERNAME)
        print(f"[DEBUG] 抽出された有効な投稿ブロック数: {len(tweets)} 件")
        
        new_seen_ids = list(seen_ids)
        
        for tweet in tweets:
            tweet_id = tweet["id"]
            if tweet_id in seen_ids:
                continue
            
            text_lower = tweet["text"].lower()
            if any(kw in text_lower for kw in KEYWORDS):
                print(f"[MATCH] 新着のキーワード検出！ 通知送信")
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
