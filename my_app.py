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

    # 完全な中央配置のためのダミーカラム
    _, center_col, _ = st.columns([1, 4, 1])

    with center_col:
        c1, c2 = st.columns(2)
        with c1: target_player = st.selectbox("選手を選択", PLAYERS)
        
        pdf = db_df[db_df['Player Name'] == target_player].copy()
        if not pdf.empty:
            pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
            with c2: target_date = st.selectbox("日付を選択", sorted(pdf['Date_Only'].unique(), reverse=True))
            vdf = pdf[pdf['Date_Only'] == target_date].copy()
            
            metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            target_metric = st.selectbox("分析指標", metrics if metrics else ["データなし"])

            # --- 図の作成 ---
            fig = go.Figure()

            # 1. 地面：深緑の芝生
            fig.add_shape(type="rect", x0=-150, x1=150, y0=-20, y1=250, fillcolor="#1a4314", line_width=0, layer="below")
            
            # 2. ホームベース：投手視点（尖った方が下）
            fig.add_shape(type="path", path="M -12 40 L 12 40 L 12 25 L 0 10 L -12 25 Z", 
                          fillcolor="white", line=dict(color="#444", width=2), layer="below")
            
            # 3. バッターボックス（左右対称）
            box_line = dict(color="rgba(255,255,255,0.6)", width=3)
            fig.add_shape(type="rect", x0=-50, x1=-18, y0=15, y1=75, line=box_line, layer="below")
            fig.add_shape(type="rect", x0=18, x1=50, y0=15, y1=75, line=box_line, layer="below")

            # 4. ファウルライン（ベースの延長線）
            line_style = dict(color="white", width=4)
            fig.add_shape(type="line", x0=-52, y0=75, x1=-160, y1=210, line=line_style, layer="below")
            fig.add_shape(type="line", x0=52, y0=75, x1=160, y1=210, line=line_style, layer="below")

            # 5. 赤枠とグリッドの完全同期描画
            # 基準となる台形の四隅 (下左, 下右, 上右, 上左)
            trap_x = [-38, 38, 33, -33] 
            trap_y = [100, 100, 150, 150]

            if target_metric != "データなし":
                # グリッド計算
                def get_grid_pos(x, y):
                    r = 0 if y > 110 else 1 if y > 88.2 else 2 if y > 66.6 else 3 if y > 45 else 4
                    c = 0 if x < -28.8 else 1 if x < -9.6 else 2 if x <= 9.6 else 3 if x <= 28.8 else 4
                    return r, c

                grid_val = np.zeros((5, 5)); grid_count = np.zeros((5, 5))
                for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                    r, c = get_grid_pos(row['StrikeZoneX'], row['StrikeZoneY'])
                    grid_val[r, c] += row[target_metric]; grid_count[r, c] += 1
                display_grid = np.where(grid_count > 0, grid_val / grid_count, 0)

                # グリッド描画（赤枠の範囲を5等分して台形を作る）
                for r in range(5):
                    for c in range(5):
                        # yの比率計算
                        y_low_pct = (4 - r) / 5; y_high_pct = (5 - r) / 5
                        y_l = trap_y[0] + (trap_y[2] - trap_y[0]) * y_low_pct
                        y_h = trap_y[0] + (trap_y[2] - trap_y[0]) * y_high_pct
                        
                        # そのy座標におけるxの幅を線形補間
                        xl_start = trap_x[0] + (trap_x[3] - trap_x[0]) * y_low_pct
                        xl_end = trap_x[1] + (trap_x[2] - trap_x[1]) * y_low_pct
                        xh_start = trap_x[0] + (trap_x[3] - trap_x[0]) * y_high_pct
                        xh_end = trap_x[1] + (trap_x[2] - trap_x[1]) * y_high_pct
                        
                        # x方向の5分割
                        xl1 = xl_start + (xl_end - xl_start) * (c / 5); xl2 = xl_start + (xl_end - xl_start) * ((c+1) / 5)
                        xh1 = xh_start + (xh_end - xh_start) * (c / 5); xh2 = xh_start + (xh_end - xh_start) * ((c+1) / 5)
                        
                        val = display_grid[r, c]
                        color = f"rgba(255, {max(0, 255-int(val*2.2))}, 0, 0.85)" if val > 0 else "rgba(255,255,255,0.05)"
                        
                        fig.add_shape(type="path", path=f"M {xl1} {y_l} L {xl2} {y_l} L {xh2} {y_h} L {xh1} {y_h} Z",
                                      fillcolor=color, line=dict(color="#222", width=1))
                        if val > 0:
                            fig.add_annotation(x=(xl1+xl2+xh1+xh2)/4, y=(y_l+y_h)/2,
                                               text=str(round(val,1)), showarrow=False, 
                                               font=dict(size=14, color="white", weight="bold"))

            # 6. ストライクゾーンの赤枠（グリッドの基準点と完全に一致させる）
            fig.add_shape(type="path", 
                          path=f"M {trap_x[0]} {trap_y[0]} L {trap_x[1]} {trap_y[1]} L {trap_x[2]} {trap_y[2]} L {trap_x[3]} {trap_y[3]} Z", 
                          line=dict(color="#ff2222", width=6))

            fig.update_layout(
                width=700, height=700,
                xaxis=dict(range=[-100, 100], visible=False, fixedrange=True),
                yaxis=dict(range=[-10, 220], visible=False, fixedrange=True),
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(vdf)
