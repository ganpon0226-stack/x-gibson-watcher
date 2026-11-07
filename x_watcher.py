import os
import json
import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
TARGET_USERNAME = "GibsonJapan"
STATE_FILE = "watched_tweets.json"
KEYWORDS = ["gibson", "ギブソン", "tak", "レスポール"]

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

def send_discord(text, link):
    if not DISCORD_WEBHOOK_URL:
        return
    payload = {
        "content": f"🚨 **【新着・最速検知】Gibson情報**\n🔗 {link}\n```{text[:300]}```"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def fetch_and_parse():
    # ツイートのやり取りやメディア、検索結果など、一番情報がダイレクトに出るURLを狙う
    url = f"https://r.jina.ai/https://x.com/{TARGET_USERNAME}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    
    found_items = []
    if response.status_code == 200:
        content = response.text
        blocks = content.split('\n\n')
        
        for block in blocks:
            text = block.strip()
            
            # ノイズ（プロフィール紹介文、メニュー、画像リンク単体など）を完全に弾く
            if len(text) < 35:
                continue
            if "1894年の創業から" in text or "公式アカウント" in text:
                continue
            if text.startswith("Title:") or text.startswith("URL Source:") or "![Image" in text:
                continue
                
            # テキストの一部から一意なID（ハッシュ）を生成
            item_id = f"{TARGET_USERNAME}_{abs(hash(text)) % 100000000}"
            
            found_items.append({
                "id": str(item_id),
                "text": text,
                "link": f"https://x.com/{TARGET_USERNAME}"
            })
            
    return found_items

def main():
    print("=== [DEBUG] X Watcher (Direct Clean Feed) 起動 ===")
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    try:
        items = fetch_and_parse()
        print(f"[DEBUG] 抽出されたクリーンな投稿候補: {len(items)} 件")
        
        new_seen_ids = list(seen_ids)
        
        for item in items:
            item_id = item["id"]
            if item_id in seen_ids:
                continue
            
            text_lower = item["text"].lower()
            # キーワードが完全に入っているものだけを通知
            if any(kw in text_lower for kw in KEYWORDS):
                print(f"[MATCH] 目的のキーワードを検出！ 通知送信")
                send_discord(item["text"], item["link"])
            
            # 一度処理したものは（ヒットしなくても）既読リストに入れて二度と読まないようにする
            new_seen_ids.append(item_id)
            
        state["seen_ids"] = new_seen_ids[-500:]
    except Exception as e:
        print(f"[ERROR] エラー発生: {e}")
    finally:
        save_state(state)
        print("[DEBUG] 状態保存完了")

if __name__ == "__main__":
    main()
