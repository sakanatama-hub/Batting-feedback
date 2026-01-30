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

def draw_catcher_view_field(fig, zoom=False):
    """
    捕手視点の明るいスタジアムをシミュレート
    """
    # 芝生（明るい緑）
    fig.add_shape(type="rect", x0=-150, x1=150, y0=-50, y1=250, fillcolor="#32CD32", line_width=0, layer="below")
    # 土のサークル（パース付き）
    fig.add_shape(type="circle", x0=-120, x1=120, y0=-80, y1=160, fillcolor="#DEB887", line_color="#A0522D", layer="below")
    
    # 捕手視点のホームベース（五角形の尖った方が上/投手側）
    # M [左上] [右上] [右下中央] [中央尖り] [左下中央] Z
    fig.add_shape(type="path", path="M -10 10 L 10 10 L 10 20 L 0 30 L -10 20 Z", 
                  fillcolor="white", line=dict(color="gray", width=1), layer="below")
    
    # バッターボックス（捕手から見て左右）
    box_line = dict(color="white", width=3)
    fig.add_shape(type="rect", x0=-40, x1=-15, y0=0, y1=45, line=box_line, layer="below")
    fig.add_shape(type="rect", x0=15, x1=40, y0=0, y1=45, line=box_line, layer="below")
    
    # キャッチャーボックス
    fig.add_shape(type="path", path="M -15 0 L 15 0 L 20 -20 L -20 -20 Z", line=box_line, layer="below")

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
        st.header("📊 選手分析")
        target_player = st.sidebar.selectbox("選手を選択", PLAYERS)
        pdf = db_df[db_df['Player Name'] == target_player].copy()
        
        if not pdf.empty:
            pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
            target_date = st.sidebar.selectbox("日付を選択", sorted(pdf['Date_Only'].unique(), reverse=True))
            vdf = pdf[pdf['Date_Only'] == target_date].copy()
            metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            target_metric = st.selectbox("分析指標", metrics if metrics else ["データなし"])

            # --- 1. コース別平均（グリッド数値復元版） ---
            st.subheader("🎯 コース別平均 (ヒートマップ)")
            if target_metric != "データなし":
                clean_df = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                
                # 正確なグリッド判定ロジックの復元
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
                
                fig1 = go.Figure()
                draw_catcher_view_field(fig1)
                
                # ヒートマップの色と位置を以前の成功パターンに固定
                fig1.add_trace(go.Heatmap(
                    z=np.flipud(display_grid),
                    x=['極内','内','中','外','極外'],
                    y=['極低','低','中','高','極高'],
                    x0=-38.4, dx=19.2, y0=40, dy=20, # 座標をホームベース上に合わせる
                    colorscale='YlOrRd', # 色を元に戻す
                    opacity=0.7,
                    text=np.flipud(np.round(display_grid, 1)),
                    texttemplate="%{text}",
                    showscale=True
                ))
                # ストライクゾーン強調枠 (赤・太線)
                fig1.add_shape(type="rect", x0=-28.8, x1=28.8, y0=45, y1=110, line=dict(color="Red", width=5))
                
                fig1.update_layout(width=750, height=700, xaxis=dict(range=[-100, 100], visible=False), yaxis=dict(range=[-30, 180], visible=False))
                st.plotly_chart(fig1)

            # --- 2. 打点プロット (完璧と言われたロジックの復元) ---
            st.markdown("---")
            st.subheader("📍 打点詳細プロット")
            if 'StrikeZoneX' in vdf.columns:
                fig2 = go.Figure()
                draw_catcher_view_field(fig2)
                
                fig2.add_trace(go.Scatter(
                    x=vdf['StrikeZoneX'], y=vdf['StrikeZoneY'],
                    mode='markers',
                    marker=dict(size=12, color='yellow', line=dict(width=1, color='black'))
                ))
                # 赤い正方形のストライクゾーン
                fig2.add_shape(type="rect", x0=-22, x1=22, y0=45, y1=110, line=dict(color="Red", width=4))
                
                fig2.update_layout(width=750, height=700, xaxis=dict(range=[-100, 100], visible=False), yaxis=dict(range=[-30, 180], visible=False))
                st.plotly_chart(fig2)

            st.dataframe(vdf)
