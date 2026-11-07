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
        # プロフィールの固定文などを除外するため、文字数が一定以上の実のあるブロックに絞る
        blocks = content.split('\n\n')
        for i, block in enumerate(blocks):
            block_str = block.strip()
            # プロフィール文やUI共通パーツを除外し、ツイート本文らしきものに限定
            if len(block_str) > 20 and "1894年の創業から" not in block_str:
                t_id = f"{username}_{hash(block_str) % 10000000}"
                parsed_tweets.append({
                    "id": str(t_id),
                    "author": username,
                    "text": block_str,
                    "link": f"https://x.com/{username}"
                })
    return parsed_tweets

def main():
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    try:
        tweets = fetch_tweets_via_proxy(TARGET_USERNAME)
        new_seen_ids = list(seen_ids)
        
        for tweet in tweets:
            tweet_id = tweet["id"]
            if tweet_id in seen_ids:
                continue
            
            text_lower = tweet["text"].lower()
            if any(kw in text_lower for kw in KEYWORDS):
                send_discord(tweet)
            
            new_seen_ids.append(tweet_id)
            
        state["seen_ids"] = new_seen_ids[-500:]
    except Exception as e:
        print(f"Error: {e}")
    finally:
        save_state(state)

if __name__ == "__main__":
    main()
