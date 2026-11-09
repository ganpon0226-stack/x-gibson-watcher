const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;
const X_COOKIES_JSON = process.env.X_COOKIES; // GitHub SecretsからCookieを受け取る
const TARGET_LIST_URL = 'https://x.com/i/lists/2119143672495460833';
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
    console.log('=== Puppeteer X List Watcher (Cookie Auth) 起動 ===');
    const state = loadState();
    let seenIds = new Set(state.seen_ids || []);

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

    try {
        // Cookieが設定されていればブラウザにインジェクトする
        if (X_COOKIES_JSON) {
            console.log('[AUTH] Cookieを適用してログイン状態を作ります');
            const cookies = JSON.parse(X_COOKIES_JSON);
            // Puppeteerの形式に整形（domainなどが厳密な場合があるため調整）
            const formattedCookies = cookies.map(c => ({
                name: c.name,
                value: c.value,
                domain: c.domain.startsWith('.') ? c.domain : '.' + c.domain,
                path: c.path || '/',
                secure: c.secure !== undefined ? c.secure : true,
                httpOnly: c.httpOnly !== undefined ? c.httpOnly : false,
            }));
            await page.setCookie(...formattedCookies);
        } else {
            console.log('[WARN] X_COOKIESが設定されていません。ログインせずにアクセスします。');
        }

        console.log(`[NAVIGATE] リストへアクセス中: ${TARGET_LIST_URL}`);
        await page.goto(TARGET_LIST_URL, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // タイムラインの読み込みをしっかり待つ
        await new Promise(resolve => setTimeout(resolve, 7000));

        // ツイート抽出
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

        let newSeenIds = [...seenIds];
        let isFirstRun = seenIds.size === 0;

        for (const tweet of tweets) {
            if (seenIds.has(tweet.id)) {
                continue;
            }

            const textLower = tweet.text.toLowerCase();
            const matched = KEYWORDS.some(kw => textLower.includes(kw));

            if (matched && !isFirstRun) {
                console.log(`[MATCH] キーワード検出！ 通知送信: ${tweet.link}`);
                await sendDiscord(tweet.text, tweet.link || TARGET_LIST_URL);
            } else if (matched && isFirstRun) {
                console.log(`[INIT] 初回起動のため過去のヒットはスキップ: ${tweet.link}`);
            }

            newSeenIds.push(tweet.id);
        }

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
