import requests
import re
import json
from openai import OpenAI

def get_channel_info(handle, api_key):
    if handle.startswith('@'): handle = handle[1:]
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=channel&q={handle}&key={api_key}"
    res = requests.get(url).json()
    if 'items' in res and len(res['items']) > 0:
        ch_id = res['items'][0]['snippet']['channelId']
        details_url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&id={ch_id}&key={api_key}"
        d_res = requests.get(details_url).json()
        if 'items' in d_res:
            return d_res['items'][0]
    return None

def is_short_video(duration_str):
    if not duration_str: return False
    h = re.search(r'(\d+)H', duration_str)
    m = re.search(r'(\d+)M', duration_str)
    s = re.search(r'(\d+)S', duration_str)
    
    hours = int(h.group(1)) if h else 0
    minutes = int(m.group(1)) if m else 0
    seconds = int(s.group(1)) if s else 0
    
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds <= 60

def get_videos_and_stats(uploads_id, api_key, max_results=50):
    valid_videos = []
    page_token = ""
    while len(valid_videos) < max_results:
        url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_id}&maxResults=50&pageToken={page_token}&key={api_key}"
        res = requests.get(url).json()
        if 'items' not in res or not res['items']: break
        
        video_ids = [item['snippet']['resourceId']['videoId'] for item in res['items']]
        v_ids_str = ",".join(video_ids)
        
        d_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,statistics,liveStreamingDetails&id={v_ids_str}&key={api_key}"
        d_res = requests.get(d_url).json()
        
        if 'items' in d_res:
            for v_item in d_res['items']:
                vid_id = v_item['id']
                title = str(v_item['snippet'].get('title', ''))
                description = str(v_item['snippet'].get('description', ''))
                duration = v_item['contentDetails'].get('duration', 'PT0S')
                
                if not ('liveStreamingDetails' in v_item) and not is_short_video(duration):
                    stats = v_item.get('statistics', {})
                    valid_videos.append({
                        'id': vid_id,
                        'title': title,
                        'description': description,
                        'views': int(stats.get('viewCount', 0)),
                        'likes': int(stats.get('likeCount', 0)),
                        'comments': int(stats.get('commentCount', 0)),
                        'shares': int(int(stats.get('likeCount', 0)) * 0.08)
                    })
                if len(valid_videos) >= max_results: break
        page_token = res.get('nextPageToken')
        if not page_token: break
    return valid_videos, valid_videos[:10]

def get_comments_and_replies(video_ids, creator_id, api_key):
    all_comments = []
    creator_replies = 0
    quota_per_video = 1000 // len(video_ids) if video_ids else 0
    carry_over = 0
    for vid in video_ids:
        target = quota_per_video + carry_over
        fetched = 0
        page_token = ""
        while fetched < target:
            max_res = min(100, target - fetched)
            url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet,replies&videoId={vid}&maxResults={max_res}&pageToken={page_token}&key={api_key}"
            res = requests.get(url).json()
            if 'items' not in res: break
            for item in res['items']:
                try:
                    all_comments.append(str(item['snippet']['topLevelComment']['snippet'].get('textDisplay', '')))
                    fetched += 1
                    if 'replies' in item:
                        for reply in item['replies']['comments']:
                            if str(reply['snippet']['authorChannelId']['value']) == str(creator_id):
                                creator_replies += 1
                                break
                except KeyError: continue
            page_token = res.get('nextPageToken')
            if not page_token: break
        carry_over = target - fetched
    return all_comments, creator_replies

def comprehensive_ai_analysis(comments, openai_key):
    if not comments:
        return {"real_ratio": 0, "purchase_intent": 0, "pos": 0, "neu": 100, "neg": 0}
    
    client = OpenAI(api_key=openai_key)
    comments_json = json.dumps(comments[:300], ensure_ascii=False)
    
    prompt = (
        "Sen katı ve objektif bir veri analistisin. Kendi yorumunu kesinlikle katma. SADECE aşağıdaki JSON formatında yanıt ver.\n\n"
        "İstenen Veriler:\n"
        "- \"real_ratio\": Gerçek insan yorumlarının yüzdesi (0-100).\n"
        "- \"purchase_intent\": Tavsiye, ürün karşılaştırması veya doğrudan satın alma sorusu soran YORUM SAYISI (Yüzde değil, mutlak Adet ver. Örn: 42, 18, 70 vb.).\n"
        "- \"pos\": Pozitif yorumların yüzdesi.\n"
        "- \"neu\": Nötr yorumların yüzdesi.\n"
        "- \"neg\": Negatif yorumların yüzdesi. (pos, neu ve neg toplamı tam 100 olmalı).\n\n"
        f"Yorumlar: {comments_json}\n\n"
        "Örnek Çıktı Formatı:\n"
        "{\"real_ratio\": 80, \"purchase_intent\": 70, \"pos\": 60, \"neu\": 30, \"neg\": 10}"
    )
    
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        print(f"Yapay Zeka Hatası: {e}")
        return {"real_ratio": 50, "purchase_intent": 0, "pos": 33, "neu": 34, "neg": 33}

def generate_influencer_summary(ch_title, final_score, reach_score, kols_score, avg_tis, tis_label, openai_key):
    client = OpenAI(api_key=openai_key)
    
    prompt = f"""
    Sen kıdemli bir Fujifilm marka ve influencer pazarlama stratejistisin. 
    Aşağıda '{ch_title}' adlı YouTube kanalının metrikleri bulunuyor.
    
    Kanal Verileri:
    - Nihai Influencer Skoru (0-100): {final_score:.2f}
    - Erişim Gücü Skoru (0-100): {reach_score:.2f}
    - Fikir Liderliği / KOLs Skoru (0-100): {kols_score:.2f}
    - TIS (Gerçek Etki) Skoru: {avg_tis:.2f} (Sistemimize göre bu TIS skorunun başarı durumu: {tis_label})
    
    Görev:
    Bu verileri analiz ederek, kanalın HANGİ SEGMENT ürünlerin tanıtımı için uygun olduğunu belirten 4 veya 5 cümlelik stratejik bir yönetici özeti yaz.
    
    Strateji ve Yorum Kuralları:
    1. TIS skoru için kesinlikle "düşük" veya "yetersiz" gibi kendi yorumlarını katma. Sana verdiğim "{tis_label}" durumunu doğru kabul et.
    2. Eğer KOLs (Fikir Liderliği) ve Nihai Skor yüksekse: Bu kanal tam bir sektörel otoritedir ve profesyonellere hitap eder. Üst segment (Premium/Pro) ürünler (Örn: GFX serisi, X-H2, Cine lensler) için biçilmiş kaftandır de.
    3. Eğer TIS skoru ve Erişimi yüksek, ancak KOLs skoru düşük/ortalama ise: Bu kanal genel tüketiciye hitap eder. Daha geniş kitlelerin kullanacağı giriş seviyesi, lifestyle veya genel vlogger ürünleri (Örn: Instax, X-S20, X-A7) tanıtımları için kullanılmalıdır de.
    4. Hem TIS hem KOLs yüksekse: Sektörü domine eden amiral gemisi lansmanları (Örn: X-T5) için kitlesel bir güçtür de.
    5. Asla etkileşim derinliği, yorum sayıları veya satın alma niyetinden bahsetme. Sadece elindeki 4 metriği ürün stratejisine çevir.
    
    Sadece özeti düz metin olarak ver. Markdown veya başlık kullanma. Profesyonel, vizyoner ve doğrudan aksiyona yönelik bir dil kullan.
    """
    
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return "Yapay zeka özet metni oluşturulurken bir bağlantı sorunu yaşandı."
