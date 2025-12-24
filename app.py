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
# タブ構成
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📝 入力", "📅 カレンダー", "📊 履歴・編集", "🛒 買い物リスト"])

# ------------------------------------------
# タブ1：入力画面（複数支払い対応！）
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
                # 二人で払った場合は、データを2行に分けて保存する（これが一番管理しやすい！）
                rows_to_add = []
                if amount_riku > 0:
                    rows_to_add.append([str(date), category, amount_riku, f"{memo}(りく分)", "りく", type_option, year, month])
                if amount_minami > 0:
                    rows_to_add.append([str(date), category, amount_minami, f"{memo}(みなみ分)", "みなみ", type_option, year, month])
                
                if rows_to_add:
                    sheet_log.append_rows(rows_to_add)
                    st.success(f"保存しました！ りく:{amount_riku}円、みなみ:{amount_minami}円")
            
            st.rerun()

# ------------------------------------------
# タブ2：カレンダー
# ------------------------------------------
with tab2:
    st.subheader('📅 収支カレンダー')
    if not df.empty:
        events = []
        # 日付ごとに合計
        daily_sum = df.groupby('日付')['金額'].sum().reset_index()
        for index, row in daily_sum.iterrows():
            events.append({
                "title": f"¥{row['金額']:,}", 
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
    else:
        st.info("データがありません")

# ------------------------------------------
# タブ3：履歴・編集（★ここが進化！）
# ------------------------------------------
with tab3:
    st.subheader('📊 データの履歴と編集')
    st.caption("👇 表の中をダブルクリックすると書き換えられます！")
    
    if not df.empty:
        # データ編集用エディタ
        edited_df = st.data_editor(
            df, 
            num_rows="dynamic", # 行の追加削除も可能に
            use_container_width=True,
            key="history_editor"
        )
        
        # 変更を保存するボタン
        if st.button("変更をスプレッドシートに保存する"):
            # データフレームをリストに変換してスプレッドシートを全更新（一番確実な方法）
            # ヘッダー + データ
            updated_data = [edited_df.columns.tolist()] + edited_df.astype(str).values.tolist()
            sheet_log.clear()
            sheet_log.update(updated_data)
            st.success("スプレッドシートを更新しました！")
            st.rerun()
            
        st.divider()
        
        # --- 簡易分析 ---
        current_m = datetime.now().month
        st.markdown(f"##### 📊 {current_m}月の内訳")
        df_m = df[df['月'] == current_m]
        if not df_m.empty:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig = px.pie(df_m, values='金額', names='カテゴリー', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            with col_g2:
                # 精算計算
                shared = df_m[df_m['種別'] == '共通（割り勘）']
                riku_pay = shared[shared['支払者'] == 'りく']['金額'].sum()
                minami_pay = shared[shared['支払者'] == 'みなみ']['金額'].sum()
                diff = riku_pay - minami_pay
                
                st.write(f"りく支払: **{riku_pay:,}** 円")
                st.write(f"みなみ支払: **{minami_pay:,}** 円")
                if diff > 0:
                    st.info(f"👉 **みなみ** → **りく** に **{diff//2:,}円** 渡す")
                elif diff < 0:
                    st.info(f"👉 **りく** → **みなみ** に **{abs(diff)//2:,}円** 渡す")
    else:
        st.info("データがありません")

# ------------------------------------------
# タブ4：買い物リスト（★編集・ソート・メモ対応！）
# ------------------------------------------
with tab4:
    st.subheader('🛒 買い物＆欲しいものリスト')
    st.caption("👇 表の「お店」や「品目」をクリックすると並び替えできます！")
    
    # 新規追加フォーム
    with st.expander("➕ 新しいアイテムを追加する"):
        with st.form("shop_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 2])
            item = c1.text_input("買うもの")
            shop = c2.text_input("お店・場所")
            price = c3.number_input("予想金額", step=100)
            memo_shop = c4.text_input("メモ")
            
            if st.form_submit_button("リストに追加"):
                sheet_shop.append_row([item, shop, price, "未購入", memo_shop])
                st.success("追加しました！")
                st.rerun()

    # 編集可能なリスト表示
    if not df_shop.empty:
        edited_shop_df = st.data_editor(
            df_shop,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "ステータス": st.column_config.SelectboxColumn(
                    "ステータス",
                    options=["未購入", "購入済"],
                    required=True,
                ),
                "予想金額": st.column_config.NumberColumn(
                    "予想金額",
                    format="¥%d",
                ),
            },
            key="shop_editor"
        )
        
        if st.button("買い物リストの変更を保存する"):
            # 更新処理
            updated_shop_data = [edited_shop_df.columns.tolist()] + edited_shop_df.astype(str).values.tolist()
            sheet_shop.clear()
            sheet_shop.update(updated_shop_data)
            st.success("買い物リストを更新しました！")
            st.rerun()
    else:
        st.info("買い物リストは空っぽです")
