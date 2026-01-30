import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import base64
import requests
import json

# --- 基本設定 ---
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

def load_data_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}?nocache={datetime.datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        return df
    except:
        return pd.DataFrame()

def save_to_github(df):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    csv_content = df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_content.encode()).decode()
    data = {"message": f"Update: {datetime.datetime.now()}", "content": encoded_content}
    if sha: data["sha"] = sha
    res = requests.put(url, headers=headers, data=json.dumps(data))
    return res.status_code

def add_field_graphics(fig, zoom=False):
    """
    イラストのような野球の背景グラフィック（マウンド、ホームベース、ライン）を
    Plotlyの図形として追加する関数
    """
    # 背景の芝生（緑）
    fig.add_shape(type="rect", x0=-100, x1=100, y0=0, y1=200, fillcolor="seagreen", layer="below", line_width=0)
    
    # 土の部分（扇形）
    fig.add_shape(type="path", path="M -80 180 Q 0 250 80 180 L 0 0 Z", fillcolor="peru", layer="below", line_width=0)

    # ホームベース（白）
    fig.add_shape(type="path", path="M -8.5 5 L 8.5 5 L 8.5 12 L 0 20 L -8.5 12 Z", fillcolor="white", layer="below", line_width=1)
    
    # バッターボックスのライン
    fig.add_shape(type="rect", x0=-25, x1=-12, y0=2, y1=18, line=dict(color="white", width=2), layer="below")
    fig.add_shape(type="rect", x0=12, x1=25, y0=2, y1=18, line=dict(color="white", width=2), layer="below")

    if not zoom:
        # マウンド
        fig.add_shape(type="circle", x0=-15, x1=15, y0=145, y1=175, fillcolor="peru", line_color="white", layer="below")

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
    mode = st.sidebar.radio("機能切替", ["📊 選手分析", "📥 新規登録"])

    if mode == "📊 選手分析":
        st.header("📊 選手分析ダッシュボード")
        if db_df.empty:
            st.warning("データがありません。")
        else:
            target_player = st.sidebar.selectbox("選手を選択", PLAYERS)
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            if not pdf.empty:
                pdf['Date_Only'] = pdf['DateTime'].dt.date
                target_date = st.sidebar.selectbox("日付を選択", sorted(pdf['Date_Only'].unique(), reverse=True))
                vdf = pdf[pdf['Date_Only'] == target_date].copy()
                
                metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
                target_metric = st.selectbox("分析指標を選択", metrics if metrics else ["データなし"])

                # --- 1. コース別平均 (前面ヒートマップ) ---
                st.subheader("🎯 コース別平均 (Zone Analysis)")
                if target_metric != "データなし":
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
                    
                    fig_h = go.Figure()
                    # フィールドの描画
                    add_field_graphics(fig_h)
                    # ヒートマップ
                    fig_h.add_trace(go.Heatmap(
                        z=np.flipud(display_grid),
                        x=[-38, -19, 0, 19, 38], y=[35, 55, 75, 95, 115],
                        colorscale='YlOrRd', opacity=0.8,
                        text=np.flipud(np.round(display_grid, 1)), texttemplate="%{text}", showscale=True
                    ))
                    # ストライクゾーン強調
                    fig_h.add_shape(type="rect", x0=-28.8, x1=28.8, y0=45, y1=110, line=dict(color="red", width=4))
                    
                    fig_h.update_layout(width=700, height=600, xaxis=dict(range=[-100, 100], visible=False), yaxis=dict(range=[0, 180], visible=False))
                    st.plotly_chart(fig_h)

                # --- 2. 打点プロット (ズームアップ) ---
                st.subheader("📍 打球詳細プロット (Point View)")
                if 'StrikeZoneX' in vdf.columns:
                    fig_s = go.Figure()
                    add_field_graphics(fig_s, zoom=True)
                    fig_s.add_trace(go.Scatter(
                        x=vdf['StrikeZoneX'], y=vdf['StrikeZoneY'],
                        mode='markers', marker=dict(size=14, color='yellow', line=dict(width=1, color='black'), symbol='circle')
                    ))
                    # 赤枠
                    fig_s.add_shape(type="rect", x0=-22, x1=22, y0=45, y1=110, line=dict(color="red", width=5))
                    
                    fig_s.update_layout(width=700, height=600, xaxis=dict(range=[-60, 60], visible=False), yaxis=dict(range=[0, 140], visible=False))
                    st.plotly_chart(fig_s)
                
                st.dataframe(vdf)

    elif mode == "📥 新規登録":
        st.header("📥 データ登録")
        target_player = st.selectbox("選手を選択", PLAYERS)
        target_date = st.date_input("日付", datetime.date.today())
        uploaded_file = st.file_uploader("ファイルをアップロード", type=["csv", "xlsx"])
        
        if st.button("GitHubへ保存"):
            if uploaded_file:
                try:
                    df_up = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                    df_up['Player Name'] = target_player
                    df_up['DateTime'] = datetime.datetime.combine(target_date, datetime.datetime.now().time())
                    new_db = pd.concat([db_df, df_up], ignore_index=True).replace({np.nan: ""})
                    save_to_github(new_db)
                    st.success("GitHubに保存しました。")
                    st.cache_data.clear()
                except Exception as e: st.error(f"エラー: {e}")
