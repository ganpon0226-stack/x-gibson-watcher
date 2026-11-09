const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;
const X_COOKIES_JSON = process.env.X_COOKIES;
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
    console.log('=== Puppeteer X List Watcher (Top-First Extraction) 起動 ===');
    const state = loadState();
    let seenIds = new Set(state.seen_ids || []);

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

    try {
        if (X_COOKIES_JSON) {
            console.log('[AUTH] Cookieを適用してログイン状態を作ります');
            const cookies = JSON.parse(X_COOKIES_JSON);
            const formattedCookies = cookies.map(c => ({
                name: c.name,
                value: c.value,
                domain: c.domain.startsWith('.') ? c.domain : '.' + c.domain,
                path: c.path || '/',
                secure: c.secure !== undefined ? c.secure : true,
                httpOnly: c.httpOnly !== undefined ? c.httpOnly : false,
            }));
            await page.setCookie(...formattedCookies);
        }

        console.log(`[NAVIGATE] リストへアクセス中: ${TARGET_LIST_URL}`);
        await page.goto(TARGET_LIST_URL, { waitUntil: 'networkidle2', timeout: 30000 });
        
        console.log('[WAIT] 最新ツイートの読み込みを待っています...');
        try {
            await page.waitForSelector('article[data-testid="tweet"]', { timeout: 15000 });
        } catch (e) {
            console.log('[WARN] 待機タイムアウトしましたが続行します');
        }
        
        await new Promise(resolve => setTimeout(resolve, 3000));

        // ★修正：スクロールする前に「一番上の新鮮な状態」で一度ツイートを収集する！
        const extractTweets = async () => {
            return await page.evaluate(() => {
                const results = [];
                const articles = document.querySelectorAll('article[data-testid="tweet"]');
                articles.forEach(article => {
                    const textElement = article.querySelector('[data-testid="tweetText"]');
                    const linkElement = article.querySelector('a[href*="/status/"]');

                    if (textElement) {
                        const text = textElement.innerText;
                        const link = linkElement ? `https://x.com${linkElement.getAttribute('href')}` : '';
                        const id = link || `hash_${text.substring(0, 30)}`;
                        // 重複を防ぐため配列にまだなければ追加
                        if (!results.some(r => r.id === id)) {
                            results.push({ id, text, link });
                        }
                    }
                });
                return results;
            });
        };

        console.log('[COLLECT] 1回目の取得（最上部の最新ツイート）...');
        let allTweets = await extractTweets();

        // その後、下にスクロールして過去分を少しずつ追加で拾う
        console.log('[SCROLL] 下にスクロールして追加のツイートを読み込みます...');
        for (let i = 0; i < 4; i++) {
            await page.evaluate(() => window.scrollBy(0, 800));
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            const moreTweets = await extractTweets();
            // 結合して重複を排除
            for (const t of moreTweets) {
                if (!allTweets.some(existing => existing.id === t.id)) {
                    allTweets.push(t);
                }
            }
        }

        console.log(`[DEBUG] 最終的に取得したユニークツイート数: ${allTweets.length} 件`);

        let newSeenIds = [...seenIds];
        let isFirstRun = seenIds.size === 0;

        for (const tweet of allTweets) {
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

        state.seen_ids = newSeenIds.slice(-800);
        saveState(state);

    } catch (error) {
        console.error('[ERROR]', error);
    } finally {
        await browser.close();
        console.log('=== 終了 ===');
    }
}

main();
