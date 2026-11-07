import os
import json
import requests

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
        
        # 【重要】ページ上部のプロフィールやヘッダーが含まれる最初の数ブロックを丸ごとスキップ
        # 実際のツイートが並んでくる後ろ側のブロックだけを対象にします
        target_blocks = blocks[4:] if len(blocks) > 4 else blocks
        
        for block in target_blocks:
            clean_text = block.strip()
            
            # 「Title:」で始まるもの、短すぎるもの、メニュー系要素は除外
            if clean_text.startswith("Title:") or clean_text.startswith("URL Source:"):
                continue
            if len(clean_text) < 30:
                continue
                
            # ツイート固有のハッシュIDを生成
            t_id = f"{username}_{abs(hash(clean_text)) % 100000000}"
            parsed_tweets.append({
                "id": str(t_id),
                "author": username,
                "text": clean_text,
                "link": f"https://x.com/{username}"
            })
                
    return parsed_tweets

def main():
    print("=== [DEBUG] X Watcher (Profile Skip Mode) 起動 ===")
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
                print(f"[MATCH] キーワード検出！ 通知送信")
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
