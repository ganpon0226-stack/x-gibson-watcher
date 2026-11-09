const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;
// 実際の公開リストのURLに書き換えてください
const TARGET_LIST_URL = 'https://x.com/あなたのサブ垢ID/lists/あなたのリスト名';
const STATE_FILE = path.join(__dirname, 'watched_tweets.json');
const KEYWORDS = ['gibson', 'ギブソン', 'tak', 'les paul', 'dc'];

// 既読状態の読み込み
function loadState() {
    if (fs.existsSync(STATE_FILE)) {
        try {
            return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
        } catch (e) {
            console.error('State read error:', e);
        }
    }
    return { seen_ids: [] };
}

// 既読状態の保存
function saveState(state) {
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf8');
}

// Discord通知
async function sendDiscord(text, link) {
    if (!DISCORD_WEBHOOK_URL) return;
    const payload = {
        content: `🚨 **【Tak・Gibson速報】**\n🔗 ${link}\n\`\`\`${text.substring(0, 300)}\`\`\``
    };
    await fetch(DISCORD_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
}

async function main() {
    console.log('=== Puppeteer X List Watcher 起動 ===');
    const state = loadState();
    let seenIds = new Set(state.seen_ids || []);

    // ヘッドレスブラウザの起動
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    // ボット判定を回避するためのUser-Agent設定
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

    try {
        console.log(`[NAVIGATE] リストへアクセス中: ${TARGET_LIST_URL}`);
        await page.goto(TARGET_LIST_URL, { waitUntil: 'networkidle2', timeout: 30000 });

        // ツイート要素が読み込まれるまで少し待機
        await page.waitForTimeout(5000);

        // ページ内のツイートテキストとパーマリンクをスクレイピング
        const tweets = await page.evaluate(() => {
            const results = [];
            // Xのタイムライン上の各ツイート記事要素を取得
            const articles = document.querySelectorAll('article[data-testid="tweet"]');
            
            articles.forEach(article => {
                const textElement = article.querySelector('[data-testid="tweetText"]');
                const timeElement = article.querySelector('time');
                const linkElement = article.querySelector('a[href*="/status/"]');

                if (textElement) {
                    const text = textElement.innerText;
                    const link = linkElement ? `https://x.com${linkElement.getAttribute('href')}` : '';
                    // 一意なIDとしてツイートのリンク（またはテキストのハッシュ）を使用
                    const id = link || `hash_${text.substring(0, 30)}`;
                    results.push({ id, text, link });
                }
            });
            return results;
        });

        console.log(`[DEBUG] 取得したツイート数: ${tweets.length} 件`);

        let newSeenIds = [...seenIds];

        for (const tweet of tweets) {
            if (seenIds.has(tweet.id)) {
                continue;
            }

            const textLower = tweet.text.toLowerCase();
            const matched = KEYWORDS.some(kw => textLower.includes(kw));

            if (matched) {
                console.log(`[MATCH] キーワード検出！ 通知送信: ${tweet.link}`);
                await sendDiscord(tweet.text, tweet.link || TARGET_LIST_URL);
            }

            newSeenIds.push(tweet.id);
        }

        // 履歴は直近300件に絞る
        state.seen_ids = newSeenIds.slice(-300);
        saveState(state);

    } catch (error) {
        console.error('[ERROR]', error);
    } finally {
        await browser.close();
        console.log('=== 終了 ===');
    }
}

main();
