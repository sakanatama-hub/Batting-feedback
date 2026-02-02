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

# 選手・打席定義（記憶済みデータ）
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
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'])
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
    return put_res.status_code == 200 or put_res.status_code == 201

# --- メイン表示 ---
st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
if "ok" not in st.session_state: st.session_state["ok"] = False

if not st.session_state["ok"]:
    # ログイン画面 (省略)
    pass
else:
    db_df = load_data_from_github()
    tab1, tab2 = st.tabs(["📊 データ分析", "📝 データ登録"])

    # --- タブ1: 分析 (以前の完成したコードをここに維持) ---
    with tab1:
        st.title("🔵 選手別打撃分析")
        # (前述のヒートマップ & インパクトポイント描画ロジック)
        pass

    # --- タブ2: 登録 (Excel一括登録対応) ---
    with tab2:
        st.title("📝 データ登録")
        
        st.subheader("📁 ファイルから一括登録")
        uploaded_file = st.file_uploader("ExcelまたはCSVファイルを選択してください", type=['xlsx', 'csv'])
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.xlsx'):
                    input_df = pd.read_excel(uploaded_file)
                else:
                    input_df = pd.read_csv(uploaded_file)
                
                st.write("プレビュー:", input_df.head())
                
                if st.button("この内容でGitHubのデータを上書きする"):
                    if save_to_github(input_df):
                        st.success("一括更新が完了しました！")
                        st.rerun()
                    else:
                        st.error("保存に失敗しました。")
            except Exception as e:
                st.error(f"エラー: {e}")

        st.markdown("---")
        st.subheader("⌨️ 手入力で追加")
        with st.form("single_input"):
            # (以前の手入力フォーム)
            pass
