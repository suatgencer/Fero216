import math
import re
from keywords import TECH_KEYWORDS

def has_tech_keyword(text):
    if not text:
        return False
    for kw in TECH_KEYWORDS:
        pattern = rf"\b{re.escape(kw)}\b"
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def get_tech_comments(raw_comments):
    return [c for c in raw_comments if has_tech_keyword(c)]

def calculate_tis(top_10):
    tis_scores = []
    for v in top_10:
        views = max(v.get('views', 1), 1)
        likes = v.get('likes', 0)
        comments = v.get('comments', 0)
        
        ter = ((likes * 1) + (comments * 3)) / views * 100
        tis = ter * math.log10(views)
        tis_scores.append(tis)
        
    if len(tis_scores) > 0:
        return sum(tis_scores) / len(tis_scores)
    return 0

def get_tis_status(tis):
    if tis >= 35:
        return "Mükemmel (Viral / Lider)", "🔥"
    elif tis >= 25:
        return "Çok İyi (Güçlü Etki)", "🟢"
    elif tis >= 18:
        return "İyi (Potansiyelli)", "🟡"
    elif tis >= 10:
        return "Orta (Standart)", "🟠"
    else:
        return "Kötü (Riskli)", "🔴"

# DİKKAT: ai_consultation parametresi formülden çıkarıldı, yerine teknik yorum hacmi geldi.
def calculate_kols(top_10, creator_replies, tech_comments_count):
    # 1. Niche Hesaplama (%30)
    niche_count = 0
    for v in top_10:
        title = str(v.get('title', ''))
        desc = str(v.get('description', ''))
        if has_tech_keyword(f"{title} {desc}"):
            niche_count += 1
            
    niche_score = 0
    if len(top_10) > 0:
        niche_score = (niche_count / len(top_10)) * 100
        
    # 2. Teknik Yorum Hacmi Skoru (%40) - YENİ MANTIK
    # 200 teknik yorum tavan kabul ediliyor. (Örn: 100 yorum = 50 Puan)
    volume_score = min(100, (tech_comments_count / 200) * 100)
    
    # 3. Yönlendirme ve Rehberlik (%30)
    safe_tech = max(tech_comments_count, 1)
    guidance_score = min(100, (creator_replies / safe_tech) * 100)
    
    return (niche_score * 0.30) + (volume_score * 0.40) + (guidance_score * 0.30)

def calculate_3d_matrix(top_10, kols_score):
    if not top_10:
        return 0, 0, 0
        
    # 1. Erişim Gücü Skoru (Tavan 100.000 İzlenme = 100 Puan)
    total_views_for_avg = sum(v.get('views', 0) for v in top_10)
    avg_views = total_views_for_avg / len(top_10)
    reach_score = min(100, (avg_views / 100000) * 100)

    # 2. Etkileşim Derinliği (TER) Skoru (Tavan %10 Etkileşim = 100 Puan)
    total_views = sum(max(v.get('views', 1), 1) for v in top_10)
    total_engagements = sum(v.get('likes', 0) + v.get('comments', 0) for v in top_10)
    
    avg_ter = 0
    if total_views > 0:
        avg_ter = (total_engagements / total_views) * 100
        
    engagement_score = min(100, (avg_ter / 10) * 100)

    # 3. Nihai Influencer Skoru
    final_score = (reach_score * 0.30) + (engagement_score * 0.30) + (kols_score * 0.40)
    
    return reach_score, engagement_score, final_score

def get_campaign_suitability(final_score):
    if final_score >= 80:
        return "Yıldız (Kesinlikle Çalışılmalı)", "success", "🌟"
    elif final_score >= 60:
        return "Çok İyi (Güçlü Alternatif)", "info", "🔵"
    elif final_score >= 40:
        return "Ortalama (Değerlendirilebilir)", "warning", "🟡"
    else:
        return "Riskli (Uzak Durulmalı)", "error", "🔴"
