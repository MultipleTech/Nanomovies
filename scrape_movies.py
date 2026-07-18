import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse

def get_movie_urls_from_sitemap():
    """ sitemap.xml ထဲကနေ /movie/ ပါတဲ့ ရုပ်ရှင်လင့်ခ်တွေအကုန်လုံးကို အရင်စုဆောင်းမယ် """
    sitemap_url = "https://nanoflix.io/sitemap.xml"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    movie_urls = set()
    
    try:
        print("Reading sitemap to discover all movies...")
        response = requests.get(sitemap_url, headers=headers, timeout=15)
        if response.status_code == 200:
            # XML ထဲက <loc> tag တွေထဲက URL တွေကို ရှာမယ်
            urls = re.findall(r'<loc>(https://nanoflix\.io/movie/[^<]+)</loc>', response.text)
            for url in urls:
                # ပင်မ /movie/ page ကို ဖယ်ပြီး detail page တွေကိုပဲ ယူမယ်
                if url.strip() != "https://nanoflix.io/movie/" and url.strip() != "https://nanoflix.io/movie":
                    movie_urls.add(url.strip())
        
        # အကယ်၍ sitemap မတွေ့ရင် သယ်ရင်းပေးထားတဲ့ နမူနာလင့်ခ်တွေကို အခြေခံပြီး base ရှာဖို့ ထည့်ထားမယ်
        if not movie_urls:
            print("Sitemap empty or blocked. Using fallback URL seed...")
            movie_urls.update([
                "https://nanoflix.io/movie/the-portable-door/",
                "https://nanoflix.io/movie/ghajini/"
            ])
            
        return list(movie_urls)
    except Exception as e:
        print(f"Sitemap read error: {e}")
        return ["https://nanoflix.io/movie/the-portable-door/", "https://nanoflix.io/movie/ghajini/"]

def scrape_movie_detail(url):
    """ ဇာတ်ကားတစ်ကားချင်းစီရဲ့ page ထဲကနေ data တွေကို အတိအကျ ကောက်ယူမယ် """
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    }
    try:
        print(f"Scraping detail from: {url}")
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None
            
        html = res.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # URL ရဲ့ အဆုံးအပိုင်း (Slug) ကို ယူမယ် (ဥပမာ- the-portable-door)
        slug = url.rstrip('/').split('/')[-1]
        
        # ၁။ နာမည် (Title) ရှာဖွေခြင်း
        name_tag = soup.find('h1') or soup.find('title')
        name = name_tag.text.replace("- Nanoflix", "").strip() if name_tag else slug.replace("-", " ").title()
        
        # ၂။ Description ရှာဖွေခြင်း
        desc_tag = soup.find('meta', {'name': 'description'}) or soup.find('p')
        description = desc_tag['content'].strip() if desc_tag and desc_tag.has_attr('content') else (desc_tag.text.strip() if desc_tag else "")
        if not description or "Nanoflix" in description and len(description) < 30:
            # တကယ်လို့ meta ထဲမှာ မရှိရင် စာသားထဲက လိုက်ရှာမယ်
            p_tags = soup.find_all('p')
            for p in p_tags:
                if len(p.text.strip()) > 50:
                    description = p.text.strip()
                    break
        
        # ၃။ Year & Genre ရှာဖွေခြင်း
        # HTML text တစ်ခုလုံးထဲကနေ Year (၂၀၀၀-၂၀၃၀) ကို ရှာမယ်
        year_match = re.search(r'\b(19\d\d|20[0-2]\d|2030)\b', html)
        year = year_match.group(0) if year_match else "2026"
        
        # Genre ကို စာသားတွေထဲကနေ match လုပ်မယ်
        genres = []
        for g in ["Action", "Comedy", "Drama", "Thriller", "Horror", "Sci-Fi", "Romance", "Fantasy", "Mystery", "Adventure"]:
            if g.lower() in html.lower():
                genres.append(g)
        genre = ", ".join(genres) if genres else "Movies"
        
        # ၄။ Stream URL တည်ဆောက်ခြင်း
        # Nanoflix Stream format အတိုင်း Slug သို့မဟုတ် အမည်ကို သုံးပြီး ပြန်ဆောက်မယ်
        # ဥပမာ - Ghajini ဆိုရင် Ghajini-(2008), The Portable Door ဆိုရင် The-Portable-Door-(2023) 
        formatted_slug = slug.title().replace(" ", "-")
        
        # HTML ထဲမှာ တိုက်ရိုက် master.m3u8 လင့်ခ် ပါမပါ အရင်ရှာမယ်
        stream_finder = re.search(r'https://stream\.nanoflix\.io/[^\s"\'\>]+/master\.m3u8', html)
        if stream_finder:
            stream_url = stream_finder.group(0)
        else:
            # မတွေ့ရင် ပုံသေ format အတိုင်း Auto ဆောက်မယ်
            stream_url = f"https://stream.nanoflix.io/{formatted_slug}-({year})/master.m3u8"
            
        return {
            "name": name,
            "year": year,
            "genre": genre,
            "description": description if description else f"{name} ({year}) movie on Nanoflix.",
            "stream_url": stream_url
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

if __name__ == "__main__":
    movie_urls = get_movie_urls_from_sitemap()
    print(f"Found {len(movie_urls)} movie URLs to process.")
    
    all_movies_data = []
    
    # တွေ့တဲ့ URL တစ်ခုချင်းစီထဲ ဝင်မွှေမယ်
    for url in movie_urls:
        movie_data = scrape_movie_detail(url)
        if movie_data:
            all_movies_data.append(movie_data)
            
    # JSON သိမ်းမယ်
    if all_movies_data:
        with open("movies_data.json", "w", encoding="utf-8") as f:
            json.dump(all_movies_data, f, indent=4, ensure_ascii=False)
        print(f"Successfully saved {len(all_movies_data)} movies to movies_data.json!")
    else:
        print("No dynamic data could be scraped.")
                  
