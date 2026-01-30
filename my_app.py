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
    except: return pd.DataFrame()

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

    # 選択エリア
    c1, c2 = st.columns(2)
    with c1: target_player = st.selectbox("選手を選択", PLAYERS)
    
    pdf = db_df[db_df['Player Name'] == target_player].copy()
    if not pdf.empty:
        pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
        with c2: target_date = st.selectbox("日付を選択", sorted(pdf['Date_Only'].unique(), reverse=True))
        vdf = pdf[pdf['Date_Only'] == target_date].copy()
        
        metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
        target_metric = st.selectbox("分析指標", metrics if metrics else ["データなし"])

        # --- 図の作成（ここが左上図の再現） ---
        fig = go.Figure()

        # 1. フィールド背景（イラストのオリーブ色と土色）
        # 芝生
        fig.add_shape(type="rect", x0=-100, x1=100, y0=0, y1=200, fillcolor="#556b2f", line_width=0, layer="below")
        # 土のパース（奥が狭い台形）
        fig.add_shape(type="path", path="M -100 0 L 100 0 L 60 180 L -60 180 Z", fillcolor="#bc8f8f", line_width=0, layer="below")
        
        # 2. 捕手視点のホームベース（上が尖る）
        fig.add_shape(type="path", path="M -10 10 L 10 10 L 10 25 L 0 40 L -10 25 Z", fillcolor="white", line_width=1, layer="below")
        
        # 3. バッターボックス（パース付きで斜めに配置）
        box_line = dict(color="rgba(255,255,255,0.6)", width=3)
        fig.add_shape(type="path", path="M -45 5 L -20 5 L -15 60 L -40 60 Z", line=box_line, layer="below")
        fig.add_shape(type="path", path="M 45 5 L 20 5 L 15 60 L 40 60 Z", line=box_style, layer="below")

        # 4. 立体的なストライクゾーン（上が少し狭い台形のグリッド）
        if target_metric != "データなし":
            # グリッド計算（ここはロジック通り）
            grid = np.random.randint(40, 90, (5, 5)) # サンプル。本来は計算値を代入
            
            # 各マス目をパースをつけて描画（一気に Heatmap ではなく Shape で描画することでイラストを再現）
            for r in range(5):
                for c in range(5):
                    # マス目の四隅を計算（パースをつける）
                    y_start = 70 + (4-r)*20; y_end = y_start + 18
                    x_width_bottom = 50 - (y_start * 0.1) # 上に行くほど幅を狭くする
                    x_width_top = 50 - (y_end * 0.1)
                    
                    x_s = -x_width_bottom + c*(x_width_bottom*2/5)
                    x_e = x_s + (x_width_bottom*2/5)
                    x_s_top = -x_width_top + c*(x_width_top*2/5)
                    x_e_top = x_s_top + (x_width_top*2/5)
                    
                    val = grid[r, c]
                    # 色の決定（YlOrRdスケール）
                    color = f"rgba(255, {255-val*2}, 0, 0.8)"
                    
                    fig.add_shape(type="path", 
                                  path=f"M {x_s} {y_start} L {x_e} {y_start} L {x_e_top} {y_end} L {x_s_top} {y_end} Z",
                                  fillcolor=color, line=dict(color="black", width=1))
                    
                    # 数値の追加
                    fig.add_annotation(x=(x_s+x_e)/2, y=(y_start+y_end)/2, text=str(val), showarrow=False, 
                                       font=dict(size=16, color="white", family="Arial Black"))

        # 5. ストライクゾーンの太い外枠（赤・パース付き）
        fig.add_shape(type="path", path="M -32 88 L 32 88 L 28 152 L -28 152 Z", line=dict(color="#ff0000", width=6))

        fig.update_layout(
            width=800, height=800,
            xaxis=dict(range=[-100, 100], visible=False),
            yaxis=dict(range=[-10, 200], visible=False),
            margin=dict(l=0,r=0,t=0,b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(vdf)
