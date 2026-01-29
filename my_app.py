import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import datetime
import base64

# --- 基本設定 ---
PW = "TOYOTABASEBALLCLUB"
# URLの最後を /export?format=csv に変えるのがコツです
SPREADSHEET_ID = "1uXTl0qap2MWW2b1Y-dTUl5UZ7ierJvWv9znmLzCDnBk"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv"

PLAYERS = [
    "#1 熊田 任洋", "#2 逢澤 崚介", "#3 三塚 武蔵", "#4 北村 祥治", "#5 前田 健伸",
    "#6 佐藤 勇基", "#7 西村 友哉", "#8 和田 佳大", "#9 今泉 颯太", "#10 福井 章吾",
    "#22 高祖 健輔", "#23 箱山 遥人", "#24 坂巻 尚哉", "#26 西村 彰浩", "#27 小畑 尋規",
    "#28 宮崎 仁斗", "#29 徳本 健太朗", "#39 柳 元珍", "#99 尾瀬 雄大"
]

LOCAL_IMAGE_PATH = "捕手目線.png"

def get_encoded_bg(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return None

def check_auth():
    if "ok" not in st.session_state:
        st.session_state["ok"] = False
    if st.session_state["ok"]:
        return True
    st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("パスワードを入力", type="password")
    if st.button("ログイン"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
        else:
            st.error("パスワードが違います")
    return False

if check_auth():
    @st.cache_data(ttl=60) # 1分間はデータをキャッシュして速くする
    def load_data():
        # 直接CSV形式で読み込む（これが一番確実！）
        return pd.read_csv(CSV_URL)

    try:
        db_df = load_data()
    except Exception as e:
        st.error(f"スプレッドシートが読み込めません。共有設定を確認してください。")
        st.stop()

    # 以降、解析ロジック（前回のコードと同じ）
    # ... (省略) ...
    st.write("データ読み込み成功！")
    st.write(db_df.head()) # 試しに最初の数行を表示
