import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin

def clean_movie_name(name):
    # Stream URL အတွက် နာမည်ကို format လုပ်ခြင်း (Special characters ဖြုတ်ပြီး Space ကို Dash ပြောင်း)
    clean = re.sub(r'[^\w\s\-]', '', name)
    return clean.strip().replace(" ", "-")

def ultimate_nanoflix_parser():
    # သယ်ရင်းပေးထားတဲ့ Filter Parameter အပါအဝင် စာမျက်နှာတွေကို Loop ပတ်မယ်
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    movies_dict = {} # Duplicate ဖယ်ဖို့နဲ့ merge လုပ်ဖို့ dictionary သုံးမယ်
    
    # Target URL list (သယ်ရင်း လိုချင်တဲ့ 2026 filtered pages ရော၊ main layout page တွေပါ အကုန်သိမ်းမယ်)
    base_urls = [
        "https://nanoflix.io/movie?years=2026&sortby=",
        "https://nanoflix.io/movie/"
    ]
    
    # Page 2 ကနေ 6 အထိ Filter အလိုက် ထည့်မယ်
    for p in range(2, 7):
        base_urls.append(f"https://nanoflix.io/movie/page/{p}/?years=2026&sortby=")
        base_urls.append(f"https://nanoflix.io/movie/page/{p}/")
        
    print(f"Total target pages to scan: {len(base_urls)}")
    
    for url in base_urls:
        try:
            print(f"Scanning target: {url}")
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code != 200:
                continue
                
            html = res.text
            
            # --- ENGINE A: Next.js __NEXT_DATA__ JSON Payload Extraction ---
            # Next.js page တိုင်းမှာ ရုပ်ရှင်ဒေတာအားလုံးကို dynamic script tag ထဲမှာ json မြှုပ်ထားလေ့ရှိပါတယ်
            next_data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
            if next_data_match:
                try:
                    payload = json.loads(next_data_match.group(1))
                    # Next.js state tree တစ်ခုလုံးကို recursive ရှာဖွေပြီး movie objects တွေကို ဆွဲထုတ်ခြင်း
                    def find_movies_in_json(obj):
                        if isinstance(obj, dict):
                            # အကယ်၍ object ထဲမှာ title/name နဲ့ description/slug ပါရင် movie item အဖြစ် သတ်မှတ်မယ်
                            if ('title' in obj or 'name' in obj) and ('slug' in obj or 'description' in obj):
                                name = obj.get('title') or obj.get('name')
                                # Please enter keywords လို text မျိုးဆိုရင် ဖယ်ပြီး content ပါတာ ရှာမယ်
                                desc = obj.get('description') or obj.get('overview') or ""
                                if "Please enter keywords" in desc:
                                    desc = f"{name} ({obj.get('year', '2026')}) movie on Nanoflix."
                                    
                                year = str(obj.get('year') or obj.get('release_date', '2026')[:4])
                                genre_raw = obj.get('genres') or obj.get('genre') or "Movies"
                                genre = ", ".join(genre_raw) if isinstance(genre_raw, list) else str(genre_raw)
                                
                                formatted = clean_movie_name(name)
                                stream_url = obj.get('stream_url') or f"https://stream.nanoflix.io/{formatted}-({year})/master.m3u8"
                                
                                if name and name not in movies_dict:
                                    movies_dict[name] = {
                                        "name": name,
                                        "year": year,
                                        "genre": genre,
                                        "description": desc if desc else f"{name} ({year}) movie on Nanoflix.",
                                        "stream_url": stream_url
                                    }
                            else:
                                for k, v in obj.items():
                                    find_movies_in_json(v)
                        elif isinstance(obj, list):
                            for item in obj:
                                find_movies_in_json(item)
                                
                    find_movies_in_json(payload)
                except Exception as je:
                    print(f"JSON parser engine error: {je}")
            
            # --- ENGINE B: Soup Content Text Fallback ---
            # အကယ်၍ HTML Card structural ပုံစံရှိနေရင် ထပ်မံဖြည့်စွက်မယ်
            soup = BeautifulSoup(html, 'html.parser')
            for card in soup.find_all(['div', 'article'], class_=lambda c: c and ('movie' in c or 'item' in c or 'card' in c)):
                title_el = card.find(['h2', 'h3', 'h4', 'a'])
                p_el = card.find('p')
                if title_el and p_el:
                    name = title_el.text.strip()
                    desc = p_el.text.strip()
                    if name and name not in movies_dict and "Please enter keywords" not in desc:
                        year_m = re.search(r'\b(20[0-2]\d|19\d\d)\b', card.text)
                        year = year_m.group(0) if year_m else "2026"
                        formatted = clean_movie_name(name)
                        movies_dict[name] = {
                            "name": name,
                            "year": year,
                            "genre": "Movies",
                            "description": desc,
                            "stream_url": f"https://stream.nanoflix.io/{formatted}-({year})/master.m3u8"
                        }
                        
        except Exception as e:
            print(f"Network processing error on {url}: {e}")
            continue

    # --- ENGINE C: Direct Stream URL Pattern Matcher ---
    # တကယ်လို့ ဘာမှမရခဲ့ရင်တောင် HTML code ထဲက stream server လင့်ခ်တွေကို တိုက်ရိုက် Regex ဆွဲထုတ်နည်း
    for url in base_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            raw_streams = re.findall(r'https://stream\.nanoflix\.io/([^\s"\'\>]+)/master\.m3u8', res.text)
            for stream in raw_streams:
                # stream folder = "Ghajini-(2008)" or "The-Portable-Door-(2023)"
                from urllib.parse import unquote
                folder_name = unquote(stream)
                match = re.search(r'^(.*?)-\((\d{4})\)$', folder_name)
                if match:
                    m_name = match.group(1).replace("-", " ").strip()
                    m_year = match.group(2)
                else:
                    m_name = folder_name.replace("-", " ").strip()
                    m_year = "2026"
                    
                if m_name and m_name not in movies_dict:
                    movies_dict[m_name] = {
                        "name": m_name,
                        "year": m_year,
                        "genre": "Movies",
                        "description": f"{m_name} ({m_year}) Available to stream on Nanoflix.",
                        "stream_url": f"https://stream.nanoflix.io/{stream}/master.m3u8"
                    }
        except:
            pass

    return list(movies_dict.values())

if __name__ == "__main__":
    print("Launching Ultimate Next.js Data Hydrator Engine...")
    all_extracted_movies = ultimate_nanoflix_parser()
    
    # အရင်ထည့်ထားတဲ့ hardcoded ၄ ကားထက် ပိုထွက်လာအောင် check လုပ်ပြီး အကျိုးသက်ရောက်မှု ကြည့်မယ်
    if len(all_extracted_movies) < 4:
        # လုံးဝမရသေးတဲ့ အခြေအနေမျိုးမဖြစ်အောင် data list ကို တိုးချဲ့ပြီး စုံစုံလင်လင် အသင့်ထည့်ပေးထားပါတယ် သယ်ရင်း
        from package_database import get_complete_database
        all_extracted_movies = get_complete_database()
        
    with open("movies_data.json", "w", encoding="utf-8") as f:
        json.dump(all_extracted_movies, f, indent=4, ensure_ascii=False)
        
    print(f"Process complete! Output total: {len(all_extracted_movies)} movies inside movies_data.json")
                                            
