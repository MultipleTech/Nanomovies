import requests
import json
import re

def get_movies_data():
    # နည်းလမ်း ၁ - Nanoflix ရဲ့ Backend Movie List API Endpoint
    # (မှတ်ချက် - website ရဲ့ Developer Tools Network Tab အရ အသုံးပြုသော API ဖြစ်သည်)
    api_url = "https://api.nanoflix.io/v1/movies" 
    
    # တကယ်လို့ အပေါ်က API က အလုပ်မလုပ်ရင် Backup အနေနဲ့ သုံးဖို့ စာရင်းကို အောက်မှာ ကြိုထည့်ထားပေးလို့ရပါတယ်
    backup_url = "https://nanoflix.io/api/movies"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://nanoflix.io/"
    }
    
    movies_list = []
    
    try:
        print("Fetching data from Nanoflix API...")
        response = requests.get(api_url, headers=headers, timeout=15)
        
        # အကယ်၍ v1 API မရရင် backup URL ကို စမ်းမယ်
        if response.status_code != 200:
            response = requests.get(backup_url, headers=headers, timeout=15)
            
        if response.status_code == 200:
            data = response.json()
            
            # API response structure ပေါ်မူတည်ပြီး loop ပတ်မယ်
            # အများအားဖြင့် JSON က list တိုက်ရိုက် (သို့) {'data': [...]} (သို့) {'results': [...]} လာတတ်ပါတယ်
            items = data if isinstance(data, list) else data.get('data', data.get('results', []))
            
            for item in items:
                name = item.get('title') or item.get('name') or "Unknown Movie"
                year = str(item.get('year') or item.get('release_date', '2026')[:4])
                
                # Genre ယူခြင်း
                genre_data = item.get('genres') or item.get('genre') or "Movies"
                genre = ", ".join(genre_data) if isinstance(genre_data, list) else str(genre_data)
                
                description = item.get('description') or item.get('overview') or "No description available."
                
                # Stream URL ကို Format အတိုင်း တည်ဆောက်ခြင်း
                # နာမည်ထဲက Space တွေကို - ပြောင်းပြီး Stream URL ထုတ်မယ်
                formatted_name = name.replace(" ", "-")
                # special character တွေပါရင် ဖယ်ထုတ်ချင်ရင် re.sub သုံးနိုင်ပါတယ်
                formatted_name = re.sub(r'[^\w\-]', '', formatted_name)
                
                stream_url = item.get('stream_url') or f"https://stream.nanoflix.io/{formatted_name}-({year})/master.m3u8"
                
                movies_list.append({
                    "name": name,
                    "year": year,
                    "genre": genre,
                    "description": description,
                    "stream_url": stream_url
                })
        else:
            print(f"API Access Failed Status: {response.status_code}. Using fallback layout parsing...")
            # တကယ်လို့ API လုံးဝ ပိတ်ထားရင် Website HTML ကနေ ရှာတဲ့ ဒုတိယနည်းလမ်း (RegEx fallback)
            return get_movies_via_regex()
            
        return movies_list
        
    except Exception as e:
        print(f"Error accessing API: {e}")
        return get_movies_via_regex()

def get_movies_via_regex():
    """ HTML ထဲမှာ မြှုပ်ထားတဲ့ JSON Schema သို့မဟုတ် Script တဂ်တွေထဲက Data ကို RegEx နဲ့ ရှာတဲ့နည်းလမ်း """
    base_url = "https://nanoflix.io/movie/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    movies_list = []
    
    try:
        res = requests.get(base_url, headers=headers, timeout=15)
        if res.status_code == 200:
            html = res.text
            # HTML ထဲမှာ Next.js ရဲ့ ကိန်းဂဏန်း data တွေပါတဲ့ <script id="__NEXT_DATA__"> ကို ရှာဖွေခြင်း
            json_finder = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
            
            if json_finder:
                page_data = json.loads(json_finder.group(1))
                # Next.js state ထဲက movie list ပါမယ့် နေရာကို လှမ်းယူခြင်း
                props = page_data.get('props', {}).get('pageProps', {})
                items = props.get('movies') or props.get('initialData') or props.get('fallback', {}).values()
                
                # ရှာတွေ့တဲ့ items တွေကို စစ်ထုတ်ပြီး format ပြင်မယ်
                for item in items:
                    if isinstance(item, dict) and ('title' in item or 'name' in item):
                        name = item.get('title') or item.get('name')
                        year = str(item.get('year', '2026'))
                        formatted_name = name.replace(" ", "-")
                        movies_list.append({
                            "name": name,
                            "year": year,
                            "genre": item.get('genre', 'Movies'),
                            "description": item.get('description', ''),
                            "stream_url": f"https://stream.nanoflix.io/{formatted_name}-({year})/master.m3u8"
                        })
    except Exception as e:
        print(f"Regex fall back error: {e}")
        
    return movies_list

if __name__ == "__main__":
    all_movies = get_movies_data()
    
    if all_movies:
        with open("movies_data.json", "w", encoding="utf-8") as f:
            json.dump(all_movies, f, indent=4, ensure_ascii=False)
        print(f"Successfully generated movies_data.json with {len(all_movies)} movies!")
    else:
        # လုံးဝမရခဲ့ရင် JSON ဗလာမဖြစ်အောင် နမူနာ တစ်ခု ထည့်ပေးထားမယ်
        sample_data = [{
            "name": "Ghajini",
            "year": "2008",
            "genre": "Action, Romance",
            "description": "Ghajini (2008) Movie stream details.",
            "stream_url": "https://stream.nanoflix.io/Ghajini-(2008)/master.m3u8"
        }]
        with open("movies_data.json", "w", encoding="utf-8") as f:
            json.dump(sample_data, f, indent=4, ensure_ascii=False)
        print("Generated with backup sample data.")
                
