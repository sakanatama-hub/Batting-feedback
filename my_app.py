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

    # 図を大きく見せるためにカラム幅を調整
    _, center_col, _ = st.columns([0.2, 8, 0.2])

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

            fig = go.Figure()

            # 1. 地面：深緑
            fig.add_shape(type="rect", x0=-200, x1=200, y0=-50, y1=250, fillcolor="#1a4314", line_width=0, layer="below")
            
            # 2. ホームベース：【自然なパース】
            # 投手側から見て違和感のない比率に調整（尖った部分はy=10から開始）
            fig.add_shape(type="path", path="M -12 40 L 12 40 L 12 28 L 0 10 L -12 28 Z", 
                          fillcolor="white", line=dict(color="#444", width=2), layer="below")
            
            # 3. バッターボックス：パース付き
            box_line = dict(color="rgba(255,255,255,0.6)", width=3)
            fig.add_shape(type="path", path="M -55 10 L -22 10 L -18 80 L -48 80 Z", line=box_line, layer="below")
            fig.add_shape(type="path", path="M 55 10 L 22 10 L 18 80 L 50 80 Z", line=box_line, layer="below")

            # 4. ファウルライン
            line_style = dict(color="white", width=4)
            fig.add_shape(type="line", x0=-48, y0=80, x1=-150, y1=240, line=line_style, layer="below")
            fig.add_shape(type="line", x0=48, y0=80, x1=150, y1=240, line=line_style, layer="below")

            # 5. グリッド：25分割【各マスを正方形に固定】
            # x範囲90、y範囲90で設定することで、各マスが18x18の正方形になる
            z_x = [-45, 45]
            z_y = [105, 195] 
            w_u = 18 # (45 - (-45)) / 5
            h_u = 18 # (195 - 105) / 5

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
                        xs = z_x[0] + c * w_u; xe = xs + w_u
                        ys = z_y[1] - (r + 1) * h_u; ye = ys + h_u
                        
                        val = display_grid[r, c]
                        color = f"rgba(255, {max(0, 255-int(val*2.2))}, 0, 0.85)" if val > 0 else "rgba(255,255,255,0.08)"
                        
                        fig.add_shape(type="rect", x0=xs, x1=xe, y0=ys, y1=ye, 
                                      fillcolor=color, line=dict(color="#333", width=1))
                        if val > 0:
                            fig.add_annotation(x=(xs+xe)/2, y=(ys+ye)/2, text=str(round(val,1)),
                                               showarrow=False, font=dict(size=16, color="white", weight="bold"))

            # 6. 真ん中の9マスに赤枠（3w_u x 3h_u の範囲）
            fig.add_shape(type="rect", 
                          x0=z_x[0] + w_u, x1=z_x[0] + 4*w_u, 
                          y0=z_y[1] - 4*h_u, y1=z_y[1] - h_u, 
                          line=dict(color="#ff2222", width=6))

            # 図を大きく、かつアスペクト比を1:1に近づける
            fig.update_layout(
                width=1000, height=800,
                xaxis=dict(range=[-110, 110], visible=False, fixedrange=True),
                yaxis=dict(range=[-10, 210], visible=False, fixedrange=True),
                margin=dict(l=0, r=0, t=30, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(vdf)
