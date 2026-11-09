const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;
const TARGET_LIST_URL = 'https://x.com/i/lists/2119143672495460833?s=20';
const STATE_FILE = path.join(__dirname, 'watched_tweets.json');
const KEYWORDS = ['gibson', 'ギブソン', 'tak', 'les paul', 'dc'];

function loadState() {
    if (fs.existsSync(STATE_FILE)) {
        try {
            return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
        } catch (e) {}
    }
    return { seen_ids: [] };
}

function saveState(state) {
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf8');
}

async function main() {
    console.log('=== Puppeteer X List Watcher (Debug Screenshot) 起動 ===');
    const state = loadState();
    let seenIds = new Set(state.seen_ids || []);

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

    try {
        console.log(`[NAVIGATE] リストへアクセス中: ${TARGET_LIST_URL}`);
        await page.goto(TARGET_LIST_URL, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // しっかり読み込まれるまで少し待機
        await new Promise(resolve => setTimeout(resolve, 6000));

        // ★現在の画面のスクリーンショットを保存
        await page.screenshot({ path: 'debug_screenshot.png', fullPage: true });
        console.log('[DEBUG] debug_screenshot.png を保存しました');

        const tweets = await page.evaluate(() => {
            const results = [];
            const articles = document.querySelectorAll('article[data-testid="tweet"]');
            
            articles.forEach(article => {
                const textElement = article.querySelector('[data-testid="tweetText"]');
                const linkElement = article.querySelector('a[href*="/status/"]');

                if (textElement) {
                    const text = textElement.innerText;
                    const link = linkElement ? `https://x.com${linkElement.getAttribute('href')}` : '';
                    const id = link || `hash_${text.substring(0, 30)}`;
                    results.push({ id, text, link });
                }
            });
            return results;
        });

        console.log(`[DEBUG] 取得したツイート数: ${tweets.length} 件`);

    } catch (error) {
        console.error('[ERROR]', error);
    } finally {
        await browser.close();
        console.log('=== 終了 ===');
    }
}

main();
