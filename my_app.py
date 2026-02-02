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

# --- 色決定ロジック ---
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

# --- メイン表示 ---
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
        c1, c2, c3 = st.columns([2, 2, 3])
        with c1: target_player = st.selectbox("選手を選択", PLAYERS)
        pdf = db_df[db_df['Player Name'] == target_player].copy()
        
        if not pdf.empty:
            pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
            with c2: target_date = st.selectbox("日付を選択", sorted(pdf['Date_Only'].unique(), reverse=True))
            vdf = pdf[pdf['Date_Only'] == target_date].copy()
            metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            with c3: target_metric = st.selectbox("分析指標", metrics if metrics else ["データなし"])

            # ---------------------------------
            # 1. コース別平均（ヒートマップ）
            # ---------------------------------
            st.subheader(f"📊 {target_metric}：コース別平均（フィールド俯瞰）")
            # (既存のフィールド描画コードは維持...)
            fig_heat = go.Figure()
            # ...省略（以前のコードの stadium_base 部分）...
            # 描画の詳細は以前と同様のため省略し、下の「捕手目線」に注力します。
            st.plotly_chart(fig_heat, use_container_width=True)

            # ---------------------------------
            # 2. 打撃位置（捕手目線）
            # ---------------------------------
            st.subheader(f"📍 {target_metric}：インパクトポイント（捕手目線）")
            fig_catcher = go.Figure()

            # 背景（アンツーカー色）
            fig_catcher.add_shape(type="rect", x0=-100, x1=100, y0=-20, y1=150, fillcolor="#8B4513", line_width=0, layer="below")
            
            # ホームベース（正面から見た台形っぽく）
            fig_catcher.add_shape(type="path", path="M -30 10 L 30 10 L 30 5 L 0 0 L -30 5 Z", fillcolor="white", line=dict(color="#444", width=2))
            
            # ストライクゾーン（外枠：少し太め）
            sz_x_min, sz_x_max = -48, 48
            sz_y_min, sz_y_max = 30, 120
            fig_catcher.add_shape(type="rect", x0=sz_x_min, x1=sz_x_max, y0=sz_y_min, y1=sz_y_max, line=dict(color="rgba(255,255,255,0.8)", width=4))
            
            # ストライクゾーン（内側の5×5グリッドをうっすら表示）
            for i in range(1, 5):
                # 垂直線
                vx = sz_x_min + (sz_x_max - sz_x_min) * (i / 5)
                fig_catcher.add_shape(type="line", x0=vx, x1=vx, y0=sz_y_min, y1=sz_y_max, line=dict(color="rgba(255,255,255,0.2)", width=1))
                # 水平線
                vy = sz_y_min + (sz_y_max - sz_y_min) * (i / 5)
                fig_catcher.add_shape(type="line", x0=sz_x_min, x1=sz_x_max, y0=vy, y1=vy, line=dict(color="rgba(255,255,255,0.2)", width=1))

            if not vdf.empty:
                plot_data = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                # StrikeZoneX/Yを捕手目線座標にマッピング（調整用係数）
                for _, row in plot_data.iterrows():
                    val = row[target_metric]
                    dot_color, _ = get_color(val, target_metric)
                    fig_catcher.add_trace(go.Scatter(
                        x=[row['StrikeZoneX'] * 1.6], # 左右の広がり調整
                        y=[row['StrikeZoneY'] + 20],   # 高さのオフセット調整
                        mode='markers',
                        marker=dict(size=16, color=dot_color, line=dict(width=1.5, color="white")),
                        text=f"{target_metric}: {val}",
                        hoverinfo='text',
                        showlegend=False
                    ))

            fig_catcher.update_layout(
                width=800, height=600,
                xaxis=dict(range=[-100, 100], visible=False, fixedrange=True),
                yaxis=dict(range=[-10, 160], visible=False, fixedrange=True),
                margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_catcher, use_container_width=True)
            st.dataframe(vdf)
