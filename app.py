import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# ==========================================
# ★設定（スプレッドシートのURLだけ書き換えて！）
# ==========================================
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1-UbZzne8Cfd2m8-wwVpy8miV_Uo8fl5ZM-KN42jGJDY/edit?gid=0#gid=0'
# ==========================================

st.title('💰 りく＆パートナーの最強家計簿')

# --- 1. 接続設定（ここが進化！PCでもネットでも動くようにする） ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

try:
    # Aプラン：Streamlit Cloud（ネット上）の鍵を使う
    if "gcp_service_account" in st.secrets:
        key_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    # Bプラン：自分のPCの鍵ファイルを使う
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("secret.json", scope)
    
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).sheet1

except Exception as e:
    st.error(f"接続エラー！鍵の設定を確認してね: {e}")
    st.stop()

# --- 2. 入力エリア ---
st.subheader('📝 新しい出費を記録')
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

# --- 3. 履歴エリア ---
st.subheader('📊 最近の履歴')
try:
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df.sort_values(by="日付", ascending=False))
        total = df["金額"].sum()
        st.metric("今月の合計出費", f"{total:,} 円")
    else:
        st.info("データはまだありません。")
except:
    st.info("データ読み込み中...")