import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar
import plotly.express as px

# ==========================================
# ★設定（スプレッドシートのURL）
# ==========================================
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1-UbZzne8Cfd2m8-wwVpy8miV_Uo8fl5ZM-KN42jGJDY/edit?gid=0#gid=0'
# ==========================================

# ページ設定（タイトルやアイコン）
st.set_page_config(page_title="りく＆みなみの家計簿", page_icon="🏠", layout="wide")

# --- 1. スプレッドシート接続 ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
try:
    if "gcp_service_account" in st.secrets:
        key_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("secret.json", scope)
    
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(SHEET_URL)
    sheet_log = spreadsheet.sheet1          # 1枚目：家計簿ログ
    sheet_shop = spreadsheet.worksheet("shopping") # 2枚目：買い物メモ
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- データの読み込み ---
def load_data():
    # 家計簿データ
    records = sheet_log.get_all_records()
    df = pd.DataFrame(records) if records else pd.DataFrame()
    # 買い物データ
    shop_records = sheet_shop.get_all_records()
    df_shop = pd.DataFrame(shop_records) if shop_records else pd.DataFrame()
    return df, df_shop

df, df_shop = load_data()

st.title('🏠 りく＆みなみの最強家計簿')

# --- 予算アラート機能 ---
if not df.empty:
    current_month = datetime.now().month
    this_month_data = df[df['月'] == current_month]
    total_spend = this_month_data['金額'].sum()
    budget_limit = 200000 # ★予算（20万円）
    
    if total_spend > budget_limit:
        st.error(f"⚠️ 今月の出費が {total_spend:,}円 です！予算オーバーです！")
    elif total_spend > budget_limit * 0.8:
        st.warning(f"⚠️ そろそろ予算ピンチです（現在: {total_spend:,}円）")

# ==========================================
# タブ構成
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📝 入力", "📅 カレンダー", "📊 分析・精算", "🛒 買い物メモ"])

# ------------------------------------------
# タブ1：入力画面（割り勘対応）
# ------------------------------------------
with tab1:
    st.subheader('📝 レシート入力')
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("日付", datetime.now())
            category = st.selectbox("カテゴリー", 
                ["食費", "外食", "日用品", "家賃・光熱費", "交通費", "娯楽", "地方競馬", "特別費", "その他"])
            amount = st.number_input("金額（円）", min_value=0, step=100)
        
        with col2:
            payer = st.radio("誰が払った？（財布を出した人）", ["りく", "みなみ"], horizontal=True)
            type_option = st.radio("支出の種類は？", ["共通（割り勘）", "りく個人", "みなみ個人"], horizontal=True)
            memo = st.text_input("メモ（店名など）")
        
        submitted = st.form_submit_button("家計簿に保存する")
        
        if submitted:
            # 年と月を自動計算
            year = date.year
            month = date.month
            
            new_row = [str(date), category, amount, memo, payer, type_option, year, month]
            sheet_log.append_row(new_row)
            st.success(f"保存しました！ {category}: {amount}円 ({type_option})")
            st.rerun()

# ------------------------------------------
# タブ2：カレンダー（シンプル表示）
# ------------------------------------------
with tab2:
    st.subheader('📅 収支カレンダー')
    if not df.empty:
        # 月ごとの集計エリア
        col_c1, col_c2, col_c3 = st.columns(3)
        current_m = datetime.now().month
        m_data = df[df['月'] == current_m]
        
        with col_c1:
            st.metric(f"{current_m}月の支出合計", f"{m_data['金額'].sum():,} 円")
        with col_c2:
            st.metric("共通の支出", f"{m_data[m_data['種別']=='共通（割り勘）']['金額'].sum():,} 円")
        
        # カレンダーデータ作成
        events = []
        # 日付ごとに合計する
        daily_sum = df.groupby('日付')['金額'].sum().reset_index()
        
        for index, row in daily_sum.iterrows():
            events.append({
                "title": f"¥{row['金額']:,}", # 金額だけシンプルに
                "start": str(row['日付']),
                "backgroundColor": "#FF6C6C" if row['金額'] > 10000 else "#3788d8",
            })

        calendar_options = {
            "headerToolbar": {
                "left": "prev,next",
                "center": "title",
                "right": "dayGridMonth,listMonth"
            },
        }
        calendar(events=events, options=calendar_options)
        
        # 下にリスト表示
        with st.expander("詳細リストを見る"):
            st.dataframe(df.sort_values(by="日付", ascending=False))
    else:
        st.info("データがありません")

# ------------------------------------------
# タブ3：分析・精算（★カップル機能！）
# ------------------------------------------
with tab3:
    st.subheader('📊 分析＆精算')
    
    if not df.empty:
        # 月選択
        month_list = df['月'].unique()
        selected_month = st.selectbox("月を選択", sorted(month_list, reverse=True))
        
        # 選択した月のデータ
        df_m = df[df['月'] == selected_month]
        
        # --- 円グラフ ---
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("##### カテゴリー内訳")
            fig = px.pie(df_m, values='金額', names='カテゴリー', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
        # --- 精算機能（超重要） ---
        with col_g2:
            st.markdown("##### 💰 今月の精算（割り勘）")
            # 共通の出費だけを取り出す
            shared_data = df_m[df_m['種別'] == '共通（割り勘）']
            
            # りくが払った共通費
            riku_paid = shared_data[shared_data['支払者'] == 'りく']['金額'].sum()
            # みなみが払った共通費
            minami_paid = shared_data[shared_data['支払者'] == 'みなみ']['金額'].sum()
            
            st.write(f"りくの立替: **{riku_paid:,}円**")
            st.write(f"みなみの立替: **{minami_paid:,}円**")
            st.write(f"合計: {riku_paid + minami_paid:,}円")
            
            st.divider()
            
            # 精算ロジック
            diff = riku_paid - minami_paid
            if diff > 0:
                pay_amount = diff // 2
                st.success(f"👉 **みなみ** は **りく** に **{pay_amount:,}円** 渡してください")
            elif diff < 0:
                pay_amount = abs(diff) // 2
                st.success(f"👉 **りく** は **みなみ** に **{pay_amount:,}円** 渡してください")
            else:
                st.balloons()
                st.info("精算なし！ぴったりです！")

# ------------------------------------------
# タブ4：買い物メモ（新機能！）
# ------------------------------------------
with tab4:
    st.subheader('🛒 買い物＆欲しいものリスト')
    
    # 入力フォーム
    with st.form("shop_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        item = c1.text_input("買うもの")
        shop = c2.text_input("お店・場所")
        price = c3.number_input("予想金額", step=100)
        if st.form_submit_button("リストに追加"):
            sheet_shop.append_row([item, shop, price, "未購入"])
            st.success("追加しました！")
            st.rerun()
    
    # リスト表示
    if not df_shop.empty:
        # 未購入と購入済みを分ける
        st.write("▼ まだ買ってないもの")
        for i, row in df_shop.iterrows():
            if row['ステータス'] != "購入済":
                col_s1, col_s2, col_s3 = st.columns([3, 2, 1])
                col_s1.write(f"**{row['品目']}** ({row['店・場所']})")
                col_s2.write(f"¥{row['予想金額']}")
                if col_s3.button("買った！", key=f"buy_{i}"):
                    # ステータスを更新（スプレッドシートの行を特定して書き換え）
                    # 行番号は i + 2 (ヘッダー分)
                    sheet_shop.update_cell(i + 2, 4, "購入済")
                    st.rerun()
        
        with st.expander("🗑️ 購入済みリスト（履歴）"):
            done_items = df_shop[df_shop['ステータス'] == "購入済"]
            st.dataframe(done_items)
    else:
        st.info("買い物リストは空っぽです")
