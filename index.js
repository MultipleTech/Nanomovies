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

    // Title ထဲမှ Year နှင့် ပိုနေသော စာသားများကို ဖယ်ထုတ်ပါ
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

// 2. Detail Page Scraper (Meta Title & Header များပါ လိုက်ရှာပေးမည်)
async function scrapeDetail(pageUrl, title, initialYear) {
    try {
        const { data } = await axios.get(pageUrl, { headers: HEADERS, timeout: 10000 });
        const $ = cheerio.load(data);
        
        let finalYear = initialYear;

        // List တွင် Year မပါခဲ့ပါက Detail Page ၏ Meta/Title Tag များမှ တိကျစွာ ရှာယူမည်
        if (!finalYear) {
            // ၁။ Open Graph Title သို့မဟုတ် Page <title> ထဲမှ Year ရှာခြင်း (အထိရောက်ဆုံး)
            const metaTitle = $('meta[property="og:title"]').attr('content') || $('title').text() || '';
            let yearMatch = metaTitle.match(/\b(19\d{2}|20\d{2})\b/);

            // ၂။ မတွေ့သေးပါက Body Area (Footer မပါ) ထဲမှ ရှာခြင်း
            if (!yearMatch) {
                $('footer, header, nav, .footer, .header, .site-footer, .site-header').remove();
                const targetAreaText = $('.movie-info, .entry-title, .video-info, .post-meta, h1, .dt-release, .entry-content').text();
                yearMatch = targetAreaText.match(/\b(19\d{2}|20\d{2})\b/);
            }

            if (yearMatch) {
                finalYear = yearMatch[0];
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

// 3. Single List Page ကို Scrape လုပ်ပေးသည့် Function
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

            // Card စာသားမှ Year ဖမ်းယူခြင်း
            const cardText = $el.find('.video-years, .year, .meta-year, .post-meta').text() || $el.text();
            const yearMatch = cardText.match(/\b(19\d{2}|20\d{2})\b/);
            let year = yearMatch ? yearMatch[0] : "";

            const title = rawTitle
                .replace(/\s*\(\s*(19\d{2}|20\d{2})\s*\)\s*/g, '')
                .replace(/\b(19\d{2}|20\d{2})\b/g, '')
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

// 5. Main Execution
async function main() {
    // maxPages ကို 18 သို့ တိုးမြှင့်ထားသည်
    const movies = await scrapeAllPages(`${BASE_URL}/new-release/`, 'movie', 18);
    await fs.writeJson('nanoflix_movies.json', movies, { spaces: 2 });
    console.log('✅ Movies saved to nanoflix_movies.json');

    const tvShows = await scrapeAllPages(`${BASE_URL}/tv_shows/`, 'tv', 18);
    await fs.writeJson('nanoflix_tv_shows.json', tvShows, { spaces: 2 });
    console.log('✅ TV Shows saved to nanoflix_tv_shows.json');

    console.log(`\n🎉 Completed! Total movies: ${movies.length} | TV shows: ${tvShows.length}`);
}

main().catch(console.error);
                                                              
