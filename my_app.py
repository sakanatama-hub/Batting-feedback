import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import datetime
import base64
import requests
import json

# --- 基本設定 ---
PW = "TOYOTABASEBALLCLUB"
GITHUB_USER = "sakanatama-hub" # あなたのGitHubユーザー名
GITHUB_REPO = "Batting-feedback" 
GITHUB_FILE_PATH = "data.csv"
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

# GitHubから最新のデータを読み込む
@st.cache_data(ttl=5) # 5秒間キャッシュ
def load_data_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}"
    try:
        df = pd.read_csv(url)
        # 日付型に変換
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        return df
    except:
        # ファイルがない場合は最小限の列を持つ空のDFを作成
        return pd.DataFrame(columns=["DateTime", "Player Name", "StrikeZoneX", "StrikeZoneY"])

# GitHubへデータを保存（上書きコミット）
def save_to_github(df):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
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
    
    st.sidebar.title("メニュー")
    mode = st.sidebar.radio("機能切替", ["📊 選手別・日付別分析", "📥 新規データ登録"])

    if mode == "📊 選手別・日付別分析":
        st.header("📊 選手別・日付別分析")
        
        if db_df.empty:
            st.warning("GitHubにデータがありません。先に「新規データ登録」を行ってください。")
        else:
            # 1. 選手で絞り込み
            target_player = st.sidebar.selectbox("選手を選択", PLAYERS)
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            
            if pdf.empty:
                st.info(f"{target_player} 選手のデータはまだありません。")
            else:
                # 2. 日付で絞り込み
                pdf['Date_Only'] = pdf['DateTime'].dt.date
                available_dates = sorted(pdf['Date_Only'].unique(), reverse=True)
                target_date = st.sidebar.selectbox("日付を選択", available_dates)
                
                vdf = pdf[pdf['Date_Only'] == target_date].copy()
                
                st.subheader(f"📍 {target_player} : {target_date} のデータ")
                
                # 分析項目の選択
                metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
                target_metric = st.selectbox("分析指標を選択", metrics if metrics else ["データなし"])
                
                if not vdf.empty and target_metric != "データなし":
                    # --- ヒートマップ描画 (5x5) ---
                    clean_df = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                    
                  elif mode == "📥 新規データ登録":
        st.header("📥 新規データ登録 (GitHub保存)")
        st.info("データはGitHubのリポジトリに直接保存されます。")
        
        target_player = st.selectbox("選手を選択", PLAYERS)
        uploaded_file = st.file_uploader("CSVファイルをアップロード", type="csv")
        
        if st.button("GitHubへ保存（コミット）"):
            if uploaded_file:
                try:
                    # 1. 診断情報の表示（404エラーの原因を探る）
                    st.write(f"📡 送信先確認: https://github.com/{GITHUB_USER}/{GITHUB_REPO}")
                    
                    new_df = pd.read_csv(uploaded_file)
                    new_df['Player Name'] = target_player
                    new_df['DateTime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 既存データと統合
                    combined_df = pd.concat([db_df, new_df], ignore_index=True)
                    
                    # GitHubに保存実行
                    status = save_to_github(combined_df)
                    
                    if status in [200, 201]:
                        st.success(f"{target_player} 選手のデータをGitHubに保存しました！")
                        st.balloons()
                        st.cache_data.clear()
                    elif status == 404:
                        st.error("❌ 保存失敗: ステータス 404")
                        st.warning(f"原因の可能性:\n1. ユーザー名 '{GITHUB_USER}' が違う\n2. リポジトリ名 '{GITHUB_REPO}' が違う\n3. トークンの権限に 'repo' が入っていない")
                        st.info("GitHubのURLが https://github.com/ren-baseball/batting-feedback で合っているか今一度確認してください。")
                    else:
                        st.error(f"GitHubへの保存に失敗しました。ステータスコード: {status}")
                except Exception as e:
                    st.error(f"プログラムエラー: {e}")
            else:
                st.warning("CSVファイルを選択してください。")
