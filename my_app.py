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

    # 図を最大化するため左右の余白を最小に
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

            # --- 背景とフィールド ---
            # 1. 全体の芝生
            fig.add_shape(type="rect", x0=-200, x1=200, y0=-50, y1=300, fillcolor="#1a4314", line_width=0, layer="below")
            
            # 2. フェアゾーンの土
            fig.add_shape(type="path", path="M -50 85 L -200 280 L 200 280 L 50 85 Z", 
                          fillcolor="#8B4513", line_width=0, layer="below")
            
            # 3. ホームベース周りの土
            fig.add_shape(type="circle", x0=-30, x1=30, y0=-10, y1=60, fillcolor="#8B4513", line_width=0, layer="below")

            # 4. ホームベース
            fig.add_shape(type="path", path="M -12 40 L 12 40 L 12 28 L 0 10 L -12 28 Z", 
                          fillcolor="white", line=dict(color="#444", width=2), layer="below")
            
            # 5. バッターボックス（中を緑に）
            box_style = dict(fillcolor="#1a4314", line=dict(color="rgba(255,255,255,0.8)", width=3), layer="below")
            fig.add_shape(type="path", path="M -55 10 L -22 10 L -18 85 L -48 85 Z", **box_style)
            fig.add_shape(type="path", path="M 55 10 L 22 10 L 18 85 L 50 85 Z", **box_style)

            # 6. ファウルライン
            fig.add_shape(type="line", x0=-48, y0=85, x1=-195, y1=270, line=dict(color="white", width=4), layer="below")
            fig.add_shape(type="line", x0=48, y0=85, x1=195, y1=270, line=dict(color="white", width=4), layer="below")

            # --- 正方形グリッドシステム ---
            # 各マスが完全な正方形になるよう、幅と高さを等しく設定
            side = 20  # 1マスの辺の長さ
            z_x_start = -(side * 2.5)
            z_y_start = 120
            
            if target_metric != "データなし":
                def get_grid_pos(x, y):
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
                        
                        # 色の定義（以前の指示通り、白ベースに映えるYlOrRd系）
                        color = f"rgba(255, {max(0, 255-int(val*2.5))}, 0, 0.9)" if val > 0 else "rgba(255,255,255,0.15)"
                        
                        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, 
                                      fillcolor=color, line=dict(color="#333", width=1))
                        if val > 0:
                            fig.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=str(round(val,1)),
                                               showarrow=False, font=dict(size=18, color="white", weight="bold"))

            # 7. 真ん中9マスの赤枠（3x3部分）
            fig.add_shape(type="rect", x0=z_x_start + side, x1=z_x_start + 4*side, 
                          y0=z_y_start + side, y1=z_y_start + 4*side, 
                          line=dict(color="#ff2222", width=7))

            # 特大サイズかつアスペクト比を維持
            fig.update_layout(
                width=1100, height=900,
                xaxis=dict(range=[-150, 150], visible=False, fixedrange=True),
                yaxis=dict(range=[-20, 280], visible=False, fixedrange=True),
                margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(vdf)
