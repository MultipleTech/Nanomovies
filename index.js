const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs-extra');

const BASE_URL = 'https://nanoflix.io';
const HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
};

// တစ်ပိုင်းချင်းဆွဲတဲ့ Function
async function fetchPageItems(pageNum) {
    const url = `${BASE_URL}/page-${pageNum}.html`;
    console.log(`📄 Fetching Page ${pageNum}: ${url}`);

    try {
        const { status, data } = await axios.get(url, { headers: HEADERS, timeout: 10000 });
        console.log(` -> Status: ${status}, Size: ${data.length}`);

        const $ = cheerio.load(data);
        const items = [];

        $('.product_pod').each((i, el) => {
            const title = $(el).find('h3 a').attr('title');
            const price = $(el).find('.price_color').text();
            items.push({ title, price });
        });

        console.log(` -> Found ${items.length} items`);
        return items;

    } catch (e) {
        // Page မရှိတော့ရင် 404 error တက်မယ်
        if (e.response && e.response.status === 404) {
            console.log(` -> Page ${pageNum} not found (404) - End of list`);
            return null; // null ပြန်ရင် ရပ်ရမယ်ဆိုတာ သိမယ်
        }
        console.log(` -> Error: ${e.message}`);
        return []; // တခြား error ဆို ခဏကျော်မယ်
    }
}

// Main Loop - Page 18 ထိ
async function scrapeAllPages(maxPages = 18) {
    const allData = [];
    
    for (let page = 1; page <= maxPages; page++) {
        // ၁။ Delay ထည့် - Bot လို့ မထင်အောင်
        await new Promise(r => setTimeout(r, 800));

        const items = await fetchPageItems(page);

        // ၂။ null (404) ပြန်လာရင် ရပ်မယ်
        if (items === null) {
            console.log('⏹️ No more pages, stopping.');
            break;
        }

        // ၃။ 0 ခုဖြစ်ရင် ချက်ချင်း break မလုပ်ဘဲ ကျော်မယ်
        if (items.length === 0) {
            console.log('⚠️ Empty page, skipping...');
            continue;
        }

        allData.push(...items);
    }

    await fs.writeJson('practice_data.json', allData, { spaces: 2 });
    console.log(`\n✅ Done! Total: ${allData.length} items saved to practice_data.json`);
}

scrapeAllPages(18);
