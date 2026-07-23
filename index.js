const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs-extra');

const BASE_URL = 'https://nanoflix.io';
const HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
};

// Extra Space များကို ရှင်းထုတ်ပေးသည့် Helper Function
const cleanText = (text) => text ? text.trim().replace(/\s+/g, ' ') : '';

// 1. Stream URL ကို တိကျသော Pattern ဖြစ်သည့် Title-(Year) ဖြင့် တည်ဆောက်ပေးသည့် Function
function generateStreamUrl(title, year) {
    if (!title) return '';

    // Title ထဲတွင် ပါဝင်နေသော (2008) စသည့် နှစ်များကို ဖယ်ထုတ်ပါ
    let cleanTitle = title.replace(/\s*\(\d{4}\)\s*/g, '').trim();

    // စာလုံးတိုင်း၏ ပထမအက္ခရာကို Capital ပြုလုပ်ပြီး Space များကို '-' ပြောင်းပါ
    const formattedTitle = cleanTitle
        .split(/\s+/)
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join('-');

    // Year ထဲမှ လက်သည်းကွင်းများကို ရှင်းထုတ်ပြီး -(YYYY) ပုံစံ ပြုလုပ်ပါ
    const cleanYear = year ? year.replace(/[()]/g, '').trim() : '';
    const yearStr = cleanYear ? `-(${cleanYear})` : '';

    return `https://stream.nanoflix.io/${formattedTitle}${yearStr}/master.m3u8`;
}

// 2. Detail Page Scraper
async function scrapeDetail(pageUrl, title, year) {
    try {
        const { data } = await axios.get(pageUrl, { headers: HEADERS, timeout: 10000 });
        const $ = cheerio.load(data);
        
        let streamUrl = null;

        // Page ထဲတွင် .m3u8 တိုက်ရိုက်ပါမပါ ရှာပါ
        const m3u8Match = data.match(/https?:\/\/[^"'\s]+\.m3u8[^"'\s]*/i);
        if (m3u8Match) {
            streamUrl = m3u8Match[0];
        } else {
            const iframeSrc = $('iframe[src*="m3u8"]').attr('src');
            if (iframeSrc) streamUrl = iframeSrc;
        }

        // မတွေ့ပါက Correct Stream Pattern ဖြင့် Auto Generate လုပ်ပါ
        if (!streamUrl) {
            streamUrl = generateStreamUrl(title, year);
        }

        const fullDesc = cleanText($('.entry-content, .video-description, .description').text());

        return { streamUrl, fullDesc };
    } catch (e) {
        return { 
            streamUrl: generateStreamUrl(title, year),
            fullDesc: "" 
        };
    }
}

// 3. Single List Page ကို Fetch လုပ်ပေးသည့် Function
async function fetchPageItems(url, type) {
    try {
        const { data } = await axios.get(url, { headers: HEADERS, timeout: 10000 });
        const $ = cheerio.load(data);
        const items = [];

        $('.jws-post-item, article.post, .video-item').each((i, el) => {
            const $el = $(el);
            
            const titleTag = $el.find('.video_title a, h2 a, .entry-title a').first();
            const title = cleanText(titleTag.text());
            let itemUrl = titleTag.attr('href');

            if (!title || !itemUrl) return;

            itemUrl = itemUrl.startsWith('http') ? itemUrl : BASE_URL + itemUrl;

            const year = cleanText($el.find('.video-years, .year, .meta-year').text()) || "";
            const description = cleanText($el.find('.video-description, .excerpt, .entry-summary').text()) || "";
            
            const img = $el.find('img').first();
            let logo = img.attr('data-src') || img.attr('src') || img.attr('data-lazy') || "";
            if (logo && logo.startsWith('//')) logo = 'https:' + logo;

            const genres = $el.find('.video-cat a, .genre a, .category a')
                .map((_, a) => cleanText($(a).text())).get().filter(Boolean);

            const category = genres.length > 0 ? genres[0] : (type === 'tv' ? 'TV Series' : 'Action');

            items.push({
                title,
                year,
                category,
                description,
                logo,
                itemUrl
            });
        });

        return items;
    } catch (e) {
        return [];
    }
}

// 4. စာမျက်နှာပေါင်းစုံ (Pagination Loop) Scrape လုပ်ပေးမည့် Function
async function scrapeAllPages(targetUrl, type = 'movie', maxPages = 5) {
    console.log(`\n🔍 Scraping all pages for ${type} starting from: ${targetUrl}`);
    const resultsMap = new Map();

    for (let page = 1; page <= maxPages; page++) {
        let pageUrl = targetUrl;
        if (page > 1) {
            pageUrl = targetUrl.endsWith('/') 
                ? `${targetUrl}page/${page}/` 
                : `${targetUrl}/page/${page}/`;
        }

        console.log(`  📄 Fetching Page ${page}: ${pageUrl}`);
        const items = await fetchPageItems(pageUrl, type);

        if (items.length === 0) {
            console.log(`  ⏹️ Page ${page} တွင် Data မရှိတော့ပါ။ ရပ်နားပါမည်။`);
            break;
        }

        let newItemsCount = 0;
        for (const item of items) {
            if (!resultsMap.has(item.itemUrl)) {
                resultsMap.set(item.itemUrl, item);
                newItemsCount++;
            }
        }

        console.log(`  ↳ Found ${items.length} items (${newItemsCount} new) on page ${page}`);
    }

    const allItems = Array.from(resultsMap.values());
    console.log(`\n→ Total unique items found: ${allItems.length}`);
    console.log(`→ Processing stream URLs...`);

    const finalResults = [];
    for (let i = 0; i < allItems.length; i++) {
        const item = allItems[i];
        console.log(`  🎬 [${i + 1}/${allItems.length}] Fetching stream: ${item.title}`);
        const detail = await scrapeDetail(item.itemUrl, item.title, item.year);
        
        finalResults.push({
            title: item.title,
            year: item.year,
            category: item.category,
            description: detail.fullDesc || item.description,
            logo: item.logo,
            url: detail.streamUrl
        });
    }

    return finalResults;
}

// 5. Main Execution
async function main() {
    // Movies (maxPages ကို 5 ဟု သတ်မှတ်ထားသည်၊ လိုသလို တိုးနိုင်ပါသည်)
    const movies = await scrapeAllPages(`${BASE_URL}/new-release/`, 'movie', 5);
    await fs.writeJson('nanoflix_movies.json', movies, { spaces: 2 });
    console.log('✅ Movies saved to nanoflix_movies.json');

    // TV Shows
    const tvShows = await scrapeAllPages(`${BASE_URL}/tv_shows/`, 'tv', 5);
    await fs.writeJson('nanoflix_tv_shows.json', tvShows, { spaces: 2 });
    console.log('✅ TV Shows saved to nanoflix_tv_shows.json');

    console.log(`\n🎉 Completed! Total movies: ${movies.length} | TV shows: ${tvShows.length}`);
}

main().catch(console.error);
                
