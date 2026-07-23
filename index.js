const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs-extra');

const BASE_URL = 'https://nanoflix.io';
const HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
};

const cleanText = (text) => text ? text.trim().replace(/\s+/g, ' ') : '';

// 1. Stream URL ဖွဲ့စည်းပေးမည့် Helper Function
function generateStreamUrl(title, year) {
    if (!title) return '';

    let cleanTitle = title
        .replace(/\s*\(\s*(19\d{2}|20\d{2})\s*\)/g, '')
        .replace(/\b(19\d{2}|20\d{2})\b/g, '')
        .trim();

    const formattedTitle = cleanTitle
        .split(/\s+/)
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join('-');

    const yearMatch = year ? year.match(/\b(19\d{2}|20\d{2})\b/) : null;
    const validYear = yearMatch ? yearMatch[0] : '';
    const yearStr = validYear ? `-(${validYear})` : '';

    return `https://stream.nanoflix.io/${formattedTitle}${yearStr}/master.m3u8`;
}

// 2. Detail Page Scraper (Multi-source Fallback ရေးထားသည်)
async function scrapeDetail(pageUrl, title, initialYear) {
    try {
        const { data } = await axios.get(pageUrl, { headers: HEADERS, timeout: 10000 });
        const $ = cheerio.load(data);
        
        let finalYear = initialYear;

        // List တွင် Year မပါခဲ့ပါက နည်းလမ်း ၅ ခုဖြင့် လိုက်ရှာမည်
        if (!finalYear) {
            
            // နည်းလမ်း ၁ - URL Slug ထဲမှ Year ကို ရှာခြင်း (ဥပမာ /movie/ghajini-2008/)
            const urlYearMatch = pageUrl.match(/\b(19\d{2}|20[0-2]\d)\b/);
            if (urlYearMatch) {
                finalYear = urlYearMatch[0];
            }

            // နည်းလမ်း ၂ - JSON-LD Metadata ထဲမှ datePublished/releaseDate ရှာခြင်း
            if (!finalYear) {
                $('script[type="application/ld+json"]').each((_, el) => {
                    const jsonText = $(el).html() || '';
                    const jsonMatch = jsonText.match(/"(datePublished|releaseDate|uploadDate)"\s*:\s*"(\d{4})/i);
                    if (jsonMatch && jsonMatch[2]) {
                        finalYear = jsonMatch[2];
                    }
                });
            }

            // နည်းလမ်း ၃ - Meta Tag Article Published Time မှ ရှာခြင်း
            if (!finalYear) {
                const metaPublished = $('meta[property="article:published_time"]').attr('content');
                if (metaPublished) {
                    const pubYearMatch = metaPublished.match(/\b(19\d{2}|20[0-2]\d)\b/);
                    if (pubYearMatch) finalYear = pubYearMatch[0];
                }
            }

            // နည်းလမ်း ၄ - Page Title / Meta Title မှ ရှာခြင်း
            if (!finalYear) {
                const metaTitle = $('meta[property="og:title"]').attr('content') || $('title').text() || '';
                const titleYearMatch = metaTitle.match(/\b(19\d{2}|20[0-2]\d)\b/);
                if (titleYearMatch) finalYear = titleYearMatch[0];
            }

            // နည်းလမ်း ၅ - Main Page Content ထဲမှ ရှာခြင်း (Footer/Header များကို ဖယ်ထုတ်ပြီးမှ ရှာမည်)
            if (!finalYear) {
                $('footer, header, nav, .footer, .header, .site-footer, .site-header').remove();
                const targetAreaText = $('.movie-info, .entry-title, .video-info, .post-meta, h1, .dt-release, .entry-content').text();
                const contentYearMatch = targetAreaText.match(/\b(19\d{2}|20[0-2]\d)\b/);
                if (contentYearMatch) finalYear = contentYearMatch[0];
            }
        }

        // Stream URL ရှာဖွေခြင်း
        let streamUrl = null;
        const m3u8Match = data.match(/https?:\/\/[^"'\s]+\.m3u8[^"'\s]*/i);
        if (m3u8Match) {
            streamUrl = m3u8Match[0];
        } else {
            const iframeSrc = $('iframe[src*="m3u8"]').attr('src');
            if (iframeSrc) streamUrl = iframeSrc;
        }

        if (!streamUrl) {
            streamUrl = generateStreamUrl(title, finalYear);
        }

        let fullDesc = cleanText($('.entry-content p, .video-description p, .description p').first().text());
        if (!fullDesc) {
            fullDesc = cleanText($('.entry-content, .video-description').text()).split('Show More')[0];
        }

        return { streamUrl, fullDesc, finalYear };
    } catch (e) {
        return { 
            streamUrl: generateStreamUrl(title, initialYear),
            fullDesc: "",
            finalYear: initialYear
        };
    }
}

// 3. Single List Page Scraper
async function fetchPageItems(url, type) {
    try {
        const { data } = await axios.get(url, { headers: HEADERS, timeout: 10000 });
        const $ = cheerio.load(data);
        const items = [];

        $('.jws-post-item, article.post, .video-item').each((i, el) => {
            const $el = $(el);
            
            const titleTag = $el.find('.video_title a, h2 a, .entry-title a').first();
            const rawTitle = cleanText(titleTag.text());
            let itemUrl = titleTag.attr('href');

            if (!rawTitle || !itemUrl) return;

            itemUrl = itemUrl.startsWith('http') ? itemUrl : BASE_URL + itemUrl;

            // Card Text သို့မဟုတ် Card Link URL မှ Year ကို ရှာမည်
            const cardText = $el.find('.video-years, .year, .meta-year, .post-meta').text() || $el.text();
            let yearMatch = cardText.match(/\b(19\d{2}|20[0-2]\d)\b/) || itemUrl.match(/\b(19\d{2}|20[0-2]\d)\b/);
            let year = yearMatch ? yearMatch[0] : "";

            const title = rawTitle
                .replace(/\s*\(\s*(19\d{2}|20[0-2]\d)\s*\)\s*/g, '')
                .replace(/\b(19\d{2}|20[0-2]\d)\b/g, '')
                .trim();

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

// 4. Multi-page Scrape Loop
async function scrapeAllPages(targetUrl, type = 'movie', maxPages = 18) {
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
    console.log(`→ Processing stream URLs & detail pages...`);

    const finalResults = [];
    for (let i = 0; i < allItems.length; i++) {
        const item = allItems[i];
        console.log(`  🎬 [${i + 1}/${allItems.length}] Processing: ${item.title}`);
        
        const detail = await scrapeDetail(item.itemUrl, item.title, item.year);
        
        finalResults.push({
            title: item.title,
            year: detail.finalYear || item.year,
            category: item.category,
            description: detail.fullDesc || item.description,
            logo: item.logo,
            url: detail.streamUrl
        });
    }

    return finalResults;
}

// 5. Main Execution (Existing JSON နှင့် Merge လုပ်ပေးသည့် Logic)
async function main() {
    const movieFilePath = 'nanoflix_movies.json';
    const tvFilePath = 'nanoflix_tv_shows.json';

    // ၁။ Movies Scrape လုပ်ခြင်း
    const scrapedMovies = await scrapeAllPages(`${BASE_URL}/new-release/`, 'movie', 18);
    
    // မူလ JSON ဖိုင်ရှိပါက အရင်ဖတ်ပါမည်
    let existingMovies = [];
    if (await fs.pathExists(movieFilePath)) {
        existingMovies = await fs.readJson(movieFilePath);
    }

    // Existing Movies များကို Map ဖြင့် သိမ်းဆည်းပါမည်
    const mergedMoviesMap = new Map();
    existingMovies.forEach(item => mergedMoviesMap.set(item.title, item));

    // Scraped Data များကို Existing Data နှင့် ပေါင်းစပ်ပါမည်
    scrapedMovies.forEach(newItem => {
        if (mergedMoviesMap.has(newItem.title)) {
            const oldItem = mergedMoviesMap.get(newItem.title);
            // အကယ်၍ မူလ JSON တွင် Year ပြင်ထားပြီးဖြစ်ပါက မူလ Year ကိုအတည်ယူမည်
            mergedMoviesMap.set(newItem.title, {
                ...newItem,
                year: oldItem.year || newItem.year // Old Year ကို မဖျက်ဘဲ ထိန်းထားမည်
            });
        } else {
            mergedMoviesMap.set(newItem.title, newItem); // ကားအသစ်ဆိုလျှင် ထပ်ပေါင်းမည်
        }
    });

    const finalMovies = Array.from(mergedMoviesMap.values());
    await fs.writeJson(movieFilePath, finalMovies, { spaces: 2 });
    console.log(`✅ Movies saved (Total: ${finalMovies.length})`);


    // ၂။ TV Shows Scrape လုပ်ခြင်း
    const scrapedTv = await scrapeAllPages(`${BASE_URL}/tv_shows/`, 'tv', 18);
    
    let existingTv = [];
    if (await fs.pathExists(tvFilePath)) {
        existingTv = await fs.readJson(tvFilePath);
    }

    const mergedTvMap = new Map();
    existingTv.forEach(item => mergedTvMap.set(item.title, item));

    scrapedTv.forEach(newItem => {
        if (mergedTvMap.has(newItem.title)) {
            const oldItem = mergedTvMap.get(newItem.title);
            mergedTvMap.set(newItem.title, {
                ...newItem,
                year: oldItem.year || newItem.year
            });
        } else {
            mergedTvMap.set(newItem.title, newItem);
        }
    });

    const finalTv = Array.from(mergedTvMap.values());
    await fs.writeJson(tvFilePath, finalTv, { spaces: 2 });
    console.log(`✅ TV Shows saved (Total: ${finalTv.length})`);

    console.log(`\n🎉 Completed Auto-Merge!`);
}

main().catch(console.error);
