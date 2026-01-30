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

    _, center_col, _ = st.columns([0.1, 8, 0.1])

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

            # --- 背景：芝生（深緑） ---
            fig.add_shape(type="rect", x0=-450, x1=450, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
            
            # --- ラインと土の座標 ---
            L_start_x, L_start_y = 75, 85
            R_start_x, R_start_y = -75, 85
            Outer_x, Outer_y = 450, 550 # 上部まで突き抜ける設定
            
            # フェアゾーンの土（茶色）：上部の隙間をなくすためyを大きめに設定
            fig.add_shape(type="path", 
                          path=f"M {R_start_x} {R_start_y} L -{Outer_x} {Outer_y} L {Outer_x} {Outer_y} L {L_start_x} {L_start_y} Z", 
                          fillcolor="#8B4513", line_width=0, layer="below")
            
            # ホームベース周りの土
            fig.add_shape(type="circle", x0=-65, x1=65, y0=-30, y1=100, fillcolor="#8B4513", line_width=0, layer="below")
            
            # 復元：大きめのホームベース
            fig.add_shape(type="path", path="M -15 50 L 15 50 L 15 35 L 0 5 L -15 35 Z", 
                          fillcolor="white", line=dict(color="#444", width=2.5), layer="below")
            
            # バッターボックス
            box_style = dict(fillcolor="#1a4314", line=dict(color="rgba(255,255,255,0.8)", width=3.5), layer="below")
            fig.add_shape(type="path", path="M -95 15 L -45 15 L -40 105 L -90 105 Z", **box_style)
            fig.add_shape(type="path", path="M 95 15 L 45 15 L 40 105 L 90 105 Z", **box_style)

            # ファウルライン
            fig.add_shape(type="line", x0=L_start_x, y0=L_start_y, x1=Outer_x, y1=Outer_y, line=dict(color="white", width=6), layer="below")
            fig.add_shape(type="line", x0=R_start_x, y0=R_start_y, x1=-Outer_x, y1=Outer_y, line=dict(color="white", width=6), layer="below")

            # --- 25分割グリッド：各マスを厳密に正方形に維持 ---
            grid_side = 38 
            z_x_start = -(grid_side * 2.5)
            z_y_start = 140 
            
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
                        x0 = z_x_start + c * grid_side; x1 = x0 + grid_side
                        y1 = z_y_start + (5 - r) * grid_side; y0 = y1 - grid_side
                        val = display_grid[r, c]
                        
                        color = f"rgba(255, {max(0, 255-int(val*2.5))}, 0, 0.95)" if val > 0 else "rgba(255,255,255,0.18)"
                        
                        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, 
                                      fillcolor=color, line=dict(color="#222", width=1.5))
                        if val > 0:
                            fig.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=str(round(val,1)),
                                               showarrow=False, font=dict(size=22, color="white", weight="bold"))

            # 真ん中9マスの赤枠
            fig.add_shape(type="rect", x0=z_x_start + grid_side, x1=z_x_start + 4*grid_side, 
                          y0=z_y_start + grid_side, y1=z_y_start + 4*grid_side, 
                          line=dict(color="#ff2222", width=9))

            fig.update_layout(
                width=1000, height=700,
                xaxis=dict(range=[-350, 350], visible=False, fixedrange=True),
                # scaleratio=1でグリッドの正方形を担保
                yaxis=dict(range=[-50, 500], visible=False, fixedrange=True, scaleanchor="x", scaleratio=1),
                margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(vdf)
