
import os
import json
import requests
from ntscraper import Nitter

# 設定
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
X_AUTH_TOKEN = os.environ.get("X_AUTH_TOKEN")
# ご自身のリストIDやリストのURLを指定
LIST_URL = os.environ.get("X_LIST_URL", "https://x.com/i/lists/YOUR_LIST_ID")
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
    
    if not X_AUTH_TOKEN:
        print("[ERROR] X_AUTH_TOKEN が設定されていません！")
        return

    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    # Nitterインスタンス（Cookieを渡して非公開リストにアクセス）
    # ※ntscraperの仕様に合わせてセッションCookieを渡す設定
    scraper = Nitter(log_level=1)
    
    try:
        print(f"[DEBUG] リスト取得を試行中: {LIST_URL}")
        # 非公開リストをスクレイピングするためにauth_tokenを適用
        # （ntscraperが内部でrequestsを使用しているため、Cookieヘッダーを注入）
        headers = {"Cookie": f"auth_token={X_AUTH_TOKEN}"}
        
        # リストの最新ポストを取得
        tweets_data = scraper.get_list_tweets(LIST_URL, number=20, extra_headers=headers)
        
        tweets = tweets_data.get("tweets", [])
        print(f"[DEBUG] 取得成功！ 取得件数: {len(tweets)} 件")
        
        if len(tweets) > 0:
            print(f"[DEBUG] 最新のツイートサンプル: {tweets[0].get('text', '')[:50]}...")
        else:
            print("[WARNING] ツイートが0件です。リストURLやCookie（auth_token）が正しいか確認してください。")

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
        print(f"[ERROR] リストの取得中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
