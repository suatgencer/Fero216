import streamlit as st
import pandas as pd
import numpy as np
import random
import json
import requests
from openai import OpenAI

# 1. SAYFA AYARLARI EN ÜSTTE OLMALI
st.set_page_config(page_title="Influencer Etki Analizi", page_icon="📸", layout="wide")

# 2. ŞİFRE KONTROL EKRANI (KAPI GÖREVLİSİ)
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.warning("🔒 Bu araç sadece ekip kullanımına özeldir.")
    
    # Kullanıcıdan şifre iste
    entered_password = st.text_input("Lütfen Takım Şifresini Girin:", type="password")
    
    if st.button("Giriş Yap"):
        # Girilen şifreyi Secrets dosyasındakiyle karşılaştır
        correct_password = st.secrets.get("SIFRE")
        
        if entered_password == correct_password:
            st.session_state.authenticated = True
            st.rerun() # Şifre doğruysa sayfayı yenile ve içeri al
        else:
            st.error("❌ Hatalı şifre! Lütfen tekrar deneyin.")
            
    # Şifre girilene kadar kodun GERİ KALANINI ÇALIŞTIRMA!
    st.stop()

class InfluencerAnalyzer:
    def __init__(self, openai_api_key=None, youtube_api_key=None):
        # Save metriği kaldırıldı, sadece geçerli metriklerin ağırlıkları kaldı
        self.w_like = 1
        self.w_comment = 2
        self.w_share = 3
        
        self.api_key = openai_api_key
        self.youtube_api_key = youtube_api_key
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def fetch_youtube_data(self, channel_handle):
        if not self.youtube_api_key:
            return {"error": "YouTube API anahtarı bulunamadı!"}

        try:
            clean_api_key = self.youtube_api_key.strip()
            handle = channel_handle.replace("@", "").strip()
            
            # 1. Kanal Bilgilerini Çek
            channel_url = f"https://youtube.googleapis.com/youtube/v3/channels?part=statistics,contentDetails&forHandle={handle}&key={clean_api_key}"
            channel_response = requests.get(channel_url).json()
            
            if "error" in channel_response:
                return {"error": f"YouTube API İsteği Reddedildi: {channel_response['error']['message']}"}

            if "items" not in channel_response:
                return {"error": f"Kanal bulunamadı. Aranan isim: @{handle}"}
                
            channel_data = channel_response["items"][0]
            followers = int(channel_data["statistics"]["subscriberCount"])
            uploads_playlist_id = channel_data["contentDetails"]["relatedPlaylists"]["uploads"]

            # 2. Son 10 Videonun ID'lerini Çek
            playlist_url = f"https://youtube.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={uploads_playlist_id}&maxResults=10&key={clean_api_key}"
            playlist_response = requests.get(playlist_url).json()
            video_ids = [item["contentDetails"]["videoId"] for item in playlist_response.get("items", [])]

            # 3. Bu 10 Videonun İstatistiklerini ve Başlıklarını Çek (snippet eklendi)
            posts = []
            if video_ids:
                videos_url = f"https://youtube.googleapis.com/youtube/v3/videos?part=statistics,snippet&id={','.join(video_ids)}&key={clean_api_key}"
                videos_response = requests.get(videos_url).json()
                
                for video in videos_response.get("items", []):
                    stats = video.get("statistics", {})
                    snippet = video.get("snippet", {})
                    posts.append({
                        "title": snippet.get("title", "Bilinmeyen Video"),
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                        "shares": int(stats.get("likeCount", 0)) // 10 # Paylaşım simülasyonu
                    })

            # 4. GÜÇLENDİRİLMİŞ YORUM TOPLAMA ALGORİTMASI (Son 10 Video - 15 Yorum)
            sample_comments = []
            
            for vid in video_ids:
                comments_url = f"https://youtube.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={vid}&maxResults=15&order=relevance&key={clean_api_key}"
                comments_response = requests.get(comments_url).json()
                
                if "error" in comments_response:
                    continue
                    
                for item in comments_response.get("items", []):
                    try:
                        comment_text = item["snippet"]["topLevelComment"]["snippet"]["textOriginal"]
                        sample_comments.append(comment_text)
                    except KeyError:
                        continue

            if len(sample_comments) > 150:
                sample_comments = random.sample(sample_comments, 150)

            if not sample_comments:
                sample_comments = ["Bu kanalın son videolarında yorumlar kapalı, sistem otomatik nötr puan vermiştir."]

            return {
                "username": channel_handle,
                "platform": "youtube",
                "followers": followers,
                "posts": posts, # Artık başlıkları da içeriyor
                "sample_comments": sample_comments
            }
            
        except Exception as e:
            return {"error": f"YouTube verileri çekilirken hata oluştu: {str(e)}"}

    def fetch_data(self, username, platform="instagram"):
        if platform.lower() == "youtube":
            return self.fetch_youtube_data(username)
            
        # Instagram Simülasyonunu da yeni yapıya uygun hale getirdik
        return {
            "username": username,
            "platform": platform,
            "followers": 150000,
            "posts": [
                {
                    "title": f"Instagram Gönderisi {i+1}",
                    "views": random.randint(50000, 200000),
                    "likes": random.randint(2000, 10000),
                    "comments": random.randint(50, 500),
                    "shares": random.randint(20, 300)
                } for i in range(10)
            ],
            "sample_comments": ["Harika!", "Bu lensi nereden aldınız?", "gt", "Fiyat performans nasıl?"]
        }

    def calculate_metrics(self, data):
        if "error" in data or not data.get("posts"):
            return {"error": "Metrik hesaplanacak veri bulunamadı."}

        df = pd.DataFrame(data["posts"])
        followers = data["followers"]
        
        if followers == 0:
            followers = 1
            
        total_likes = df["likes"].sum()
        total_comments = df["comments"].sum()
        total_shares = df["shares"].sum()
        total_views = df["views"].sum()

        # Save metriği formülden çıkarıldı
        weighted_engagement = (
            (self.w_like * total_likes) +
            (self.w_comment * total_comments) +
            (self.w_share * total_shares)
        )
        
        weighted_er = (weighted_engagement / (followers * 10)) * 100
        view_efficiency = (total_views / (followers * 10)) * 100

        return {
            "weighted_er_percent": round(weighted_er, 2),
            "view_efficiency_percent": round(view_efficiency, 2),
            "raw_stats": data["posts"] # Ham listeyi tablo için doğrudan döndürüyoruz
        }

    def analyze_nlp(self, comments):
        if not self.client:
            return {"error": "OpenAI API Anahtarı bulunamadı."}
        if not comments:
            return {"error": "Analiz edilecek yorum bulunamadı."}

        comments_text = "\n".join([f"- {c}" for c in comments])
        
        prompt = f"""
        Aşağıdaki sosyal medya yorumlarını analiz et. Hedef kitle genellikle fotoğrafçılık, dijital kameralar, lensler ve ekipmanlar ile ilgilenen kişiler.
        
        Yorumlar:
        {comments_text}
        
        Lütfen bu yorumları inceleyerek aşağıdaki metrikleri 0 ile 100 arasında bir yüzde (sayı) olarak hesapla:
        1. follower_quality_score: Yorumların ne kadarı gerçek, anlamlı ve konuyla ilgili? (Bot, spam, emoji odaklıları dışla).
        2. purchase_intent_score: Yorumların ne kadarında bir ürün satın alma, fiyat sorma, teknik detay öğrenme veya tavsiye isteme niyeti var?
        3. sentiment_positive: Pozitif yorum oranı.
        4. sentiment_negative: Negatif yorum oranı.
        5. sentiment_neutral: Nötr yorum oranı.

        SADECE AŞAĞIDAKİ FORMATTA GEÇERLİ BİR JSON DÖNDÜR:
        {{
            "follower_quality_score": 80,
            "purchase_intent_score": 25,
            "sentiment_positive": 60,
            "sentiment_negative": 10,
            "sentiment_neutral": 30
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sen veri analizi yapan ve sadece istenilen JSON formatında çıktı üreten bir asistansın."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:-3]
            elif result_text.startswith("```"):
                result_text = result_text[3:-3]
                
            return json.loads(result_text)
            
        except Exception as e:
            return {"error": f"OpenAI API Hatası: {str(e)}"}

    def calculate_final_score(self, metrics, nlp_results):
        if "error" in metrics or "error" in nlp_results:
            return 0, "Hesaplama Hatası"

        er_score = min(metrics.get("weighted_er_percent", 0) * 5, 100) * 0.40
        view_score = min(metrics.get("view_efficiency_percent", 0), 100) * 0.20
        quality_score = nlp_results.get("follower_quality_score", 0) * 0.20
        intent_score = min(nlp_results.get("purchase_intent_score", 0) * 3, 100) * 0.20

        final_score = er_score + view_score + quality_score + intent_score
        
        if final_score >= 75:
            suitability = "Çok İyi"
        elif final_score >= 50:
            suitability = "Ortalama"
        else:
            suitability = "Riskli"

        return round(final_score, 2), suitability


# --- WEB ARAYÜZÜ (STREAMLIT) ---
st.set_page_config(page_title="Influencer Etki Analizi", page_icon="📸", layout="wide")

st.title("📸 Influencer Etki Analiz Aracı")
st.markdown("Pazarlama kampanyaları için potansiyel influencer'ların etkileşim ve kitle kalitesini analiz edin.")

try:
    openai_key = st.secrets.get("OPENAI_API_KEY")
    youtube_key = st.secrets.get("YOUTUBE_API_KEY")
except Exception:
    openai_key = None
    youtube_key = None

if not openai_key or not youtube_key:
    st.error("⚠️ Sistem Hatası: `.streamlit/secrets.toml` dosyası eksik veya API anahtarları tanımlanmamış.")

st.sidebar.header("Analiz Ayarları")
username = st.sidebar.text_input("Kullanıcı Adı / Handle", value="@cnklgl")
platform = st.sidebar.selectbox("Platform", ["YouTube", "Instagram"])

if st.sidebar.button("Analizi Başlat"):
    if openai_key and youtube_key:
        with st.spinner(f"{username} için 10 video ve 150 yorum analiz ediliyor. Bu işlem birkaç saniye sürebilir..."):
            analyzer = InfluencerAnalyzer(openai_api_key=openai_key, youtube_api_key=youtube_key)
            
            data = analyzer.fetch_data(username, platform.lower())
            
            if "error" in data:
                st.error(data["error"])
            else:
                metrics = analyzer.calculate_metrics(data)
                nlp_results = analyzer.analyze_nlp(data["sample_comments"])
                
                if "error" in nlp_results:
                    st.error(nlp_results["error"])
                else:
                    final_score, suitability = analyzer.calculate_final_score(metrics, nlp_results)
                    
                    st.header(f"Analiz Raporu: {username}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(label="🌟 Influencer Skoru (0-100)", value=final_score)
                    with col2:
                        st.metric(label="👥 Toplam Takipçi", value=f"{data['followers']:,}")
                    with col3:
                        if suitability == "Çok İyi":
                            st.success(f"Kampanya Uygunluğu: {suitability}")
                        elif suitability == "Ortalama":
                            st.warning(f"Kampanya Uygunluğu: {suitability}")
                        else:
                            st.error(f"Kampanya Uygunluğu: {suitability}")

                    st.divider()

                    # Tablo kısmını sayfa geneline yaymak için alt alta aldık
                    col_metrics, col_nlp = st.columns(2)
                    
                    with col_metrics:
                        st.subheader("📊 Performans Metrikleri")
                        st.metric(label="Ağırlıklı Etkileşim Oranı (Weighted ER)", value=f"%{metrics.get('weighted_er_percent', 0)}")
                        st.metric(label="Görüntülenme Verimliliği", value=f"%{metrics.get('view_efficiency_percent', 0)}")

                    with col_nlp:
                        st.subheader("🧠 Yapay Zeka Kitle Analizi")
                        st.metric(label="Takipçi Kalitesi (Gerçek Yorum Oranı)", value=f"%{nlp_results.get('follower_quality_score', 0)}")
                        st.metric(label="Satın Alma Niyeti Puanı", value=f"%{nlp_results.get('purchase_intent_score', 0)}")

                    st.divider()

                    # Son 10 Video tablosu ve NLP grafiği
                    col_table, col_chart = st.columns([2, 1]) # Tabloya daha fazla genişlik (2/3 oranında) veriyoruz
                    
                    with col_table:
                        st.write("📌 **Son 10 Gönderinin Detaylı Analizi:**")
                        df_posts = pd.DataFrame(metrics.get('raw_stats', []))
                        if not df_posts.empty:
                            # Sütun isimlerini Türkçeleştirip daha şık gösteriyoruz
                            df_posts = df_posts.rename(columns={
                                "title": "Video Başlığı",
                                "views": "İzlenme",
                                "likes": "Beğeni",
                                "comments": "Yorum",
                                "shares": "Paylaşım"
                            })
                            # Tabloyu Streamlit'e bas (index gizli)
                            st.dataframe(df_posts, use_container_width=True, hide_index=True)

                    with col_chart:
                        st.write("📌 **Duygu Analizi Dağılımı:**")
                        sentiment_data = pd.DataFrame({
                            "Duygu": ["Pozitif", "Nötr", "Negatif"],
                            "Oran (%)": [nlp_results.get('sentiment_positive', 0), nlp_results.get('sentiment_neutral', 0), nlp_results.get('sentiment_negative', 0)]
                        })
                        st.bar_chart(sentiment_data.set_index("Duygu"))
