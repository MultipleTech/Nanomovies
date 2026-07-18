import requests
from bs4 import BeautifulSoup
import json
import re

def get_movies_data():
    # ရုပ်ရှင်စာရင်းရှိတဲ့ ပင်မ URL (Page 1 ကနေ စဆွဲမယ်)
    base_url = "https://nanoflix.io/movie/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    movies_list = []
    
    try:
        response = requests.get(base_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Failed to connect website: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Nanoflix ရဲ့ HTML structure အလိုက် movie item တွေကို ရှာဖွေခြင်း
        # (မှတ်ချက်- website structure အပြောင်းအလဲပေါ်မူတည်၍ selector ပြင်နိုင်သည်)
        movie_items = soup.find_all('div', class_='movie-item') # သို့မဟုတ် သက်ဆိုင်ရာ card class
        
        if not movie_items:
            # တကယ်လို့ class မတူရင် tag အလိုက် ရှာတဲ့ backup နည်းလမ်း
            movie_items = soup.find_all('article') or soup.find_all('div', class_='poster')
            
        print(f"Found {len(movie_items)} movies on page.")
        
        for item in movie_items:
            try:
                # ၁။ နာမည် ရယူခြင်း
                name_tag = item.find('h2') or item.find('h3') or item.find('a')
                name = name_tag.text.strip() if name_tag else "Unknown"
                
                # ၂။ ဇာတ်ကား အသေးစိတ် link
                detail_link = name_tag['href'] if name_tag and name_tag.has_attr('href') else ""
                
                # ၃။ ဇာတ်လမ်းအကျဉ်း Description
                desc_tag = item.find('div', class_='description') or item.find('p')
                description = desc_tag.text.strip() if desc_tag else "No description available."
                
                # ၄။ ခုနှစ်နှင့် အမျိုးအစား (Year & Genre)
                # စာသားထဲကနေ ၂၀၀၀ ကနေ ၂၀၃၀ ကြား ခုနှစ်ကို ပုံစံထုတ်ရှာမယ်
                meta_text = item.text
                year_match = re.search(r'\b(19\d\d|20[0-2]\d|2030)\b', meta_text)
                year = year_match.group(0) if year_match else "2026"
                
                # Genre ခွဲထုတ်ခြင်း (ဥပမာ- Action, Comedy, Drama)
                genres = []
                for g in ["Action", "Comedy", "Drama", "Thriller", "Horror", "Sci-Fi", "Romance", "Fantasy", "Mystery"]:
                    if g.lower() in meta_text.lower():
                        genres.append(g)
                genre = ", ".join(genres) if genres else "Movies"
                
                # ၅။ Stream URL တည်ဆောက်ခြင်း
                # Format: https://stream.nanoflix.io/Movie-Name-(Year)/master.m3u8
                formatted_name = name.replace(" ", "-")
                stream_url = f"https://stream.nanoflix.io/{formatted_name}-({year})/master.m3u8"
                
                # Data စုစည်းမှု
                movie_data = {
                    "name": name,
                    "year": year,
                    "genre": genre,
                    "description": description,
                    "stream_url": stream_url
                }
                
                movies_list.append(movie_data)
                
            except Exception as e:
                print(f"Skipping an item due to error: {e}")
                continue
                
        return movies_list
        
    except Exception as e:
        print(f"Scraping Error: {e}")
        return []

# Run ပြီး JSON ထုတ်မယ်
if __name__ == "__main__":
    all_movies = get_movies_data()
    
    if all_movies:
        with open("movies_data.json", "w", encoding="utf-8") as f:
            json.dump(all_movies, f, indent=4, ensure_ascii=False)
        print("Successfully generated movies_data.json!")
    else:
        print("No data collected.")
              
