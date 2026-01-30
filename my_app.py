import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime

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

# --- 認証 ---
st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
if "ok" not in st.session_state: st.session_state["ok"] = False

if not st.session_state["ok"]:
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("PASSWORD", type="password")
    if st.button("LOGIN"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
else:
    db_df = load_data_from_github()
    st.title("🔵 選手別・コース別分析")

    _, center_col, _ = st.columns([0.05, 9.9, 0.05])

    with center_col:
        c1, c2, c3 = st.columns([2, 2, 3])
        with c1: target_player = st.selectbox("選手を選択", PLAYERS)
        
        pdf = db_df[db_df['Player Name'] == target_player].copy()
        if not pdf.empty:
            pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
            with c2: target_date = st.selectbox("日付を選択", sorted(pdf['Date_Only'].unique(), reverse=True))
            vdf = pdf[pdf['Date_Only'] == target_date].copy()
            
            metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            with c3: target_metric = st.selectbox("分析指標", metrics if metrics else ["データなし"])

            fig = go.Figure()

            # --- 背景とフィールド（グリッドに合わせてスケール調整） ---
            fig.add_shape(type="rect", x0=-300, x1=300, y0=-100, y1=450, fillcolor="#1a4314", line_width=0, layer="below")
            fig.add_shape(type="path", path="M -80 100 L -300 400 L 300 400 L 80 100 Z", fillcolor="#8B4513", line_width=0, layer="below")
            fig.add_shape(type="circle", x0=-50, x1=50, y0=-20, y1=80, fillcolor="#8B4513", line_width=0, layer="below")
            fig.add_shape(type="path", path="M -15 50 L 15 50 L 15 35 L 0 10 L -15 35 Z", fillcolor="white", line=dict(color="#444", width=2), layer="below")
            
            box_style = dict(fillcolor="#1a4314", line=dict(color="rgba(255,255,255,0.8)", width=3), layer="below")
            fig.add_shape(type="path", path="M -85 15 L -40 15 L -35 100 L -80 100 Z", **box_style)
            fig.add_shape(type="path", path="M 85 15 L 40 15 L 35 100 L 80 100 Z", **box_style)
            fig.add_shape(type="line", x0=-80, y0=100, x1=-280, y1=380, line=dict(color="white", width=4), layer="below")
            fig.add_shape(type="line", x0=80, y0=100, x1=280, y1=380, line=dict(color="white", width=4), layer="below")

            # --- 【特大】正方形グリッドシステム ---
            side = 35  # 1マスのサイズを大幅にアップ
            z_x_start = -(side * 2.5)
            z_y_start = 140 # 少し上に配置
            
            if target_metric != "データなし":
                def get_grid_pos(x, y):
                    # オリジナルのデータ範囲に基づいた判定
                    r = 0 if y > 110 else 1 if y > 88.2 else 2 if y > 66.6 else 3 if y > 45 else 4
                    c = 0 if x < -28.8 else 1 if x < -9.6 else 2 if x <= 9.6 else 3 if x <= 28.8 else 4
                    return r, c

                grid_val = np.zeros((5, 5)); grid_count = np.zeros((5, 5))
                for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                    r, c = get_grid_pos(row['StrikeZoneX'], row['StrikeZoneY'])
                    grid_val[r, c] += row[target_metric]; grid_count[r, c] += 1
                display_grid = np.where(grid_count > 0, grid_val / grid_count, 0)

                for r in range(5):
                    for c in range(5):
                        x0 = z_x_start + c * side; x1 = x0 + side
                        y1 = z_y_start + (5 - r) * side; y0 = y1 - side
                        val = display_grid[r, c]
                        
                        color = f"rgba(255, {max(0, 255-int(val*2.5))}, 0, 0.95)" if val > 0 else "rgba(255,255,255,0.15)"
                        
                        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, 
                                      fillcolor=color, line=dict(color="#222", width=1.5))
                        if val > 0:
                            fig.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=str(round(val,1)),
                                               showarrow=False, font=dict(size=24, color="white", weight="bold"))

            # 7. 真ん中9マスの赤枠（さらに太く強調）
            fig.add_shape(type="rect", x0=z_x_start + side, x1=z_x_start + 4*side, 
                          y0=z_y_start + side, y1=z_y_start + 4*side, 
                          line=dict(color="#ff2222", width=10))

            fig.update_layout(
                width=1100, height=1000,
                xaxis=dict(range=[-200, 200], visible=False, fixedrange=True),
                yaxis=dict(range=[-30, 420], visible=False, fixedrange=True),
                margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(vdf)
