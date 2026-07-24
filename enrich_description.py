import json
import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

def clean_description(text):
    """စာသားထဲမှ +++++++ နှင့် ပိုနေသော Space များကို ရှင်းထုတ်ပေးသည့် Function"""
    if not text:
        return ""
    text = re.sub(r'\+[\+\s]+', ' ', text)
    text = re.sub(r'^[^\w\s\u1000-\u109F]+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def search_cinemm_via_wp_api(clean_title):
    """၁။ WordPress REST API ဖြင့် တိုက်ရိုက် ရှာဖွေခြင်း (အထိရောက်ဆုံးနှင့် အတိကျဆုံး)"""
    try:
        api_url = f"https://cinemm.com/wp-json/wp/v2/posts?search={urllib.parse.quote(clean_title)}&per_page=3"
        res = requests.get(api_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            posts = res.json()
            if posts and len(posts) > 0:
                post = posts[0]
                raw_html = post.get('content', {}).get('rendered', '') or post.get('excerpt', {}).get('rendered', '')
                soup = BeautifulSoup(raw_html, 'html.parser')
                text = soup.get_text()
                cleaned = clean_description(text)
                if len(cleaned) > 20:
                    return cleaned
    except Exception:
        pass
    return ""

def search_cinemm_via_html(clean_title):
    """၂။ HTML Search Page မှ Selector အစုံဖြင့် လိုက်ရှာခြင်း"""
    try:
        search_url = f"https://cinemm.com/?s={urllib.parse.quote(clean_title)}"
        res = requests.get(search_url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return ""

        soup = BeautifulSoup(res.text, 'html.parser')

        # Link ရှာရန် Selector မျိုးစုံ သုံးထားသည်
        links = soup.select('article a, .post-title a, .entry-title a, h2 a, h3 a, .item a, .result-item a, a[href*="cinemm.com"]')
        
        target_link = None
        for a in links:
            href = a.get('href', '')
            text = a.get_text(strip=True).lower()
            if href and 'cinemm.com' in href and not href.endswith('/?s='):
                if clean_title.lower() in text or clean_title.lower() in href.lower():
                    target_link = href
                    break
                elif not target_link:
                    target_link = href

        if not target_link:
            return ""

        detail_res = requests.get(target_link, headers=HEADERS, timeout=10)
        if detail_res.status_code != 200:
            return ""

        detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
        paragraphs = detail_soup.select('.entry-content p, .description p, .overview p, .post-content p, article p, p')
        
        full_text = []
        for p in paragraphs:
            p_text = p.get_text(strip=True)
            if len(p_text) > 20 and not p_text.startswith(('http', 'Copyright', 'Download')):
                full_text.append(p_text)

        combined = " ".join(full_text)
        cleaned = clean_description(combined)
        if len(cleaned) > 20:
            return cleaned

    except Exception:
        pass
    return ""

def search_cinemm_description(title):
    # Title ထဲမှ Year (2025) စသည်များကို ဖြုတ်ပြီး Title သန့်သန့်ဖြင့် ရှာမည်
    clean_title = re.sub(r'\s*\(\s*(19\d{2}|20\d{2})\s*\)', '', title).strip()
    
    # 1. WP-JSON API ဖြင့် အရင်စမ်းမည်
    desc = search_cinemm_via_wp_api(clean_title)
    if desc:
        return desc

    # 2. မရပါက HTML Scraping ဖြင့် ဆက်လက်စမ်းမည်
    return search_cinemm_via_html(clean_title)

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
        
