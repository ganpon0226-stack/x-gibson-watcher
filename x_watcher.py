import os
import json
import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
# 監視対象のアカウント（例: GibsonJapan や 各店舗のID）
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

def get_guest_token(session):
    headers = {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
    }
    res = session.post("https://api.twitter.com/1.1/guest/activate.json", headers=headers, timeout=10)
    res.raise_for_status()
    return res.json()["guest_token"]

def fetch_tweets(session, username):
    guest_token = get_guest_token(session)
    headers = {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
        "x-guest-token": guest_token,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # ユーザー詳細から rest_id (数値ID) を取得
    user_url = f"https://api.twitter.com/1.1/users/show.json?screen_name={username}"
    res_user = session.get(user_url, headers=headers, timeout=10)
    res_user.raise_for_status()
    user_id = res_user.json()["id_str"]
    user_name = res_user.json()["name"]

    # ユーザーのタイムライン（最新ツイート）を取得
    timeline_url = f"https://api.twitter.com/1.1/statuses/user_timeline.json?user_id={user_id}&count=20&tweet_mode=extended"
    res_tl = session.get(timeline_url, headers=headers, timeout=10)
    res_tl.raise_for_status()
    
    raw_tweets = res_tl.json()
    parsed_tweets = []
    
    for t in raw_tweets:
        t_id = t["id_str"]
        text = t.get("full_text", t.get("text", ""))
        link = f"https://x.com/{username}/status/{t_id}"
        parsed_tweets.append({
            "id": t_id,
            "author": user_name,
            "text": text,
            "link": link
        })
        
    return parsed_tweets

def main():
    print("=== [DEBUG] X Watcher (Direct Request) 起動 ===")
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    session = requests.Session()
    
    try:
        print(f"[DEBUG] アカウント @{TARGET_USERNAME} のツイートを取得中...")
        tweets = fetch_tweets(session, TARGET_USERNAME)
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
        # エラー発生時でも json ファイルが無いことによるコミット落ちを防止
        save_state(state)
        print("[DEBUG] 状態保存完了")

if __name__ == "__main__":
    main()
