import streamlit as st
import pandas as pd
from api_service import get_channel_info, get_videos_and_stats, get_comments_and_replies, comprehensive_ai_analysis, generate_influencer_summary
from metrics import calculate_tis, get_tis_status, calculate_kols, get_tech_comments, calculate_3d_matrix, get_campaign_suitability

st.set_page_config(page_title="KOL & Etki Analizi", page_icon="📸", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.warning("🔒 Bu araç sadece ekip kullanımına özeldir.")
    entered_password = st.text_input("Lütfen Takım Şifresini Girin:", type="password")
    
    if st.button("Giriş Yap"):
        if entered_password == st.secrets.get("SIFRE"):
            st.session_state.authenticated = True
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()
        else:
            st.error("❌ Hatalı şifre! Lütfen tekrar deneyin.")
    st.stop()

YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY")
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")

st.title("📸 Influencer & KOL Analiz Radarı")
st.markdown("Fujifilm Türkiye - Sektörel Etki ve Fikir Liderliği Ölçüm Aracı")
st.divider()

channel_input = st.text_input("YouTube Kanal ID veya @KullanıcıAdı Girin:", placeholder="Örn: @cicekileteknoloji")

if st.button("Analizi Başlat", type="primary"):
    if channel_input:
        
        # 1. AŞAMA: VERİ ÇEKME
        with st.spinner("Sektörel radar devrede. API'den veriler çekiliyor..."):
            ch_data = get_channel_info(channel_input, YOUTUBE_API_KEY)
            if not ch_data:
                st.error("Kanal bulunamadı.")
                st.stop()
                
            ch_title = str(ch_data['snippet'].get('title', 'Bilinmeyen Kanal'))
            ch_subs = int(ch_data['statistics'].get('subscriberCount', 0))
            ch_id = ch_data['id']
            
            try:
                uploads_id = ch_data['contentDetails']['relatedPlaylists']['uploads']
            except KeyError:
                st.error("Kanalın video listesine ulaşılamıyor.")
                st.stop()
            
            all_videos, top_10 = get_videos_and_stats(uploads_id, YOUTUBE_API_KEY, 50)
            if not top_10:
                st.warning("Uygun VOD video bulunamadı.")
                st.stop()

            vid_ids = [v['id'] for v in top_10]
            raw_comments, creator_replies = get_comments_and_replies(vid_ids, ch_id, YOUTUBE_API_KEY)
            
        # 2. AŞAMA: HESAPLAMALAR VE YAPAY ZEKA
        with st.spinner("Yapay Zeka yorumları inceliyor ve 3 Boyutlu Matris hesaplanıyor..."):
            
            # Önce TIS ve Etiketini hesaplıyoruz (Yapay zekaya göndermek için)
            avg_tis = calculate_tis(top_10)
            tis_label, tis_icon = get_tis_status(avg_tis)
            
            tech_comments = get_tech_comments(raw_comments)
            tech_comments_count = len(tech_comments)
            
            ai_data = comprehensive_ai_analysis(tech_comments if tech_comments else raw_comments, OPENAI_API_KEY)
            purchase_intent_count = ai_data.get("purchase_intent", 0)
            
            kols_score = calculate_kols(top_10, creator_replies, tech_comments_count)
            reach_score, engagement_score, final_score = calculate_3d_matrix(top_10, kols_score)
            uygunluk, renk, ikon = get_campaign_suitability(final_score)
            
            # STRATEJİST YAPAY ZEKAYI ÇAĞIRIYORUZ (Sadece istediğimiz 4 metrik ve TIS etiketiyle)
            ai_summary_text = generate_influencer_summary(
                ch_title, final_score, reach_score, kols_score, avg_tis, tis_label, OPENAI_API_KEY
            )

        # 3. AŞAMA: EKRANA ÇİZDİRME
        st.divider()
        st.subheader(f"Analiz Raporu: {ch_title}")
        
        # YAPAY ZEKA YÖNETİCİ ÖZETİ KUTUSU
        st.info(f"💡 **Ürün Konumlandırma Stratejisi:**\n\n{ai_summary_text}")
        st.write("")
        
        # --- ÜST PANEL ---
        top_col1, top_col2, top_col3 = st.columns([1, 1, 2])
        top_col1.caption("🌟 Influencer Skoru (0-100)")
        top_col1.subheader(f"{final_score:.2f}")
        
        top_col2.caption("👥 Toplam Takipçi")
        top_col2.subheader(f"{ch_subs:,}")
        
        with top_col3:
            st.write("")
            if renk == "success": st.success(f"{ikon} Kampanya Uygunluğu: {uygunluk}")
            elif renk == "info": st.info(f"{ikon} Kampanya Uygunluğu: {uygunluk}")
            elif renk == "warning": st.warning(f"{ikon} Kampanya Uygunluğu: {uygunluk}")
            else: st.error(f"{ikon} Kampanya Uygunluğu: {uygunluk}")
            
        st.divider()
        
        # --- ORTA PANEL ---
        st.markdown("### 📊 3 Boyutlu Performans Matrisi")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        
        m_col1.caption("📈 Erişim Gücü (%30)")
        m_col1.subheader(f"{reach_score:.2f} / 100")
        
        m_col2.caption("🤝 Etkileşim (TER) (%30)")
        m_col2.subheader(f"{engagement_score:.2f} / 100")
        
        m_col3.caption("🧠 KOLs (Otorite) (%40)")
        m_col3.subheader(f"{kols_score:.2f} / 100")
        
        with m_col4:
            st.caption("🔍 TIS (Gerçek Etki)")
            st.subheader(f"{avg_tis:.2f}")
            st.markdown(f"{tis_icon} *{tis_label}*")

        st.divider()
        
        # --- ALT PANEL ---
        bot_col1, bot_col2 = st.columns([3, 2])
        with bot_col1:
            st.markdown("📌 **Son 10 Gönderinin (Sadece VOD) Detaylı Analizi:**")
            df = pd.DataFrame(top_10)[['title', 'views', 'likes', 'comments', 'shares']]
            df.columns = ["Video Başlığı", "İzlenme", "Beğeni", "Yorum", "Paylaşım"]
            
            for col in ["İzlenme", "Beğeni", "Yorum", "Paylaşım"]:
                df[col] = df[col].apply(lambda x: f"{x:,}".replace(",", "."))
                
            st.dataframe(df, hide_index=True, use_container_width=True)
            
        with bot_col2:
            st.markdown("### 🤖 Yapay Zeka Kitle Analizi")
            st.caption("Takipçi Kalitesi (Gerçek Yorum Oranı)")
            st.subheader(f"%{ai_data.get('real_ratio', 0)}")
            
            st.caption("Satın Alma Niyeti (Potansiyel Müşteri)")
            st.subheader(f"{purchase_intent_count} Adet")
            
            st.write("")
            st.markdown("📌 **Duygu Analizi Dağılımı:**")
            chart_data = pd.DataFrame({
                "Duygu": ["Negatif", "Nötr", "Pozitif"],
                "Yüzde": [ai_data.get('neg', 0), ai_data.get('neu', 0), ai_data.get('pos', 0)]
            })
            st.bar_chart(chart_data.set_index("Duygu"))
