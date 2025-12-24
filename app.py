import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar
import plotly.express as px  # 👈 これが抜けていました！

# ==========================================
# ★設定（スプレッドシートのURLだけ書き換えて！）
# ==========================================
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1-UbZzne8Cfd2m8-wwVpy8miV_Uo8fl5ZM-KN42jGJDY/edit?gid=0#gid=0'
# ==========================================

st.set_page_config(page_title="最強家計簿", layout="wide")
st.title('💰 りく＆パートナーの最強家計簿')

# --- 1. 接続設定 ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
try:
    if "gcp_service_account" in st.secrets:
        key_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    else:
        # PCで動かす時用
        creds = ServiceAccountCredentials.from_json_keyfile_name("secret.json", scope)
    
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).sheet1
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- データの読み込み ---
records = sheet.get_all_records()
df = pd.DataFrame(records) if records else pd.DataFrame()

# ==========================================
# 画面を「タブ」で分ける
# ==========================================
tab1, tab2, tab3 = st.tabs(["📝 入力", "📅 カレンダー", "📊 分析"])

# ------------------------------------------
# タブ1：入力画面
# ------------------------------------------
with tab1:
    st.subheader('新しい出費を記録')
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("日付", datetime.now())
            category = st.selectbox("カテゴリー", 
                ["食費", "日用品", "外食", "交通費", "地方競馬", "中央競馬(G1)", "カード(オリパ)", "投資", "その他"])
        with col2:
            amount = st.number_input("金額（円）", min_value=0, step=100)
            buyer = st.radio("誰が払った？", ["りく", "彼女"])
        
        memo = st.text_input("メモ")
        submitted = st.form_submit_button("保存する！")
        
        if submitted:
            new_row = [str(date), category, amount, memo, buyer]
            sheet.append_row(new_row)
            st.success(f"保存完了！: {category} {amount}円")
            st.rerun()

# ------------------------------------------
# タブ2：カレンダー画面
# ------------------------------------------
with tab2:
    st.subheader('📅 支出カレンダー')
    if not df.empty:
        events = []
        for index, row in df.iterrows():
            title = f"{row['カテゴリー']} ¥{row['金額']}"
            if row['メモ']:
                title += f" ({row['メモ']})"
            
            color = "#FF6C6C" if "競馬" in row['カテゴリー'] else "#3788d8"

            events.append({
                "title": title,
                "start": str(row['日付']),
                "backgroundColor": color,
                "borderColor": color,
            })

        calendar_options = {
            "headerToolbar": {
                "left": "today prev,next",
                "center": "title",
                "right": "dayGridMonth,listMonth"
            },
        }
        calendar(events=events, options=calendar_options)
    else:
        st.info("データがまだありません")

# ------------------------------------------
# タブ3：分析画面（円グラフ）
# ------------------------------------------
with tab3:
    st.subheader('📊 収支レポート')
    if not df.empty:
        # 合計金額
        total = df["金額"].sum()
        st.metric("今月の合計出費", f"{total:,} 円")
        
        # 円グラフ作成
        category_sum = df.groupby("カテゴリー")["金額"].sum().reset_index()
        fig = px.pie(category_sum, values='金額', names='カテゴリー', 
                     title='何にお金使ってる？', hole=0.5)
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("詳細な履歴を見る"):
            st.dataframe(df.sort_values(by="日付", ascending=False))
    else:
        st.info("データがまだありません")
