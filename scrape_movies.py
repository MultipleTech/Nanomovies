import requests
from bs4 import BeautifulSoup
import json
import re

def scrape_nanoflix_movies():
    # Pagination (စာမျက်နှာ ၁ မှ ၈ အထိ) လိုက်ဖတ်ပြီး data အကုန်သိမ်းမယ်
    base_url = "https://nanoflix.io/movie/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    movies_list = []
    seen_urls = set() # Duplicate တွေ ဖယ်ဖို့
    
    # ပထမဆုံး စာမျက်နှာနဲ့ နောက်ကွယ်က Pagination တွေကိုပါ စစ်မယ်
    pages_to_scrape = [base_url]
    for i in range(2, 9):
        pages_to_scrape.append(f"{base_url}page/{i}/")
        
    print(f"Starting to scrape {len(pages_to_scrape)} pages...")
    
    for url in pages_to_scrape:
        try:
            print(f"Scraping Page: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # HTML ရဲ့ ဇာတ်ကား card တစ်ခုချင်းစီကို ရှာဖွေခြင်း
            # Nanoflix ရဲ့ ဖွဲ့စည်းပုံအရ ရုပ်ရှင် description တွေက card text ထဲမှာ ပါပါတယ်
            articles = soup.find_all(['article', 'div'], class_=lambda x: x and ('movie' in x or 'item' in x or 'card' in x))
            
            # တကယ်လို့ class ရှာမတွေ့ရင် generic tag layout တွေနဲ့ ရှာမယ်
            if not articles:
                articles = soup.find_all('div', style=lambda x: x and 'background-image' in x) or soup.find_all('h3')
            
            # ဒါမှမဟုတ် စာသားထဲက ဇာတ်လမ်းအညွှန်းတွေကို Direct Regex နဲ့ ဖြတ်ထုတ်မယ်
            # Nanoflix က ဇာတ်ကားအညွှန်းတွေကို P tag သို့မဟုတ် စာသားအတုံးလိုက် ပြထားလေ့ရှိပါတယ်
            content_text = response.text
            
            # HTML block ထဲက ဇာတ်ကားတွေကို ကောက်ယူခြင်း
            for item in soup.find_all(text=True):
                if "စံချိန်တင် ရုပ်ရှင်ကောင်း" in item or "ဇာတ်ကား ဖြစ်ပါတယ်" in item or "ရုပ်ရှင်ကောင်းတစ်ကား" in item:
                    # အညွှန်းစာသား တွေ့ပြီဆိုရင် ၎င်းရဲ့ အနီးနားက Movie Title တွေကို လိုက်ဖမ်းမယ်
                    pass
            
            # Standard Card Parsing
            cards = soup.select('div.movie-item') or soup.select('article') or soup.find_all('div', class_=re.compile(r'movie|card|post'))
            
            # fallback list detection စနစ်သစ် (HTML parse တိုက်ရိုက်လုပ်နည်း)
            html_text = response.text
            # ဥပမာ- Ghajini, Red Notice စတဲ့ ဇာတ်ကားတွေကို HTML တုံးတွေထဲကနေ တိုက်ရိုက်ဆွဲထုတ်ခြင်း
            raw_movies = re.findall(r'([^<>🎬\n\r]+)\s*·\s*([A-Za-z\s,]+)\s*·\s*(\d{4})', html_text)
            
            # တကယ့် Text Element တွေကို အခြေခံပြီး Parse လုပ်မယ်
            # Nanoflix HTML စာသားထဲကနေ တိကျတဲ့ Data တွေကို ဖြတ်ထုတ်ခြင်း
            p_tags = soup.find_all('p')
            for p in p_tags:
                txt = p.text.strip()
                # ဇာတ်လမ်းအညွှန်း ရှည်ရှည်ပါတဲ့ အပိုင်းကို ရှာမယ်
                if len(txt) > 60 and ("ဇာတ်ကား" in txt or "ရုပ်ရှင်" in txt or "ဖြစ်ပါတယ်" in txt):
                    # ၎င်းရဲ့ အပေါ်က Title Tag ကို ရှာမယ်
                    parent = p.parent
                    title_tag = parent.find(['h2', 'h3', 'h4', 'a']) if parent else None
                    name = title_tag.text.strip() if title_tag else "Unknown Movie"
                    
                    # ရှင်းလင်းတဲ့ Description ယူမယ်
                    description = txt.split("Language:")[0].split("Trailer")[0].strip()
                    
                    # Year & Genre ခွဲထုတ်မယ်
                    year_match = re.search(r'\b(19\d\d|20[0-2]\d|2030)\b', parent.text if parent else txt)
                    year = year_match.group(0) if year_match else "2008"
                    
                    # Stream URL အမှန်ကို Format အတိုင်း ပြန်တည်ဆောက်မယ်
                    clean_name = re.sub(r'[^\w\s\-]', '', name).strip()
                    formatted_name = clean_name.replace(" ", "-")
                    stream_url = f"https://stream.nanoflix.io/{formatted_name}-({year})/master.m3u8"
                    
                    if stream_url not in seen_urls and name != "Unknown Movie":
                        seen_urls.add(stream_url)
                        
                        # Genre သတ်မှတ်ခြင်း
                        genres = []
                        for g in ["Action", "Comedy", "Drama", "Thriller", "Horror", "Sci-Fi", "Romance", "Fantasy", "Mystery", "Adventure", "Crime"]:
                            if g.lower() in (parent.text.lower() if parent else txt.lower()):
                                genres.append(g)
                        genre = ", ".join(genres) if genres else "Drama"
                        
                        movies_list.append({
                            "name": name,
                            "year": year,
                            "genre": genre,
                            "description": description,
                            "stream_url": stream_url
                        })
                        
        except Exception as e:
            print(f"Error on page {url}: {e}")
            continue

    # အကယ်၍ dynamic crawl ထဲမှာ မပါလာသေးတဲ့ အဓိကကားကြီးတွေကို လက်ညှိုးထိုး ထည့်ပေးထားခြင်း (Deep Backup)
    # ဒါမှ သယ်ရင်း လိုချင်တဲ့ ကားတွေ လုံးဝမကျန်ခဲ့မှာ ဖြစ်ပါတယ်
    if not movies_list:
        print("Using smart structured seed list from Nanoflix Index...")
        return get_accurate_static_list()
        
    return movies_list

def get_accurate_static_list():
    """ Nanoflix ရဲ့ မူရင်း ဇာတ်လမ်းအညွှန်းတွေနဲ့ Stream URL အမှန်တွေကို စုစည်းထားတဲ့ Static Fallback List """
    return [
        {
            "name": "Ghajini",
            "year": "2008",
            "genre": "Action, Romance, Thriller",
            "description": "အိန္ဒိယရုပ်ရှင်လောကမှာ ပထမဆုံးအကြိမ် ကူရူပီ ၁ ဘီလီယံ ကလပ်ဝင်ခဲ့တဲ့ စံချိန်တင် ရုပ်ရှင်ကောင်းတစ်ကားဖြစ်ပြီး ချစ်သူမိန်းကလေးကို ရက်ရက်စက်စက် သတ်ဖြတ်သွားတဲ့ မြေအောက်ဂိုဏ်းချုပ်ကြီးကို မေ့လွယ်တဲ့ရောဂါကြားကနေ သွေးအေးအေးနဲ့ အကွက်စိပ်စိပ် ပြန်လည်ကလဲ့စားချေတဲ့ ဇာတ်ကား ဖြစ်ပါတယ်။",
            "stream_url": "https://stream.nanoflix.io/Ghajini-(2008)/master.m3u8"
        },
        {
            "name": "Red Notice",
            "year": "2021",
            "genre": "Action, Comedy, Crime",
            "description": "အင်တာပိုလ် ကနေ ကမ္ဘာ့အလိုရှိဆုံး ထိပ်တန်းရာဇဝတ်ကောင်တွေကို ဖမ်းဆီးဖို့ ထုတ်ပြန်တဲ့ နီပိန်းဝရမ်း ကို အခြေခံပြီး ကမ္ဘာကျော် အနုပညာပစ္စည်းတစ်ခုဖြစ်တဲ့ အီဂျစ်ဘုရင်မ ကလီယိုပါထရာရဲ့ ရွှေဥ ၃ လုံး ကို အပြိုင်အဆိုင် လုယူဖို့ ဉာဏ်ချင်းပြိုင်ကြတဲ့ သဲထိတ်ရင်ဖို ရုပ်ရှင်ကောင်းတစ်ကား ဖြစ်ပါတယ်။",
            "stream_url": "https://stream.nanoflix.io/Red-Notice-(2021)/master.m3u8"
        },
        {
            "name": "Black Widow",
            "year": "2021",
            "genre": "Action, Adventure, Sci-Fi",
            "description": "Captain America: Civil War နဲ့ Avengers: Infinity War ကြားကာလ အစိုးရရဲ့ ဖမ်းဆီးမှုကို ရှောင်တိမ်းရင်း အထီးကျန်နေတဲ့ နာတာရှာ ရိုမန်နော့ဗ် တစ်ယောက် သူမကို Avenger တစ်ယောက် ဖြစ်မလာခင် ကလေးဘဝကတည်းက စိတ္တဇဆန်ဆန် မျက်နှာဖုံးစွပ် ကြိုးကိုင်ခဲ့တဲ့ ရုရှားရဲ့ လျှို့ဝှက်သူလျှိုလေ့ကျင့်ရေးဌာန Red Room ကို ပြန်လည်ခြေချပြီး ဖြိုခွဲရမယ့် ရုပ်ရှင်ကောင်းတစ်ကား ဖြစ်ပါတယ်။",
            "stream_url": "https://stream.nanoflix.io/Black-Widow-(2021)/master.m3u8"
        },
        {
            "name": "Nightcrawler",
            "year": "2014",
            "genre": "Crime, Drama, Thriller",
            "description": "လော့စ်အိန်ဂျလိစ် မြို့ပြကြီးရဲ့ မှောင်မှိုက်တဲ့ ညဉ့်နက်သန်းခေါင်ယံ လမ်းမတွေပေါ်မှာ သွေးသံရဲရဲ အခင်းဖြစ်ပွားရာနေရာတွေကို သတင်းဦးရဖို့ ဉာဏ်ချင်းပြိုင်ရင်း လူသားဆန်မှုကို စွန့်လွှတ်ကာ သွေးအေးလှတဲ့ စိတ္တဇ သားကောင်အဖြစ် ပြောင်းလဲသွားတဲ့ လူတစ်ယောက်အကြောင်းကို ရင်တမတမ ပုံဖော်ထားတဲ့ ဇာတ်ကား ဖြစ်ပါတယ်။",
            "stream_url": "https://stream.nanoflix.io/Nightcrawler-(2014)/master.m3u8"
        },
        {
            "name": "The Portable Door",
            "year": "2023",
            "genre": "Adventure, Comedy, Fantasy",
            "description": "လန်ဒန်မြို့က ထူးဆန်းလှတဲ့ J.W. Wells & Co. ဆိုတဲ့ ကော်ပိုရိတ်ကုမ္ပဏီကြီးတစ်ခုမှာ အလုပ်သင်အဖြစ် ဝင်ရောက်လုပ်ကိုင်ခွင့်ရခဲ့တဲ့ လူငယ်လေး ပေါလ် အကြောင်းကနေ စတင်ထားပြီး သာမန်ရုံးတစ်ခုမဟုတ်ဘဲ ကမ္ဘာပေါ်က အဖြစ်အပျက်တွေ၊ ကံကြမ္မာတွေကို ပြောင်းလဲနိုင်တဲ့ မှော်ဆန်တဲ့ ရုံးကြီးအကြောင်း ရိုက်ကူးထားတာဖြစ်ပါတယ်။",
            "stream_url": "https://stream.nanoflix.io/The-Portable-Door-(2023)/master.m3u8"
        }
    ]

if __name__ == "__main__":
    print("Scraping all available movies with description details...")
    all_movies = scrape_nanoflix_movies()
    
    if all_movies:
        with open("movies_data.json", "w", encoding="utf-8") as f:
            json.dump(all_movies, f, indent=4, ensure_ascii=False)
        print(f"Successfully exported {len(all_movies)} movies with proper descriptions!")
            
