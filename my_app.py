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

def get_color(val, metric_name):
    if val == 0: return "rgba(255, 255, 255, 0.1)", "white"
    if "スイング時間" in metric_name:
        base, sensitivity = 0.15, 0.05
        diff = val - base
        intensity = min(abs(diff) / sensitivity, 1.0)
        color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff < 0 else f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
        return color, ("black" if intensity < 0.4 else "white")
    elif "アッパースイング度" in metric_name:
        base, sensitivity = 10.5, 15
        diff = val - base
        intensity = min(abs(diff) / sensitivity, 1.0)
        color = f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)" if diff > 0 else f"rgba({int(255*(1-intensity))}, 255, {int(255*(1-intensity))}, 0.9)"
        return color, ("black" if intensity < 0.4 else "white")
    else:
        base, sensitivity = 105, 30
        diff = val - base
        intensity = min(abs(diff) / sensitivity, 1.0)
        color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff > 0 else f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
        return color, ("black" if intensity < 0.4 else "white")

# --- メイン ---
st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
if "ok" not in st.session_state: st.session_state["ok"] = False

if not st.session_state["ok"]:
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("PASSWORD", type="password")
    if st.button("LOGIN"):
        if val == PW: st.session_state["ok"] = True; st.rerun()
else:
    db_df = load_data_from_github()
    st.title("🔵 選手別打撃分析")

    _, center_col, _ = st.columns([0.1, 8.5, 0.1]) 
    with center_col:
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1: target_player = st.selectbox("選手を選択", PLAYERS)
        pdf = db_df[db_df['Player Name'] == target_player].copy()
        
        if not pdf.empty:
            pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
            with c2: target_date = st.selectbox("日付を選択", sorted(pdf['Date_Only'].unique(), reverse=True))
            vdf = pdf[pdf['Date_Only'] == target_date].copy()
            metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            with c3: target_metric = st.selectbox("分析指標", metrics if metrics else ["データなし"])
            with c4: hand = st.radio("打席", ["右", "左"])

            # 1. ヒートマップ (コード略/前回と同じ)
            # (スペースの都合上省略しますが、既存のfig_heatコードをここに配置してください)
            
            # 2. インパクトポイント (打者シルエット付き)
            st.subheader(f"📍 {target_metric}：インパクトポイント")
            fig_point = go.Figure()
            
            # 背景
            fig_point.add_shape(type="rect", x0=-150, x1=150, y0=-50, y1=200, fillcolor="#8B4513", line_width=0, layer="below")
            fig_point.add_shape(type="path", path="M -30 15 L 30 15 L 30 8 L 0 0 L -30 8 Z", fillcolor="white", line=dict(color="#444", width=2))
            
            sc, y_off = 1.2, 40
            sx_min, sx_max, sy_min, sy_max = -35, 35, 35, 115
            
            # 打者シルエット (簡易描画)
            batter_x = 75 if hand == "左" else -75
            # 胴体・足
            fig_point.add_shape(type="rect", x0=batter_x-15, x1=batter_x+15, y0=20, y1=140, fillcolor="rgba(200,200,200,0.4)", line_width=0)
            # 頭
            fig_point.add_shape(type="circle", x0=batter_x-10, x1=batter_x+10, y0=145, y1=175, fillcolor="rgba(200,200,200,0.4)", line_width=0)
            
            # ストライクゾーン
            fig_point.add_shape(type="rect", x0=sx_min, x1=sx_max, y0=sy_min, y1=sy_max, line=dict(color="rgba(255,255,255,0.8)", width=4))
            for i in range(1, 3):
                vx = sx_min + (sx_max - sx_min) * (i / 3)
                fig_point.add_shape(type="line", x0=vx, x1=vx, y0=sy_min, y1=sy_max, line=dict(color="rgba(255,255,255,0.3)", width=1.5, dash="dot"))
                vy = sy_min + (sy_max - sy_min) * (i / 3)
                fig_point.add_shape(type="line", x0=sx_min, x1=sx_max, y0=vy, y1=vy, line=dict(color="rgba(255,255,255,0.3)", width=1.5, dash="dot"))

            if not vdf.empty:
                plot_data = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                for _, row in plot_data.iterrows():
                    val = row[target_metric]
                    dot_color, _ = get_color(val, target_metric)
                    fig_point.add_trace(go.Scatter(
                        x=[row['StrikeZoneX'] * sc], y=[row['StrikeZoneY'] + y_off], 
                        mode='markers', marker=dict(size=14, color=dot_color, line=dict(width=1.2, color="white")),
                        text=f"{target_metric}: {val}", hoverinfo='text', showlegend=False
                    ))

            fig_point.update_layout(width=900, height=550, xaxis=dict(range=[-150, 150], visible=False), yaxis=dict(range=[-20, 200], visible=False), margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_point, use_container_width=True)
            st.dataframe(vdf)
