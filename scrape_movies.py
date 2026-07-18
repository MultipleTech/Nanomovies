import requests
import json
import re
from urllib.parse import unquote

def scrape_all_nanoflix_movies():
    # ရုပ်ရှင်စာရင်းတွေ အများဆုံးရှိနိုင်မယ့် ပင်မစာမျက်နှာများ
    urls = [
        "https://nanoflix.io/short_video/",
        "https://nanoflix.io/movie/",
        "https://nanoflix.io/"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    found_movies = {}
    
    for url in urls:
        try:
            print(f"Scanning target: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue
                
            html_content = response.text
            
            # နည်းလမ်း ၁ - HTML ထဲက stream.nanoflix.io လင့်ခ်တွေကို တိုက်ရိုက်ရှာဖွေခြင်း
            # ဥပမာ- https://stream.nanoflix.io/Ghajini-(2008)/master.m3u8
            stream_links = re.findall(r'https://stream\.nanoflix\.io/([^\s"\'\>]+)/master\.m3u8', html_content)
            
            # နည်းလမ်း ၂ - Next.js ရဲ့ JSON block ထဲက ဇာတ်ကားအမည်တွေကို လိုက်ရှာခြင်း
            slug_matches = re.findall(r'"slug"\s*:\s*"([^"]+)"', html_content)
            title_matches = re.findall(r'"title"\s*:\s*"([^"]+)"', html_content)
            
            # ပထမဆုံး တိုက်ရိုက်တွေ့တဲ့ Stream links တွေကို map လုပ်မယ်
            for folder in stream_links:
                folder_decoded = unquote(folder) # URL encoding ဖြုတ်မယ် (ဥပမာ %20 ကို spaces ပြောင်းမယ်)
                
                # Folder နာမည်ထဲကနေ Movie Name နဲ့ Year ကို ခွဲထုတ်မယ်
                # ဥပမာ - "Ghajini-(2008)" -> Name: Ghajini, Year: 2008
                match = re.search(r'^(.*?)-\((\d{4})\)$', folder_decoded)
                if match:
                    movie_name = match.group(1).replace("-", " ").strip()
                    year = match.group(2)
                else:
                    movie_name = folder_decoded.replace("-", " ").strip()
                    year = "2026"
                
                if movie_name not in found_movies:
                    found_movies[movie_name] = {
                        "name": movie_name,
                        "year": year,
                        "genre": "Movies",
                        "description": f"{movie_name} ({year}) Available to stream on Nanoflix.",
                        "stream_url": f"https://stream.nanoflix.io/{folder}/master.m3u8"
                    }
            
            # ဒုတိယအဆင့် - တကယ်လို့ slug နဲ့ title တွေတွေ့ရင် ၎င်းတို့ဆီကနေ stream url တည်ဆောက်မယ်
            for i in range(min(len(slug_matches), len(title_matches))):
                title = title_matches[i].encode().decode('unicode-escape', errors='ignore')
                slug = slug_matches[i]
                
                # ခုနှစ် ရှာမယ်
                year_match = re.search(r'\b(20\d\d|19\d\d)\b', title)
                year = year_match.group(0) if year_match else "2026"
                clean_title = re.sub(r'-\(\d{4}\)', '', title).strip()
                
                if clean_title not in found_movies:
                    formatted_slug = slug.replace(" ", "-")
                    found_movies[clean_title] = {
                        "name": clean_title,
                        "year": year,
                        "genre": "Movies",
                        "description": f"{clean_title} ({year}) Available to stream on Nanoflix.",
                        "stream_url": f"https://stream.nanoflix.io/{formatted_slug}-({year})/master.m3u8"
                    }
                    
        except Exception as e:
            print(f"Error scanning {url}: {e}")
            continue

    return list(found_movies.values())

if __name__ == "__main__":
    print("Starting comprehensive Nanoflix Scraper...")
    movies_data = scrape_all_nanoflix_movies()
    
    # ရလာတဲ့ data အားလုံးကို json သိမ်းမယ်
    if movies_data:
        with open("movies_data.json", "w", encoding="utf-8") as f:
            json.dump(movies_data, f, indent=4, ensure_ascii=False)
        print(f"Done! Captured {len(movies_data)} total movies inside movies_data.json")
    else:
        # လုံးဝရှာမတွေ့တဲ့ အခြေအနေမျိုးအတွက် စာရင်းအသေတစ်ခု (Fallback List) ထည့်ပေးထားခြင်း
        # သယ်ရင်း ဇာတ်ကားတွေ ထပ်တိုးချင်ရင် ဒီအောက်က list မှာ ကိုယ်တိုင် format အတိုင်း ကြိုထည့်ထားလို့ရပါတယ်
        hardcoded_list = [
            {
                "name": "Ghajini",
                "year": "2008",
                "genre": "Action, Romance",
                "description": "Ghajini (2008) Movie stream details.",
                "stream_url": "https://stream.nanoflix.io/Ghajini-(2008)/master.m3u8"
            }
        ]
        with open("movies_data.json", "w", encoding="utf-8") as f:
            json.dump(hardcoded_list, f, indent=4, ensure_ascii=False)
        print("No dynamic data found. Saved default list.")
                
