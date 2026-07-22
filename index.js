const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs-extra');

const BASE_URL = 'https://nanoflix.io';
const HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
};

const cleanText = (text) => text ? text.trim().replace(/\s+/g, ' ') : '';

// Detail page သို့ဝင်ရောက်ပြီး .m3u8 stream URL နှင့် Description အပြည့်အစုံ ရယူခြင်း
async function scrapeDetail(pageUrl, title, year) {
    try {
        const { data } = await axios.get(pageUrl, { headers: HEADERS });
        const $ = cheerio.load(data);
        
        // 1. Script/HTML ထဲမှ .m3u8 URL ကို တိုက်ရိုက် ရှာဖွေခြင်း
        let streamUrl = null;
        const m3u8Match = data.match(/https?:\/\/[^"'\s]+\.m3u8[^"'\s]*/i);
        
        if (m3u8Match) {
            streamUrl = m3u8Match[0];
        } else {
            const iframeSrc = $('iframe[src*="m3u8"]').attr('src');
            if (iframeSrc) streamUrl = iframeSrc;
        }

        // 2. ရှာမတွေ့ပါက Stream URL Pattern ဖြင့် Auto Formatting ပြုလုပ်ခြင်း
        if (!streamUrl && title) {
            const formattedTitle = title
                .split(' ')
                .map(w => w.charAt(0).toUpperCase() + w.slice(1))
                .join('-');
            const yearStr = year ? `-${year}` : '';
            streamUrl = `https://stream.nanoflix.io/${formattedTitle}${yearStr}/master.m3u8`;
        }

        // Full Description ဆွဲယူခြင်း
        const fullDesc = cleanText($('.entry-content, .video-description, .description').text());

        return { streamUrl, fullDesc };
    } catch (e) {
        console.error(`  ⚠️ Detail Error (${pageUrl}):`, e.message);
        const formattedTitle = title.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('-');
        const yearStr = year ? `-${year}` : '';
        return { 
            streamUrl: `https://stream.nanoflix.io/${formattedTitle}${yearStr}/master.m3u8`,
            fullDesc: "" 
        };
    }
}

async function scrapeListPage(listUrl, type = 'movie') {
    console.log(`\n🔍 Scraping ${type} list: ${listUrl}`);
    const { data } = await axios.get(listUrl, { headers: HEADERS });
    const $ = cheerio.load(data);
    const resultsMap = new Map();

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

        // Category: ပထမဆုံး Genre သို့မဟုတ် Default
        const category = genres.length > 0 ? genres[0] : (type === 'tv' ? 'TV Series' : 'Action');

        // Duplicate များ ဖယ်ထုတ်ခြင်း
        if (!resultsMap.has(itemUrl) || (!resultsMap.get(itemUrl).year && year)) {
            resultsMap.set(itemUrl, {
                title,
                year,
                category,
                description,
                logo,
                itemUrl
            });
        }
    });

    const items = Array.from(resultsMap.values());
    console.log(`→ Found ${items.length} unique items. Processing stream URLs...`);

    const finalResults = [];

    for (let item of items) {
        console.log(`  🎬 Fetching stream data: ${item.title}`);
        const detail = await scrapeDetail(item.itemUrl, item.title, item.year);
        
        // တောင်းဆိုထားသည့် JSON Format အတိုင်း တည်ဆောက်ခြင်း
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

async function main() {
    // Movies
    const movies = await scrapeListPage(`${BASE_URL}/movie/`, 'movie');
    await fs.writeJson('nanoflix_movies.json', movies, { spaces: 2 });
    console.log('✅ Movies saved to nanoflix_movies.json');

    // TV Shows
    const tvShows = await scrapeListPage(`${BASE_URL}/tv_shows/`, 'tv');
    await fs.writeJson('nanoflix_tv_shows.json', tvShows, { spaces: 2 });
    console.log('✅ TV Shows saved to nanoflix_tv_shows.json');

    console.log(`\n🎉 Completed! Total movies: ${movies.length} | TV shows: ${tvShows.length}`);
}

main().catch(console.error);
                                
