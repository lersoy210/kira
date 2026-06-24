import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# Sayfa Yapılandırması
st.set_page_config(layout="wide", page_title="Kira Portal Yönetim Sistemi")

# Başlık ve Stil Açıklaması
st.title("🌐 Kira Portalı - Dijital Mülk ve Yönetim Sistemi")
st.write("Profesyonel kira yönetim paneli. Excel/CSV dosyanızı yükleyerek tüm portföyünüzü, tahsilatlarınızı ve gecikmeleri anlık takip edin.")

# Dosya Yükleme Alanı
uploaded_file = st.file_uploader("📂 Güncel Kira Listenizi Yükleyin (.csv veya .xlsx)", type=["csv", "xlsx"])

# Veri Temizleme ve Formatlama Fonksiyonu
@st.cache_data
def process_kira_data(file):
    try:
        if file.name.endswith('.xlsx'):
            df = pd.read_excel(file, header=None)
        else:
            df = pd.read_csv(file, header=None)
        
        # Başlıkları ayarla (İndeks 1'deki satır)
        df.columns = [str(c).strip() for c in df.iloc[1]]
        df = df[2:].reset_index(drop=True)
        
        # Kolon ismini standartlaştır
        df = df.rename(columns={df.columns[1]: "MÜLK_KIRACI"})
        
        # Tamamen boş veya ara başlık satırlarını temizle
        df = df[df["MÜLK_KIRACI"].notna() & (df["MÜLK_KIRACI"] != "")]
        df = df[df["K:D:"] != "K:D:"]
        
        # Sayısal veri temizliği (Kira Bedeli ve Ödenmeyen sütunları için)
        def clean_money(val):
            if pd.isna(val) or val == "": return 0.0
            val_str = str(val).replace("TL", "").replace(".", "").replace(",", ".").strip()
            try:
                return float(val_str)
            except:
                return 0.0

        df["KİRA BEDELİ"] = df["KİRA BEDELİ"].apply(clean_money)
        
        # ÖDENMEYEN sütunundaki "HAYIR İŞİ" vb. sözel ifadeleri korumak için yeni bir borç kolonu oluşturalım
        def extract_debt(val, price):
            val_str = str(val).strip().upper()
            if "HAYIR" in val_str or "VEFAT" in val_str:
                return 0.0
            try:
                return float(val_str.replace(".", "").replace(",", "."))
            except:
                # Eğer boşsa veya başka bir not varsa kira bedeli kadar borç varsayma (Ödeme durumuna göre alt tarafta işlenecek)
                return 0.0
                
        df["TEMİZ_BORÇ"] = df.apply(lambda row: extract_debt(row.get("ÖDENMEYEN", 0), row["KİRA BEDELİ"]), axis=1)
        
        return df
    except Exception as e:
        st.error(f"Veri işlenirken bir hata oluştu: {e}")
        return pd.DataFrame()

# Ana Akış
if uploaded_file is not None:
    df = process_kira_data(uploaded_file)
    
    if not df.empty:
        # --- 1. FİNANSAL GÖSTERGE PANELİ (KPI DASHBOARD) ---
        st.markdown("### 📊 Finansal Durum Panosu")
        
        # Hesaplamalar
        toplam_mulk = len(df)
        
        # Hayır işleri hariç potansiyel ciro
        toplam_potansiyel_ciro = df["KİRA BEDELİ"].sum()
        
        # Tablodaki ödenmeyen veya borç durum analizi
        toplam_gecikmiş_borc = df["TEMİZ_BORÇ"].sum()
        
        # Cari Ay Analizi (Örn: Haziran)
        # Tablonuzdaki '+' işaretlerine bakarak tahsilat oranını ölçüyoruz
        aylar = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]
        current_month_name = "HAZİRAN" # Dosyanızdaki en güncel aktif ay
        
        # Aktif ayda kaç kişi ödeme yapmış?
        odeme_yapanlar = df[df[current_month_name].astype(str).str.strip() == "+"]
        toplam_tahsil_edilen = odeme_yapanlar["KİRA BEDELİ"].sum()
        
        tahsilat_orani = (toplam_tahsil_edilen / toplam_potansiyel_ciro * 100) if toplam_potansiyel_ciro > 0 else 0

        # Metrik Kutuları
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🏠 Toplam Portföy", f"{toplam_mulk} Birim")
        m2.metric("💰 Aylık Toplam Ciro Hedefi", f"{toplam_potansiyel_ciro:,.0f} TL")
        m3.metric("✅ Bu Ay Tahsil Edilen", f"{toplam_tahsil_edilen:,.0f} TL", f"%{tahsilat_orani:.1f} Tahsilat Oranı")
        m4.metric("⚠️ Toplam Geciken/Kalan Borç", f"{toplam_gecikmiş_borc:,.0f} TL", delta="-Aksiyon Gerekli", delta_color="inverse")
        
        st.markdown("---")
        
        # --- 2. UYARI VE KRİTİK İŞLEMLER MERKEZİ ---
        st.markdown("### 🔔 Kira Portal Akıllı Bildirimler")
        col_u1, col_u2 = st.columns(2)
        
        with col_u1:
            st.warning("⚠️ **Geciken Ödemeler (Acil Aranması Gerekenler):**")
            # Hem borcu olan hem de bu ay '+' konulmamış kişileri süz
            gecikenler = df[(df["TEMİZ_BORÇ"] > 0) | ((df[current_month_name].isna()) & (df["KİRA BEDELİ"] > 0))]
            gecikenler_temiz = gecikenler[~gecikenler["ÖDENMEYEN"].astype(str).str.contains("HAYIR|VEFAT", case=False, na=False)]
            
            if not gecikenler_temiz.empty:
                for idx, row in gecikenler_temiz.head(5).iterrows():
                    st.write(f"• **{row['MÜLK_KIRACI']}** ({row['K:D:']}) - Tel: {row['TELEFON']} — *Kira Günü: {row['KİRA GÜNÜ']}*")
            else:
                st.success("Harika! Bu ay ödemesi geciken kritik bir kiracı bulunmuyor.")
                
        with col_u2:
            st.info("🤝 **Özel Statülü Mülkler & Notlar:**")
            # Hayır işi veya özel durum içeren notlar
            ozel_durumlar = df[df["ÖDENMEYEN"].astype(str).str.contains("HAYIR|VEFAT|SORALIM", case=False, na=False)]
            if not ozel_durumlar.empty:
                for idx, row in ozel_durumlar.iterrows():
                    st.write(f"• **{row['MÜLK_KIRACI']}** — Durum: `{row['ÖDENMEYEN']}`")
            else:
                st.write("Özel not bırakılan mülk bulunmuyor.")

        st.markdown("---")

        # --- 3. GELİŞMİŞ FİLTRELİ TABLO VE ARAMA MOTORU ---
        st.markdown("### 🔍 Detaylı Portföy ve Kiracı Sorgulama")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            search = st.text_input("Kiracı adı, telefon numarası veya bina kodu yazın:")
        with c2:
            durum_filtresi = st.selectbox("Ödeme Durumu (Bu Ay):", ["Hepsi", "Ödeyenler (+)", "Ödemeyenler / Bekleyenler"])
        with c3:
            # Bina/Grup tespiti (Örn: Gökçe Apt, Plaza vb.)
            df["Bina_Grubu"] = df["K:D:"].fillna("Diğer")
            bina_list = ["Hepsi"] + list(df["Bina_Grubu"].unique()[:10]) # İlk 10 grubu listele
            secilen_bina = st.selectbox("Mülk Tipi / Blok:", bina_list)

        # Filtreleme Mantığı
        f_df = df.copy()
        if search:
            f_df = f_df[f_df["MÜLK_KIRACI"].astype(str).str.contains(search, case=False) | f_df["TELEFON"].astype(str).str.contains(search, case=False)]
        if durum_filtresi == "Ödeyenler (+)":
            f_df = f_df[f_df[current_month_name].astype(str).str.strip() == "+"]
        elif durum_filtresi == "Ödemeyenler / Bekleyenler":
            f_df = f_df[f_df[current_month_name].isna() | (f_df[current_month_name] == "")]
        if secilen_bina != "Hepsi":
            f_df = f_df[f_df["Bina_Grubu"] == secilen_bina]

        # Tabloyu Ekrana Basma
        show_cols = ["K:D:", "MÜLK_KIRACI", "TELEFON", "KİRA GÜNÜ", "KİRA BEDELİ", "OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "ÖDENMEYEN"]
        st.dataframe(f_df[show_cols].fillna(""), use_container_width=True)

        # --- 4. KİRACI CARİ KARTI VE WHATSAPP ENTEGRASYONU ---
        st.markdown("---")
        st.markdown("### 👤 Kiracı Cari Kartı ve İletişim Merkezi")
        
        tenant = st.selectbox("Yönetmek istediğiniz kiracıyı seçin:", df["MÜLK_KIRACI"].unique())
        
        if tenant:
            t_data = df[df["MÜLK_KIRACI"] == tenant].iloc[0]
            
            col_card1, col_card2 = st.columns(2)
            with col_card1:
                st.markdown(f"**🏠 Mülk Detayı:** {t_data['K:D:']}")
                st.markdown(f"**📅 Kira Sözleşme Bilgisi:** {t_data['KİRA GÜNÜ']}")
                st.markdown(f"**📞 Kayıtlı Telefon:** {t_data['TELEFON']}")
            with col_card2:
                st.markdown(f"**💰 Güncel Kira Bedeli:** {t_data['KİRA BEDELİ']:,.0f} TL")
                st.markdown(f"**🚨 Ödenmeyen/Borç Durumu:** {t_data['ÖDENMEYEN'] if pd.notna(t_data['ÖDENMEYEN']) else 'Borç Yok'}")

            # Kira Portal Tarzı Tek Tıkla WhatsApp Hatırlatma Mesajı Oluşturma
            raw_phone = str(t_data['TELEFON']).replace(" ", "")
            if raw_phone and raw_phone != "nan":
                # Türkiye kodu ekleme adımı
                if not raw_phone.startswith("90") and raw_phone.startswith("0"):
                    phone_formatted = "9" + raw_phone
                elif not raw_phone.startswith("90"):
                    phone_formatted = "90" + raw_phone
                else:
                    phone_formatted = raw_phone
                
                # Dinamik Mesaj Şablonu
                mesaj = f"Merhaba {t_data['MÜLK_KIRACI']}, {t_data['K:D:']} adresindeki mülkümüzün kira ödeme dönemi yaklaşmıştır/gecikmiştir. Güncel kira bedeliniz {t_data['KİRA BEDELİ']:,.0f} TL'dir. İyi günler dileriz."
                msg_encoded = pd.Series([mesaj]).str.replace(' ', '%20').iloc[0]
                whatsapp_url = f"https://api.whatsapp.com/send?phone={phone_formatted}&text={msg_encoded}"
                
                st.markdown(f"[💬 {t_data['MÜLK_KIRACI']} İsimli Kiracıya WhatsApp'tan Hatırlatma Gönder]({whatsapp_url})")

else:
    st.info("💡 Kira Portal sistemini deneyimlemek için lütfen yukarıdaki alana 'KİRACI LİSTE.csv' veya '.xlsx' dosyanızı sürükleyin.")
