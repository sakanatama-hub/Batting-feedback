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

# --- GitHubデータ関数 ---
def load_data_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}?nocache={datetime.datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        return df
    except:
        return pd.DataFrame()

# --- グラフィック描画（捕手視点・イラスト再現） ---
def draw_stadium_background(fig):
    # 明るい芝生
    fig.add_shape(type="rect", x0=-100, x1=100, y0=0, y1=160, fillcolor="#7db343", line_width=0, layer="below")
    # 土のサークル
    fig.add_shape(type="circle", x0=-80, x1=80, y0=-40, y1=100, fillcolor="#c89666", line_width=0, layer="below")
    # 捕手視点のホームベース（上が尖る）
    fig.add_shape(type="path", path="M -12 15 L 12 15 L 12 32 L 0 48 L -12 32 Z", fillcolor="white", line=dict(color="#888", width=2), layer="below")
    # バッターボックス
    box_s = dict(color="white", width=4)
    fig.add_shape(type="rect", x0=-42, x1=-18, y0=5, y1=60, line=box_s, layer="below")
    fig.add_shape(type="rect", x0=18, x1=42, y0=5, y1=60, line=box_s, layer="below")

# --- 認証 ---
def check_auth():
    if "ok" not in st.session_state: st.session_state["ok"] = False
    if st.session_state["ok"]: return True
    st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
    st.sidebar.title("🛠 設定")
    val = st.sidebar.text_input("パスワード", type="password")
    if st.sidebar.button("ログイン"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
    return False

if check_auth():
    db_df = load_data_from_github()
    
    # メインタイトル
    st.title("🔵 選手別・コース別分析")
    
    # 選手と指標の選択
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        target_player = st.selectbox("選手を選択してください", PLAYERS)
    
    pdf = db_df[db_df['Player Name'] == target_player].copy()
    
    if not pdf.empty:
        pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
        with col_sel2:
            target_date = st.selectbox("日付を選択", sorted(pdf['Date_Only'].unique(), reverse=True))
        
        vdf = pdf[pdf['Date_Only'] == target_date].copy()
        metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
        target_metric = st.selectbox("分析指標を選択", metrics if metrics else ["データなし"])

        st.markdown(f"### 🎵 コース別平均（{target_metric}）")

        # --- 図の作成 ---
        fig = go.Figure()
        draw_stadium_background(fig)

        if target_metric != "データなし":
            clean_df = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
            
            # グリッド計算
            def get_grid_pos(x, y):
                r = 0 if y > 110 else 1 if y > 88.2 else 2 if y > 66.6 else 3 if y > 45 else 4
                c = 0 if x < -28.8 else 1 if x < -9.6 else 2 if x <= 9.6 else 3 if x <= 28.8 else 4
                return r, c

            grid = np.zeros((5, 5)); counts = np.zeros((5, 5))
            for _, row in clean_df.iterrows():
                r, c = get_grid_pos(row['StrikeZoneX'], row['StrikeZoneY'])
                grid[r, c] += row[target_metric]; counts[r, c] += 1
            display_grid = np.where(counts > 0, grid / counts, 0)

            # ヒートマップ（イラストの左上のような配置）
            fig.add_trace(go.Heatmap(
                z=np.flipud(display_grid),
                x=[-38.4, -19.2, 0, 19.2, 38.4],
                y=[58, 70, 82, 94, 106],
                colorscale='YlOrRd',
                opacity=0.8,
                text=np.flipud(np.round(display_grid, 1)),
                texttemplate="<span style='font-size:22px; font-weight:bold;'>%{text}</span>",
                showscale=True
            ))

            # ストライクゾーン（太い赤枠）
            fig.add_shape(type="rect", x0=-28.8, x1=28.8, y0=48, y1=116, line=dict(color="Red", width=6))

        # レイアウト調整：ズームアップ
        fig.update_layout(
            width=850, height=750,
            xaxis=dict(range=[-70, 70], visible=False),
            yaxis=dict(range=[0, 140], visible=False),
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(vdf)
    else:
        st.warning("選択した選手のデータが見つかりません。")
