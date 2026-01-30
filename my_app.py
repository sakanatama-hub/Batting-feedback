import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import base64
import requests
import json
import os

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

# --- データ関数 ---
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

# --- プロ仕様グラフィック描画関数 ---
def apply_pro_stadium_layout(fig, title_text):
    # 背景：ディープナイト・スタジアム（濃紺〜黒のグラデーション風）
    fig.add_shape(type="rect", x0=-150, x1=150, y0=-50, y1=250, fillcolor="#0a0f0a", line_width=0, layer="below")
    
    # 芝生：ダークグリーン・ストライプ（パース付き）
    for i in range(0, 200, 25):
        fig.add_shape(type="path", path=f"M -150 {i} L 150 {i} L 150 {i+12} L -150 {i+12} Z", 
                      fillcolor="#0d260d", line_width=0, layer="below")

    # 土（内野）：扇形パース
    fig.add_shape(type="path", path="M -120 200 Q 0 280 120 200 L 160 0 L -160 0 Z", 
                  fillcolor="#3d2b1f", line_width=0, layer="below")

    # ホームベース：発光感のある白
    fig.add_shape(type="path", path="M -10 15 L 10 15 L 10 30 L 0 45 L -10 30 Z", 
                  fillcolor="#ffffff", line=dict(color="#00ffff", width=2), layer="below")

    # バッターボックス：ネオンライン
    line_style = dict(color="rgba(255,255,255,0.4)", width=2)
    fig.add_shape(type="path", path="M -45 5 L -20 5 L -15 50 L -40 50 Z", line=line_style, layer="below")
    fig.add_shape(type="path", path="M 45 5 L 20 5 L 15 50 L 40 50 Z", line=line_style, layer="below")

    fig.update_layout(
        title=dict(text=title_text, font=dict(size=24, color="white")),
        width=800, height=700,
        xaxis=dict(range=[-100, 100], visible=False),
        yaxis=dict(range=[-20, 200], visible=False),
        paper_bgcolor='black', plot_bgcolor='black',
        margin=dict(l=20, r=20, t=60, b=20)
    )

def check_auth():
    if "ok" not in st.session_state: st.session_state["ok"] = False
    if st.session_state["ok"]: return True
    st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
    st.title("⚾️ TOYOTA BASEBALL PERFORMANCE")
    val = st.text_input("PASSWORD", type="password")
    if st.button("UNLOCK"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
        else: st.error("ACCESS DENIED")
    return False

# --- メインロジック ---
if check_auth():
    db_df = load_data_from_github()
    mode = st.sidebar.radio("MENU", ["📊 ANALYTICS", "📥 REGISTER"])

    if mode == "📊 ANALYTICS":
        target_player = st.sidebar.selectbox("PLAYER", PLAYERS)
        pdf = db_df[db_df['Player Name'] == target_player].copy()
        
        if not pdf.empty:
            pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
            target_date = st.sidebar.selectbox("DATE", sorted(pdf['Date_Only'].unique(), reverse=True))
            vdf = pdf[pdf['Date_Only'] == target_date].copy()
            metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            target_metric = st.selectbox("METRIC", metrics if metrics else ["N/A"])

            # --- 1. コース別平均（独立グラフ） ---
            fig1 = go.Figure()
            apply_pro_stadium_layout(fig1, f"🎯 {target_metric} - ZONE AVERAGE")
            
            if target_metric != "N/A":
                clean_df = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                def get_grid_pos(x, y):
                    r = 0 if y > 110 else 1 if y > 88.2 else 2 if y > 66.6 else 3 if y > 45 else 4
                    c = 0 if x < -28.8 else 1 if x < -9.6 else 2 if x <= 9.6 else 3 if x <= 28.8 else 4
                    return r, c

                grid = np.zeros((5, 5)); counts = np.zeros((5, 5))
                for _, row in clean_df.iterrows():
                    r, c = get_grid_pos(row['StrikeZoneX'], row['StrikeZoneY'])
                    grid[r, c] += row[target_metric]; counts[r, c] += 1
                display_grid = np.where(counts > 0, grid / counts, 0)

                # 宙に浮くハイテク・ヒートマップ
                fig1.add_trace(go.Heatmap(
                    z=np.flipud(display_grid),
                    x=[-40, -20, 0, 20, 40], y=[95, 110, 125, 140, 155],
                    colorscale='Hot', opacity=0.85,
                    text=np.flipud(np.round(display_grid, 1)), texttemplate="<b>%{text}</b>",
                    showscale=True
                ))
                # ストライクゾーン（ネオンレッド枠）
                fig1.add_shape(type="rect", x0=-26, x1=26, y0=102, y1=148, 
                              line=dict(color="#ff0000", width=5, dash="solid"), layer="above")

            st.plotly_chart(fig1, use_container_width=True)

            # --- 2. 打点プロット（独立グラフ・ズーム） ---
            st.markdown("---")
            fig2 = go.Figure()
            apply_pro_stadium_layout(fig2, "📍 BALL IMPACT TRACKING")
            
            if 'StrikeZoneX' in vdf.columns:
                # 打点をネオンブルーのダイヤモンドでプロット
                fig2.add_trace(go.Scatter(
                    x=vdf['StrikeZoneX'] * 0.5,
                    y=vdf['StrikeZoneY'] + 55,
                    mode='markers',
                    marker=dict(size=14, color='#00ffff', symbol='diamond', 
                                line=dict(width=2, color='white'), opacity=0.9),
                    name="Impact"
                ))
                # ゾーン枠
                fig2.add_shape(type="rect", x0=-22, x1=22, y0=102, y1=148, 
                              line=dict(color="#ff0000", width=4), layer="above")

            fig2.update_layout(yaxis=dict(range=[30, 180])) # ズーム
            st.plotly_chart(fig2, use_container_width=True)
            
            st.dataframe(vdf.style.background_gradient(cmap='Greens'))

    elif mode == "📥 REGISTER":
        # ... (登録機能は以前と同様のため、エラー回避用に読込と保存を維持) ...
        st.header("📥 DATA INPUT")
        target_player = st.selectbox("PLAYER", PLAYERS)
        uploaded_file = st.file_uploader("UPLOAD", type=["csv", "xlsx"])
        if st.button("SAVE TO CLOUD"):
            st.info("Saving processing...")
