import json
import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,my;q=0.8'
}

def clean_description(text):
    """HTML Tags၊ +++++++ နှင့် မလိုလားအပ်သော သင်္ကေတများ ဖယ်ထုတ်ပေးသည့် Function"""
    if not text:
        return ""
    soup = BeautifulSoup(text, 'html.parser')
    clean_text = soup.get_text(separator=' ')
    
    clean_text = re.sub(r'\+[\+\s]+', ' ', clean_text)
    clean_text = re.sub(r'^[^\w\s\u1000-\u109F]+', '', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def fetch_description_from_page(page_url):
    """Detail Page URL မှ မြန်မာစာ ပါသော Description ကို တိုက်ရိုက် ဖတ်ယူပေးသည့် Function"""
    try:
        res = requests.get(page_url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return ""
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # မြန်မာ Unicode စာသားပါသော Paragraph များကို ဦးစားပေးရှာမည်
        paragraphs = soup.find_all(['p', 'div'])
        for p in paragraphs:
            text = p.get_text(strip=True)
            # မြန်မာစာ (Unicode Range \u1000-\u109F) ပါမပါ နှင့် စာလုံးရေ အလုံအလောက် ရှိမရှိ စစ်ဆေးခြင်း
            if len(text) > 30 and re.search(r'[\u1000-\u109F]', text):
                cleaned = clean_description(text)
                if len(cleaned) > 30 and not cleaned.startswith(('http', 'Copyright', 'Download', 'Watch')):
                    return cleaned
    except Exception:
        pass
    return ""

def search_cinemm_via_unified_wp_api(clean_title):
    """၁။ WordPress Unified Search API (/wp-json/wp/v2/search) သုံး၍ Custom Post Type (Movies) အားလုံးထဲတွင် ရှာဖွေခြင်း"""
    try:
        search_url = f"https://cinemm.com/wp-json/wp/v2/search?search={urllib.parse.quote(clean_title)}&per_page=5"
        res = requests.get(search_url, headers=HEADERS, timeout=10)
        
        if res.status_code == 200:
            items = res.json()
            if items and len(items) > 0:
                for item in items:
                    # Search result item ၏ self API link မှတစ်ဆင့် content တိုက်ရိုက်ဆွဲယူခြင်း
                    self_link = item.get('_links', {}).get('self', [{}])[0].get('href')
                    if self_link:
                        item_res = requests.get(self_link, headers=HEADERS, timeout=10)
                        if item_res.status_code == 200:
                            data = item_res.json()
                            raw_content = data.get('content', {}).get('rendered', '') or data.get('excerpt', {}).get('rendered', '')
                            cleaned = clean_description(raw_content)
                            if len(cleaned) > 20:
                                return cleaned
                    
                    # API link မရပါက Page URL မှ လှမ်းဆွဲမည်
                    page_url = item.get('url')
                    if page_url:
                        desc = fetch_description_from_page(page_url)
                        if desc:
                            return desc
    except Exception:
        pass
    return ""

def search_cinemm_via_html(clean_title):
    """၂။ HTML Search Page (?s=title) မှ Link ရှာပြီး Scraping လုပ်ခြင်း"""
    try:
        search_url = f"https://cinemm.com/?s={urllib.parse.quote(clean_title)}"
        res = requests.get(search_url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return ""

        soup = BeautifulSoup(res.text, 'html.parser')
        
        links = soup.select('a[href*="cinemm.com"]')
        for a in links:
            href = a.get('href', '')
            if href and not any(x in href for x in ['/?s=', '/category/', '/tag/', '/page/']):
                desc = fetch_description_from_page(href)
                if desc:
                    return desc
    except Exception:
        pass
    return ""

def search_cinemm_description(title):
    # Title သန့်စင်ခြင်း (ဥပမာ "Soul On Fire (2025)" -> "Soul On Fire")
    clean_title = re.sub(r'\s*\(\s*(19\d{2}|20\d{2})\s*\)', '', title).strip()
    
    # ၁။ Unified WP API ဖြင့် အရင်စမ်းမည်
    desc = search_cinemm_via_unified_wp_api(clean_title)
    if desc:
        return desc

    # ၂။ HTML Search Page ဖြင့် ဆက်လက်စမ်းမည်
    desc = search_cinemm_via_html(clean_title)
    if desc:
        return desc
        
    return ""

def main():
    file_path = 'nanoflix_movies.json'
    
    if not os.path.exists(file_path):
        print(f"⚠️ {file_path} ဖိုင်ကို ရှာမတွေ့ပါ။")
        return
        
    with open(file_path, 'r', encoding='utf-8') as f:
        movies = json.load(f)
        
    updated_count = 0
    print(f"📊 စုစုပေါင်း ဇာတ်ကား {len(movies)} ကားအနက် Description မပါသည်များကို စစ်ဆေးနေပါသည်။\n")
    
    for movie in movies:
        if not movie.get('description') or str(movie['description']).strip() == "":
            title = movie.get('title', '')
            print(f"🔍 Description လိုအပ်နေသော ဇာတ်ကား: {title}")
            
            desc = search_cinemm_description(title)
            if desc:
                movie['description'] = desc
                updated_count += 1
                print(f"  ✅ Description တွေ့ရှိ၍ ဖြည့်စွက်ပြီး: {desc[:80]}...\n")
            else:
                print(f"  ⚠️ Cinemm တွင် Description ရှာမတွေ့ပါ။\n")
                
    if updated_count > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(movies, f, ensure_ascii=False, indent=2)
        print(f"🎉 ဇာတ်ကား {updated_count} ကားအတွက် Description ဖြည့်စွက်သိမ်းဆည်းပြီးပါပြီ။")
    else:
        print("ℹ️ Description မပါသော ဇာတ်ကား မရှိပါ သို့မဟုတ် ထပ်မံဖြည့်စွက်ရန် မတွေ့ပါ။")

if __name__ == '__main__':
    main()
    
