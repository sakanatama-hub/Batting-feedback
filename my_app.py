import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import requests
import base64
import io

# --- 基本設定 ---
PW = "TOYOTABASEBALLCLUB"
GITHUB_USER = "sakanatama-hub" 
GITHUB_REPO = "Batting-feedback" 
GITHUB_FILE_PATH = "data.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# 選手定義
PLAYER_HANDS = {
    "#1 熊田 任洋": "左", "#2 逢澤 崚介": "左", "#3 三塚 武蔵": "左", 
    "#4 北村 祥治": "右", "#5 前田 健伸": "左", "#6 佐藤 勇基": "右", 
    "#7 西村 友哉": "右", "#8 和田 佳大": "左", "#9 今泉 颯太": "右", 
    "#10 福井 章吾": "左", "#22 高祖 健輔": "左", "#23 箱山 遥人": "右", 
    "#24 坂巻 尚哉": "右", "#26 西村 彰浩": "左", "#27 小畑 尋規": "右", 
    "#28 宮崎 仁斗": "右", "#29 徳本 健太朗": "左", "#39 柳 元珍": "左", 
    "#99 尾瀬 雄大": "左"
}
PLAYERS = list(PLAYER_HANDS.keys())

def load_data_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}?nocache={datetime.datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        return df
    except:
        return pd.DataFrame()

def save_to_github(new_df):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    csv_content = new_df.to_csv(index=False)
    b64_content = base64.b64encode(csv_content.encode()).decode()
    
    data = {"message": "Update batting data", "content": b64_content}
    if sha: data["sha"] = sha
    
    put_res = requests.put(url, headers=headers, json=data)
    return put_res.status_code in [200, 201]

# --- メイン表示 ---
st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
if "ok" not in st.session_state: st.session_state["ok"] = False

if not st.session_state["ok"]:
    # ログイン処理 (省略)
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("PASSWORD", type="password")
    if st.button("LOGIN"):
        if val == PW: st.session_state["ok"] = True; st.rerun()
else:
    db_df = load_data_from_github()
    tab1, tab2 = st.tabs(["📊 データ分析", "📝 データ登録"])

    # --- タブ1: 分析 (省略) ---
    with tab1:
        st.info("ここに以前の分析グラフが表示されます")

    # --- タブ2: 登録 (選手・日付選択機能付き) ---
    with tab2:
        st.title("📝 データ一括登録")
        
        with st.expander("📂 ファイルから登録 (Excel/CSV)", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                upload_player = st.selectbox("登録する選手", PLAYERS, key="upload_p")
            with col2:
                upload_date = st.date_input("練習日を選択", datetime.date.today())
            
            uploaded_file = st.file_uploader("ファイルを選択", type=['xlsx', 'csv'])
            
            if uploaded_file:
                try:
                    # ファイル読み込み
                    temp_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                    
                    # 選択された選手と日付をデータに付与
                    temp_df['Player Name'] = upload_player
                    # DateTime列を作成（日付に00:00:00を付与）
                    temp_df['DateTime'] = upload_date.strftime("%Y-%m-%d") + " 00:00:00"
                    
                    st.write("### 登録内容のプレビュー")
                    st.dataframe(temp_df.head())
                    
                    if st.button("この内容で追加保存する"):
                        # 既存データと結合（上書きではなく追記）
                        new_db_df = pd.concat([db_df, temp_df], ignore_index=True)
                        if save_to_github(new_db_df):
                            st.success(f"{upload_player} 選手の {upload_date} 分のデータを追加しました！")
                            st.rerun()
                        else:
                            st.error("保存に失敗しました。")
                except Exception as e:
                    st.error(f"ファイル形式が正しくありません: {e}")

        st.markdown("---")
        with st.expander("⌨️ 1スイングずつ手入力"):
            # 以前の手入力フォームもここに配置可能
            st.write("（必要に応じて手入力フォームを表示）")
