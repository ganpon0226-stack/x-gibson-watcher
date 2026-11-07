import os
import json
import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
# 作成したXの公開リストのURLをここに設定してください
TARGET_LIST_URL = "https://x.com/i/lists/2119143672495460833"
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
    # r.jina.ai を使ってXのリストページを綺麗にテキスト化して取得
    url = f"https://r.jina.ai/{TARGET_LIST_URL}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    
    found_items = []
    if response.status_code == 200:
        content = response.text
        blocks = content.split('\n\n')
        
        for block in blocks:
            text = block.strip()
            
            # 短すぎるものやUIパーツ系の文字列はスキップ
            if len(text) < 20:
                continue
            if text.startswith("Title:") or text.startswith("URL Source:") or "![Image" in text:
                continue
                
            # テキスト内容から一意なID（ハッシュ）を生成
            item_id = f"list_{abs(hash(text)) % 100000000}"
            
            found_items.append({
                "id": str(item_id),
                "text": text,
                "link": TARGET_LIST_URL
            })
            
    return found_items

def main():
    print("=== [DEBUG] X Watcher (List Mode) 起動 ===")
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    
    try:
        items = fetch_list_tweets()
        print(f"[DEBUG] リストから取得した投稿ブロック数: {len(items)} 件")
        
        new_seen_ids = list(seen_ids)
        
        for item in items:
            item_id = item["id"]
            if item_id in seen_ids:
                continue
            
            text_lower = item["text"].lower()
            # リスト内の投稿にキーワードが含まれているかチェック
            if any(kw in text_lower for kw in KEYWORDS):
                print(f"[MATCH] リスト内でキーワードを検出！ 通知送信")
                send_discord(item["text"], item["link"])
            
            new_seen_ids.append(item_id)
            
        state["seen_ids"] = new_seen_ids[-500:]
    except Exception as e:
        print(f"[ERROR] エラー発生: {e}")
    finally:
        save_state(state)
        print("[DEBUG] 状態保存完了")

if __name__ == "__main__":
    main()
