const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs-extra');
const path = require('path');

const BASE_URL = 'https://nanoflix.io';
const HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
};

// Helper to clean text
const cleanText = (text) => text ? text.trim().replace(/\s+/g, ' ') : null;

async function scrapeListPage(url, type = 'movie') {
    console.log(`Scraping ${type} list: ${url}`);
    const { data } = await axios.get(url, { headers: HEADERS });
    const $ = cheerio.load(data);
    const results = [];

    $('.jws-post-item, article.post, .video-item, .post').each((i, el) => {
        const $el = $(el);
        
        const titleTag = $el.find('.video_title a, h2 a, .entry-title a').first();
        const title = cleanText(titleTag.text());
        const url = titleTag.attr('href');

        if (!title || !url) return;

        const year = cleanText($el.find('.video-years, .year, .meta-year').text());
        const duration = cleanText($el.find('.video-time, .duration').text());
        const seasons = cleanText($el.find('.seasons, .season-count').text());
        
        const description = cleanText($el.find('.video-description, .excerpt, .entry-summary').text());
        
        const img = $el.find('img').first();
        let image = img.attr('data-src') || img.attr('src') || img.attr('data-lazy');
        if (image && image.startsWith('//')) image = 'https:' + image;

        const genres = $el.find('.video-cat a, .genre a, .category a')
            .map((_, a) => cleanText($(a).text())).get();

        results.push({
            title,
            url: url.startsWith('http') ? url : BASE_URL + url,
            year: year || null,
            duration: duration || null,
            seasons: seasons || null,
            description: description || null,
            genres: genres.filter(Boolean),
            image: image || null,
            type
        });
    });

    console.log(`→ Found ${results.length} items`);
    return results;
}

// Scrape detail page for more info (optional but recommended)
async function scrapeDetail(url) {
    try {
        const { data } = await axios.get(url, { headers: HEADERS });
        const $ = cheerio.load(data);
        
        // Add more fields if needed (actors, full description, etc.)
        const fullDesc = cleanText($('.entry-content, .video-description').text());
        
        return { fullDesc };
    } catch (e) {
        return {};
    }
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

    console.log('\n🎉 Done! Total movies:', movies.length, 'TV shows:', tvShows.length);
}

main().catch(console.error);
