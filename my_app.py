import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import datetime
import base64
import requests
import json

# --- 基本設定 (最新のGitHub情報に修正済み) ---
PW = "TOYOTABASEBALLCLUB"
GITHUB_USER = "sakanatama-hub" 
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

@st.cache_data(ttl=5)
def load_data_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}"
    try:
        df = pd.read_csv(url)
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        return df
    except:
        return pd.DataFrame(columns=["DateTime", "Player Name", "StrikeZoneX", "StrikeZoneY"])

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
    
    st.sidebar.title("分析メニュー")
    mode = st.sidebar.radio("機能切替", ["📊 選手別・日付別分析", "📥 新規データ登録"])

    if mode == "📊 選手別・日付別分析":
        st.header("📊 選手別・日付別分析")
        
        if db_df.empty or len(db_df) == 0:
            st.warning("現在、GitHubにデータがありません。先に登録を行ってください。")
        else:
            target_player = st.sidebar.selectbox("選手を選択", PLAYERS)
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            
            if pdf.empty:
                st.info(f"{target_player} 選手のデータはまだありません。")
            else:
                pdf['Date_Only'] = pdf['DateTime'].dt.date
                available_dates = sorted(pdf['Date_Only'].unique(), reverse=True)
                target_date = st.sidebar.selectbox("日付を選択", available_dates)
                
                vdf = pdf[pdf['Date_Only'] == target_date].copy()
                st.subheader(f"📍 {target_player} : {target_date} のデータ")
                
                metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
                target_metric = st.selectbox("分析指標を選択", metrics if metrics else ["データなし"])
                
                if not vdf.empty and target_metric != "データなし":
                    clean_df = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                    
                    def get_grid_pos(x, y):
                        if y > 110: r = 0
                        elif 88.2 < y <= 110: r = 1
                        elif 66.6 < y <= 88.2: r = 2
                        elif 45 <= y <= 66.6: r = 3
                        else: r = 4
                        if x < -28.8: c = 0
                        elif -28.8 <= x < -9.6: c = 1
                        elif -9.6 <= x <= 9.6: c = 2
                        elif 9.6 < x <= 28.8: c = 3
                        else: c = 4
                        return r, c

                    grid = np.zeros((5, 5)); counts = np.zeros((5, 5))
                    for _, row in clean_df.iterrows():
                        r, c = get_grid_pos(row['StrikeZoneX'], row['StrikeZoneY'])
                        grid[r, c] += row[target_metric]; counts[r, c] += 1
                    
                    display_grid = np.where(counts > 0, grid / counts, 0)

                    fig = go.Figure(data=go.Heatmap(
                        z=np.flipud(display_grid),
                        x=['極内','内','中','外','極外'], y=['極高','高','中','低','極低'],
                        colorscale='YlOrRd', text=np.flipud(np.round(display_grid, 1)),
                        texttemplate="%{text}", showscale=True
                    ))
                    
                    bg_img = get_encoded_bg(LOCAL_IMAGE_PATH)
                    if bg_img:
                        fig.add_layout_image(dict(source=bg_img, xref="x", yref="y", x=-0.5, y=4.5, sizex=5, sizey=5, sizing="stretch", opacity=0.4, layer="below"))
                    
                    fig.update_layout(width=600, height=600)
                    st.plotly_chart(fig)
                    st.dataframe(vdf.drop(columns=['Date_Only']))

    elif mode == "📥 新規データ登録":
        st.header("📥 新規データ登録 (GitHub保存)")
        target_player = st.selectbox("登録する選手を選択", PLAYERS)
        uploaded_file = st.file_uploader("CSVファイルをアップロード", type="csv")
        
        if st.button("GitHubへ保存（コミット）"):
            if uploaded_file:
                try:
                    new_df = pd.read_csv(uploaded_file)
                    new_df['Player Name'] = target_player
                    new_df['DateTime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    combined_df = pd.concat([db_df, new_df], ignore_index=True).replace({np.nan: ""})
                    
                    status = save_to_github(combined_df)
                    if status in [200, 201]:
                        st.success(f"{target_player} 選手のデータをGitHubに保存しました！")
                        st.balloons()
                        st.cache_data.clear()
                    else:
                        st.error(f"保存失敗。ステータスコード: {status}")
                        st.info(f"送信先: {GITHUB_USER}/{GITHUB_REPO}")
                except Exception as e:
                    st.error(f"エラー: {e}")
            else:
                st.warning("ファイルを選択してください。")
