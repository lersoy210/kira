import streamlit as st
import pandas as pd

# Sayfa Genişlik Ayarı
st.set_page_config(layout="wide", page_title="Kira Takip Sistemi")

st.title("🏢 Kira Takip ve Yönetim Portalı")
st.write("Kira takip dosyanızı (.csv veya .xlsx) yükleyerek sistemi hemen kullanmaya başlayabilirsiniz.")

# --- ARABİRİMDEN DOSYA YÜKLEME ALANI ---
uploaded_file = st.file_uploader("📂 Kira Listesi Dosyasını Seçin", type=["csv", "xlsx"])


# --- DOSYAYI OKUMA FONKSİYONU ---
@st.cache_data
def load_uploaded_data(file):
    try:
        # Yüklenen dosyanın uzantısına göre doğru okuma yöntemini seçiyoruz
        if file.name.endswith('.xlsx'):
            df = pd.read_excel(file, header=None)
        else:
            df = pd.read_csv(file, header=None)

        # Sütun başlıklarını tablonun yapısına göre (2. satır - indeks 1) ayarlayalım
        df.columns = [str(c).strip() for c in df.iloc[1]]
        # Başlık üstündeki satırları temizleyelim
        df = df[2:].reset_index(drop=True)

        # 2. sütunu standart bir isme çevirelim (MÜLK / KİRACI)
        df = df.rename(columns={df.columns[1]: "MÜLK / KİRACI"})

        # Tamamen boş veya geçersiz satırları filtrele
        df = df[df["MÜLK / KİRACI"].notna() & (df["MÜLK / KİRACI"] != "")]
        df = df[df["K:D:"] != "K:D:"]

        return df
    except Exception as e:
        st.error(f"Dosya işlenirken bir hata oluştu! Lütfen dosya formatını kontrol edin. Hata: {e}")
        return pd.DataFrame()


# Eğer kullanıcı dosya yüklediyse işlemleri başlat
if uploaded_file is not None:
    df = load_uploaded_data(uploaded_file)

    if not df.empty:
        # --- ÖZET GÖSTERGELER (KPI) ---
        total_records = len(df)
        has_phone = df[df["TELEFON"].notna() & (df["TELEFON"] != "")]

        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="📊 Toplam Kayıt Sayısı", value=total_records)
        with col2:
            st.metric(label="📞 Telefonu Kayıtlı Kiracı", value=len(has_phone))

        st.markdown("---")

        # --- FİLTRELER VE ARAMA ---
        st.subheader("🔍 Kiracı Filtreleme ve Arama")
        search_query = st.text_input("Kiracı Adı, Telefon veya Konum (K:D:) girerek arayın:")

        filtered_df = df.copy()
        if search_query:
            filtered_df = filtered_df[
                filtered_df["MÜLK / KİRACI"].astype(str).str.contains(search_query, case=False) |
                filtered_df["TELEFON"].astype(str).str.contains(search_query, case=False) |
                filtered_df["K:D:"].astype(str).str.contains(search_query, case=False)
                ]

        # --- VERİ TABLOSU ---
        st.subheader("📋 Güncel Kiracı Listesi ve Ödeme Durumları")
        cols_to_show = [c for c in filtered_df.columns if c and 'nan' not in str(c)]
        st.dataframe(filtered_df[cols_to_show].fillna(""), use_container_width=True)

        # --- DETAYLI KİRACI GÖRÜNÜMÜ ---
        st.markdown("---")
        st.subheader("🔎 Kiracı Detay Kartı")

        tenant_list = df["MÜLK / KİRACI"].dropna().unique()
        selected_tenant = st.selectbox("Detayını incelemek istediğiniz kiracıyı seçin:", tenant_list)

        if selected_tenant:
            tenant_info = df[df["MÜLK / KİRACI"] == selected_tenant].iloc[0]

            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.markdown(f"**📍 Konum (K:D):** {tenant_info.get('K:D:', 'Belirtilmemiş')}")
                st.markdown(f"**📞 Telefon:** {tenant_info.get('TELEFON', 'Belirtilmemiş')}")
                st.markdown(f"**📅 Kira Dönemi:** {tenant_info.get('KİRA GÜNÜ', 'Belirtilmemiş')}")
            with t_col2:
                st.markdown(f"**💰 Kira Bedeli:** {tenant_info.get('KİRA BEDELİ', 'Belirtilmemiş')}")
                st.markdown(f"**⚠️ Ödenmeyen / Notlar:** {tenant_info.get('ÖDENMEYEN', '-')}")

            # Ödeme Geçmişi Grafiği
            st.markdown("**📅 Aylık Ödeme Geçmişi (+: Ödendi, Boş: Bekliyor):**")
            months = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM",
                      "KASIM", "ARALIK"]

            payment_status = [1 if str(tenant_info.get(m, '')).strip() == '+' else 0 for m in months]
            chart_data = pd.DataFrame({"Ay": months, "Ödeme Durumu (1=Ödendi)": payment_status})
            st.bar_chart(chart_data, x="Ay", y="Ödeme Durumu (1=Ödendi)")
else:
    st.info(
        "💡 Lütfen yukarıdaki alandan Excel veya CSV dosyanızı sürükleyip bırakarak veya 'Browse files' butonuna tıklayarak yükleyin.")