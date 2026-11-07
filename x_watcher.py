import os
import json
import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
TARGET_LIST_URL = "https://x.com/あなたのサブ垢ID/lists/あなたのリスト名" # ご自身のリストURLに変更してください
STATE_FILE = "watched_tweets.json"
KEYWORDS = ["gibson", "ギブソン", "tak", "レスポール", "les paul"]

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
        "content": f"🚨 **【リスト検知】Gibson・楽器情報**\n🔗 {link}\n```{text[:300]}```"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def fetch_list_tweets():
    url = f"https://r.jina.ai/{TARGET_LIST_URL}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    
    found_items = []
    if response.status_code == 200:
        content = response.text
        blocks = content.split('\n\n')
        
        for block in blocks:
            text = block.strip()
            
            if len(text) < 20:
                continue
            if text.startswith("Title:") or text.startswith("URL Source:") or "![Image" in text:
                continue
                
            item_id = f"list_{abs(hash(text)) % 100000000}"
            
            found_items.append({
                "id": str(item_id),
                "text": text,
                "link": TARGET_LIST_URL
            })
            
    return found_items

def main():
    print("=== [DEBUG] X Watcher (Debug Log Mode) 起動 ===")
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    try:
        items = fetch_list_tweets()
        print(f"[DEBUG] 取得された投稿ブロック数: {len(items)} 件")
        
        # 【デバッグ用】取得した全テキストをログに出力
        for i, item in enumerate(items):
            print(f"--- [BLOCK {i+1}] ---")
            print(item["text"])
            print("-" * 20)
        
        new_seen_ids = list(seen_ids)
        
        for item in items:
            item_id = item["id"]
            if item_id in seen_ids:
                print(f"[SKIP] 既読IDのためスキップ: {item_id}")
                continue
            
            text_lower = item["text"].lower()
            print(f"[CHECK] キーワード照合中... テキスト一部: {item['text'][:50]}...")
            
            if any(kw in text_lower for kw in KEYWORDS):
                print(f"🎉 [MATCH] キーワード検出！ 通知送信を実行します")
                send_discord(item["text"], item["link"])
            else:
                print(f"[NO MATCH] キーワードに一致しませんでした")
            
            new_seen_ids.append(item_id)
            
        state["seen_ids"] = new_seen_ids[-500:]
    except Exception as e:
        print(f"[ERROR] エラー発生: {e}")
    finally:
        save_state(state)
        print("[DEBUG] 状態保存完了")

if __name__ == "__main__":
    main()
