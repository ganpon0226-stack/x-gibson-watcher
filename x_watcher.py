import os
import json
import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
# 監視対象のアカウント名（例: GibsonJapan や 各楽器店のID）
TARGET_USERNAME = os.environ.get("X_TARGET_USERNAME", "GibsonJapan")
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

def fetch_tweets(username):
    # Xの公式ウィジェット（埋め込み）用APIエンドポイント（認証不要で高確率で取得可能）
    url = f"https://cdn.syndication.twimg.com/v-1/timeline/profile?screen_name={username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    data = res.json()
    
    parsed_tweets = []
    user_name = data.get("user", {}).get("name", username)
    tweets_list = data.get("tweets", [])
    
    for t in tweets_list:
        t_id = str(t.get("id_str", ""))
        text = t.get("text", "")
        link = f"https://x.com/{username}/status/{t_id}"
        parsed_tweets.append({
            "id": t_id,
            "author": user_name,
            "text": text,
            "link": link
        })
        
    return parsed_tweets

def main():
    print("=== [DEBUG] X Watcher (Syndication API) 起動 ===")
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    try:
        print(f"[DEBUG] アカウント @{TARGET_USERNAME} のツイートを取得中...")
        tweets = fetch_tweets(TARGET_USERNAME)
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
        print(f"[ERROR] 通信またはデータ解析エラー: {e}")
    finally:
        # 例外時でも必ずファイルを保存し、Gitの未コミットエラーを防ぐ
        save_state(state)
        print("[DEBUG] 状態保存完了")

if __name__ == "__main__":
    main()
