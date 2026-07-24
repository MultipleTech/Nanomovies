import json
import os
import urllib.parse
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

def search_cinemm_description(title):
    """Cinemm.com တွင် ဇာတ်ကားခေါင်းစဉ်ဖြင့် ရှာဖွေပြီး Description ကို Extracted လုပ်ပေးသည့် Function"""
    try:
        # 1. Cinemm ရှာဖွေမှု URL တည်ဆောက်ခြင်း
        clean_title = title.split('(')[0].strip()  # Title ထဲမှ Year များပါပါက ဖြုတ်ပါ
        search_query = urllib.parse.quote(clean_title)
        search_url = f"https://cinemm.com/?s={search_query}"
        
        res = requests.get(search_url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return ""
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 2. ရလဒ်ထဲမှ ပထမဆုံး ဇာတ်ကား Link ကို ရှာခြင်း
        first_card = soup.select_one('article a, .post-title a, .entry-title a, h2.title a, .result-item a')
        if not first_card or not first_card.get('href'):
            return ""
        
        detail_url = first_card['href']
        
        # 3. Detail Page ထဲ ဝင်ပြီး Description ဖတ်ယူခြင်း
        detail_res = requests.get(detail_url, headers=HEADERS, timeout=10)
        if detail_res.status_code != 200:
            return ""
            
        detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
        
        # Description ပါဝင်နိုင်သော Class/Tag များမှ စာသားဆွဲယူခြင်း
        desc_el = detail_soup.select_one('.entry-content p, .description p, .overview p, .plot-text, .video-description p')
        if desc_el:
            desc_text = desc_el.get_text(strip=True)
            if len(desc_text) > 15:
                return desc_text
                
        return ""
    except Exception as e:
        print(f"  ❌ Error searching '{title}': {e}")
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
        # Description မပါပါက သို့မဟုတ် လွတ်နေပါက Cinemm မှ လိုက်ရှာမည်
        if not movie.get('description') or str(movie['description']).strip() == "":
            title = movie.get('title', '')
            print(f"🔍 Description လိုအပ်နေသော ဇာတ်ကား: {title}")
            
            desc = search_cinemm_description(title)
            if desc:
                movie['description'] = desc
                updated_count += 1
                print(f"  ✅ Description တွေ့ရှိ၍ ဖြည့်စွက်ပြီး: {desc[:60]}...\n")
            else:
                print(f"  ⚠️ Cinemm တွင် Description ရှာမတွေ့ပါ။\n")
                
    # ပြင်ဆင်ချက်များရှိပါက JSON ဖိုင်သို့ ပြန်ရေးသားမည်
    if updated_count > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(movies, f, ensure_ascii=False, indent=2)
        print(f"🎉 ဇာတ်ကား {updated_count} ကားအတွက် Description ဖြည့်စွက်သိမ်းဆည်းပြီးပါပြီ။")
    else:
        print("ℹ️ Description မပါသော ဇာတ်ကား မရှိပါ သို့မဟုတ် ထပ်မံဖြည့်စွက်ရန် မတွေ့ပါ။")

if __name__ == '__main__':
    main()
