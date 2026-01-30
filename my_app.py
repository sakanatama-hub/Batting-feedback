import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import datetime
import base64
import requests
import json

# --- 基本設定 (ここを書き換えてください) ---
PW = "TOYOTABASEBALLCLUB"
GITHUB_USER = "あなたのユーザー名"
GITHUB_REPO = "batting-feedback"
GITHUB_FILE_PATH = "data.csv" # 保存するファイル名
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

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

# GitHubからデータを読み込む関数
def load_data_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}"
    try:
        df = pd.read_csv(url)
        return df
    except:
        # ファイルがない場合は空のDataFrameを返す（1行目の項目を設定）
        return pd.DataFrame(columns=["DateTime", "Player Name", "StrikeZoneX", "StrikeZoneY", "ExitVelocity", "LaunchAngle"])

# GitHubにデータを保存（コミット）する関数
def save_to_github(df):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    # 現在のファイルのSHA（バージョンID）を取得
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    # CSVを文字列に変換
    csv_content = df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_content.encode()).decode()
    
    data = {
        "message": f"Update data: {datetime.datetime.now()}",
        "content": encoded_content,
    }
    if sha:
        data["sha"] = sha
        
    res = requests.put(url, headers=headers, data=json.dumps(data))
    return res.status_code

def check_auth():
    if "ok" not in st.session_state: st.session_state["ok"] = False
    if st.session_state["ok"]: return True
    st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("パスワードを入力", type="password")
    if st.button("ログイン"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
        else: st.error("パスワードが違います")
    return False

if check_auth():
    db_df = load_data_from_github()
    mode = st.sidebar.radio("メニュー", ["📊 データ分析", "📥 新規登録"])

    if mode == "📊 データ分析":
        st.header("📊 打撃データ分析")
        if db_df.empty:
            st.warning("GitHubにデータが見つかりません。")
        else:
            # --- (以前の分析ロジックはそのまま使用可能) ---
            target_player = st.sidebar.selectbox("選手を選択", PLAYERS)
            st.write(f"{target_player} 選手の最新データを表示しています")
            st.dataframe(db_df[db_df["Player Name"] == target_player])

    elif mode == "📥 新規登録":
        st.header("📥 GitHubへ保存")
        target_player = st.selectbox("登録する選手", PLAYERS)
        uploaded_file = st.file_uploader("CSVファイルをアップロード", type="csv")
        
        if st.button("GitHubへ保存（コミット）"):
            if uploaded_file:
                new_df = pd.read_csv(uploaded_file)
                new_df['Player Name'] = target_player
                new_df['DateTime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                combined_df = pd.concat([db_df, new_df], ignore_index=True)
                
                status = save_to_github(combined_df)
                if status in [200, 201]:
                    st.success("GitHubへの保存に成功しました！数秒で分析に反映されます。")
                    st.balloons()
                else:
                    st.error(f"保存失敗（ステータスコード: {status}）")
