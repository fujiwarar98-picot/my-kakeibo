import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import plotly.express as px

# ==========================================
# ★設定（スプレッドシートのURL）
# ==========================================
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1-UbZzne8Cfd2m8-wwVpy8miV_Uo8fl5ZM-KN42jGJDY/edit?gid=335284044#gid=335284044'
# ==========================================

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
    sheet_log = spreadsheet.sheet1
    sheet_shop = spreadsheet.worksheet("shopping")
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- データ読み込み関数 ---
def load_data():
    records = sheet_log.get_all_records()
    df = pd.DataFrame(records) if records else pd.DataFrame()
    
    shop_records = sheet_shop.get_all_records()
    df_shop = pd.DataFrame(shop_records) if shop_records else pd.DataFrame()
    return df, df_shop

df, df_shop = load_data()

st.title('🏠 りく＆みなみの最強家計簿')

# ==========================================
# タブ構成（3つに減らしました！）
# ==========================================
tab1, tab2, tab3 = st.tabs(["📝 入力", "📊 履歴・編集・分析", "🛒 買い物リスト"])

# ------------------------------------------
# タブ1：入力画面
# ------------------------------------------
with tab1:
    st.subheader('📝 レシート入力')
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("日付", datetime.now())
            category = st.selectbox("カテゴリー", 
                ["食費", "外食", "日用品", "家賃・光熱費", "交通費", "娯楽", "地方競馬", "特別費", "その他"])
            total_amount = st.number_input("合計金額（円）", min_value=0, step=100)
        
        with col2:
            # 支払い方法の選択
            pay_mode = st.radio("支払い方法は？", ["一人が払った", "二人で払った（金額指定）"], horizontal=True)
            
            payer = "りく" # デフォルト
            amount_riku = 0
            amount_minami = 0
            
            if pay_mode == "一人が払った":
                payer = st.radio("誰が財布を出した？", ["りく", "みなみ"], horizontal=True)
            else:
                st.info("👇 それぞれいくら出した？")
                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    amount_riku = st.number_input("りくの支払額", min_value=0, max_value=total_amount, step=100)
                with c_p2:
                    amount_minami = total_amount - amount_riku
                    st.write(f"みなみの支払額: **{amount_minami}円**")

            type_option = st.radio("支出の種類は？", ["共通（割り勘）", "りく個人", "みなみ個人"], horizontal=True)
            memo = st.text_input("メモ")
        
        submitted = st.form_submit_button("家計簿に保存する")
        
        if submitted:
            year = date.year
            month = date.month
            
            # 保存処理
            if pay_mode == "一人が払った":
                # 1行だけ保存
                new_row = [str(date), category, total_amount, memo, payer, type_option, year, month]
                sheet_log.append_row(new_row)
                st.success(f"保存しました！ {category}: {total_amount}円")
            else:
                # 二人で払った場合は、データを2行に分けて保存する
                rows_to_add = []
                if amount_riku > 0:
                    rows_to_add.append([str(date), category, amount_riku, f"{memo}(りく分)", "りく", type_option, year, month])
                if amount_minami > 0:
                    rows_to_add.append([str(date), category, amount_minami, f"{memo}(みなみ分)", "みなみ", type_option, year, month])
                
                if rows_to_add:
                    sheet_log.append_rows(rows_to_add)
                    st.success(f"保存しました！ りく:{amount_riku}円、みなみ:{amount_minami}円")
            
            st.
