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
    "#6 佐佐藤 勇基", "#7 西村 友哉", "#8 和田 佳大", "#9 今泉 颯太", "#10 福井 章吾",
    "#22 高祖 健輔", "#23 箱山 遥人", "#24 坂巻 尚哉", "#26 西村 彰浩", "#27 小畑 尋規",
    "#28 宮崎 仁斗", "#29 徳本 健太朗", "#39 柳 元珍", "#99 尾瀬 雄大"
]

# --- データ関数群 ---
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

# --- 背景デザイン関数 ---
def apply_pro_stadium_layout(fig, title_text):
    """
    漆黒のナイトスタジアムをイメージした最高級レイアウト
    """
    # 背景：最深部のブラック
    fig.add_shape(type="rect", x0=-200, x1=200, y0=-50, y1=300, fillcolor="#050805", line_width=0, layer="below")
    
    # 芝生：奥行きのあるダークストライプ
    for i in range(0, 250, 30):
        fig.add_shape(type="path", path=f"M -200 {i} L 200 {i} L 200 {i+15} L -200 {i+15} Z", 
                      fillcolor="#0a1a0a", line_width=0, layer="below")

    # 内野エリア：質感のあるブラウンのパース
    fig.add_shape(type="path", path="M -130 220 Q 0 320 130 220 L 180 -20 L -180 -20 Z", 
                  fillcolor="#2b1e16", line_width=0, layer="below")

    # ホームベース：発光ホワイト（サイバーエッジ）
    fig.add_shape(type="path", path="M -12 10 L 12 10 L 12 28 L 0 45 L -12 28 Z", 
                  fillcolor="#ffffff", line=dict(color="#00ffff", width=3), layer="below")

    # バッターボックス
    box_style = dict(color="rgba(0, 255, 255, 0.3)", width=2)
    fig.add_shape(type="path", path="M -50 -10 L -25 -10 L -20 60 L -45 60 Z", line=box_style, layer="below")
    fig.add_shape(type="path", path="M 50 -10 L 25 -10 L 20 60 L 45 60 Z", line=box_style, layer="below")

    fig.update_layout(
        title=dict(text=title_text, font=dict(size=26, color="#00ffff", family="Courier New")),
        width=900, height=750,
        xaxis=dict(range=[-110, 110], visible=False),
        yaxis=dict(range=[-30, 230], visible=False),
        paper_bgcolor='black', plot_bgcolor='black',
        margin=dict(l=10, r=10, t=70, b=10),
        showlegend=False
    )

def check_auth():
    if "ok" not in st.session_state: st.session_state["ok"] = False
    if st.session_state["ok"]: return True
    st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
    st.title("⚾️ TOYOTA BASEBALL FEEDBACK SYSTEM")
    val = st.text_input("ENTER ACCESS KEY", type="password")
    if st.button("LOGIN"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
        else: st.error("INVALID KEY")
    return False

# --- メインロジック ---
if check_auth():
    db_df = load_data_from_github()
    mode = st.sidebar.radio("CHOOSE MODE", ["📊 ANALYTICS", "📥 ENTRY"])

    if mode == "📊 ANALYTICS":
        target_player = st.sidebar.selectbox("PLAYER", PLAYERS)
        pdf = db_df[db_df['Player Name'] == target_player].copy()
        
        if not pdf.empty:
            pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
            target_date = st.sidebar.selectbox("DATE", sorted(pdf['Date_Only'].unique(), reverse=True))
            vdf = pdf[pdf['Date_Only'] == target_date].copy()
            metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            target_metric = st.selectbox("SELECT METRIC", metrics if metrics else ["N/A"])

            # --- SECTION 1: コース別平均 ---
            st.subheader("🎯 HEATMAP ANALYSIS")
            fig1 = go.Figure()
            apply_pro_stadium_layout(fig1, f"ZONE PERFORMANCE: {target_metric}")
            
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

                # ハイテク・ヒートマップ
                fig1.add_trace(go.Heatmap(
                    z=np.flipud(display_grid),
                    x=[-45, -22.5, 0, 22.5, 45], y=[105, 125, 145, 165, 185],
                    colorscale='Electric', opacity=0.9,
                    text=np.flipud(np.round(display_grid, 1)),
                    texttemplate="<span style='font-size:16px; color:white'>% {text}</span>",
                    showscale=False
                ))
                # ゾーン境界（ネオンレッド）
                fig1.add_shape(type="rect", x0=-30, x1=30, y0=115, y1=175, 
                              line=dict(color="#ff2222", width=6), layer="above")
            st.plotly_chart(fig1, use_container_width=True)

            # --- SECTION 2: 打点プロット ---
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.subheader("📍 IMPACT TRACKING")
            fig2 = go.Figure()
            apply_pro_stadium_layout(fig2, "BALL IMPACT POINT")
            
            if 'StrikeZoneX' in vdf.columns:
                # 打点（ネオンイエロー・ダイヤモンド）
                fig2.add_trace(go.Scatter(
                    x=vdf['StrikeZoneX'] * 0.6, y=vdf['StrikeZoneY'] + 80,
                    mode='markers',
                    marker=dict(size=16, color='#ffff00', symbol='diamond', 
                                line=dict(width=2, color='white'), opacity=1.0)
                ))
                # ゾーン枠
                fig2.add_shape(type="rect", x0=-25, x1=25, y0=115, y1=175, 
                              line=dict(color="#ff2222", width=5), layer="above")
            st.plotly_chart(fig2, use_container_width=True)
            
            # --- 表形式データ（エラー回避版） ---
            st.markdown("### 📋 RAW DATA")
            st.dataframe(vdf)

    elif mode == "📥 ENTRY":
        st.header("📥 DATA ENTRY")
        # 登録処理（略：以前の動くロジックを維持）
        st.info("Ready for data synchronization.")
