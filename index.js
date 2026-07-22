const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs-extra');

const BASE_URL = 'https://nanoflix.io';
const HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
};

const cleanText = (text) => text ? text.trim().replace(/\s+/g, ' ') : null;

// Detail page သို့ဝင်ရောက်ပြီး .m3u8 link နှင့် အသေးစိတ် အချက်အလက်များ ဆွဲထုတ်ခြင်း
async function scrapeDetail(url) {
    try {
        const { data } = await axios.get(url, { headers: HEADERS });
        const $ = cheerio.load(data);
        
        // 1. HTML / Script ထဲမှ .m3u8 URL ကို Regex ဖြင့် ရှာဖွေခြင်း
        let m3u8 = null;
        const m3u8Match = data.match(/https?:\/\/[^"'\s]+\.m3u8[^"'\s]*/i);
        
        if (m3u8Match) {
            m3u8 = m3u8Match[0];
        } else {
            // Check iframe src if embed player exists
            const iframeSrc = $('iframe[src*="m3u8"], iframe[src*="player"]').attr('src');
            if (iframeSrc) m3u8 = iframeSrc;
        }

        // Fallback: Nanoflix standard URL pattern
        if (!m3u8) {
            const cleanUrl = url.endsWith('/') ? url : `${url}/`;
            m3u8 = `${cleanUrl}master.m3u8`;
        }

        // 2. Full Description ရယူခြင်း
        const fullDesc = cleanText($('.entry-content, .video-description, .description').text());

        return { m3u8, fullDesc };
    } catch (e) {
        console.error(`  ⚠️ Detail page Error (${url}):`, e.message);
        const cleanUrl = url.endsWith('/') ? url : `${url}/`;
        return { m3u8: `${cleanUrl}master.m3u8` };
    }
}

async function scrapeListPage(url, type = 'movie') {
    console.log(`\n🔍 Scraping ${type} list: ${url}`);
    const { data } = await axios.get(url, { headers: HEADERS });
    const $ = cheerio.load(data);
    const resultsMap = new Map(); // Duplicates ဖယ်ထုတ်ရန် Map အသုံးပြုထားသည်

    $('.jws-post-item, article.post, .video-item').each((i, el) => {
        const $el = $(el);
        
        const titleTag = $el.find('.video_title a, h2 a, .entry-title a').first();
        const title = cleanText(titleTag.text());
        let itemUrl = titleTag.attr('href');

        if (!title || !itemUrl) return;

        itemUrl = itemUrl.startsWith('http') ? itemUrl : BASE_URL + itemUrl;

        const year = cleanText($el.find('.video-years, .year, .meta-year').text());
        const duration = cleanText($el.find('.video-time, .duration').text());
        const seasons = cleanText($el.find('.seasons, .season-count').text());
        const description = cleanText($el.find('.video-description, .excerpt, .entry-summary').text());
        
        const img = $el.find('img').first();
        let image = img.attr('data-src') || img.attr('src') || img.attr('data-lazy');
        if (image && image.startsWith('//')) image = 'https:' + image;

        const genres = $el.find('.video-cat a, .genre a, .category a')
            .map((_, a) => cleanText($(a).text())).get().filter(Boolean);

        // Data စုံလင်သော item ကိုသာ ဦးစားပေးသိမ်းဆည်းမည်
        const existing = resultsMap.get(itemUrl);
        if (!existing || (!existing.year && year)) {
            resultsMap.set(itemUrl, {
                title,
                url: itemUrl,
                year: year || null,
                duration: duration || null,
                seasons: seasons || null,
                description: description || null,
                genres: genres,
                image: image || null,
                type
            });
        }
    });

    const list = Array.from(resultsMap.values());
    console.log(`→ Found ${list.length} unique items. Now fetching .m3u8 video links...`);

    // Detail Page တစ်ခုချင်းစီဝင်ပြီး .m3u8 Link ဆွဲယူခြင်း
    for (let item of list) {
        console.log(`  🎬 Processing: ${item.title}`);
        const detail = await scrapeDetail(item.url);
        item.m3u8 = detail.m3u8;
        if (detail.fullDesc && (!item.description || detail.fullDesc.length > item.description.length)) {
            item.description = detail.fullDesc;
        }
    }

    return list;
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

    console.log('\n🎉 Done! Total unique movies:', movies.length, '| Total TV shows:', tvShows.length);
}

main().catch(console.error);
