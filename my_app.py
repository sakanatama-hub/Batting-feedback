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
        color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff > 0 else f"rgba({int(255*(1-intensity))}, 255, {int(255*(1-intensity))}, 0.9)" # その他は赤/青
        if diff < 0: color = f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
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
            # 1. コース別平均（俯瞰：カラーバー付き）
            # ---------------------------------
            st.subheader(f"📊 {target_metric}：コース別平均")
            fig_heat = go.Figure()
            # 俯瞰図の背景描画
            fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
            L_x, L_y, R_x, R_y, Outer_x, Outer_y = 125, 140, -125, 140, 450, 600
            fig_heat.add_shape(type="path", path=f"M {R_x} {R_y} L -{Outer_x} {Outer_y} L {Outer_x} {Outer_y} L {L_x} {L_y} Z", fillcolor="#8B4513", line_width=0, layer="below")
            fig_heat.add_shape(type="circle", x0=-120, x1=120, y0=-50, y1=160, fillcolor="#8B4513", line_width=0, layer="below")
            fig_heat.add_shape(type="path", path="M -25 70 L 25 70 L 25 45 L 0 5 L -25 45 Z", fillcolor="white", line=dict(color="#444", width=3), layer="below")
            box_style = dict(fillcolor="#1a4314", line=dict(color="rgba(255,255,255,0.8)", width=4), layer="below")
            fig_heat.add_shape(type="path", path="M -130 20 L -65 20 L -60 140 L -125 140 Z", **box_style)
            fig_heat.add_shape(type="path", path="M 130 20 L 65 20 L 60 140 L 125 140 Z", **box_style)
            fig_heat.add_shape(type="line", x0=L_x, y0=L_y, x1=Outer_x, y1=Outer_y, line=dict(color="white", width=7), layer="below")
            fig_heat.add_shape(type="line", x0=R_x, y0=R_y, x1=-Outer_x, y1=Outer_y, line=dict(color="white", width=7), layer="below")

            grid_side = 55
            z_x_start, z_y_start = -(grid_side * 2.5), 180 

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
                        x0, x1 = z_x_start + c * grid_side, z_x_start + (c+1) * grid_side
                        y0, y1 = z_y_start + (4-r) * grid_side, z_y_start + (5-r) * grid_side
                        val = display_grid[r, c]
                        color, f_color = get_color(val, target_metric)
                        fig_heat.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color, line=dict(color="#222", width=1.5))
                        if val > 0:
                            txt = str(round(val,3)) if "時間" in target_metric else str(round(val,1))
                            fig_heat.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=txt, showarrow=False, font=dict(size=22, color=f_color, weight="bold"))

                # --- カラーバー（凡例）の追加 ---
                if "スイング時間" in target_metric:
                    colorscale = [[0, "red"], [0.5, "white"], [1, "blue"]]
                    zmin, zmax, tickvals = 0.10, 0.20, [0.10, 0.15, 0.20]
                elif "アッパースイング度" in target_metric:
                    colorscale = [[0, "green"], [0.5, "white"], [1, "blue"]]
                    zmin, zmax, tickvals = -4.5, 25.5, [-4.5, 10.5, 25.5]
                else:
                    colorscale = [[0, "blue"], [0.5, "white"], [1, "red"]]
                    zmin, zmax, tickvals = 75, 105, 135

                fig_heat.add_trace(go.Scatter(
                    x=[None], y=[None], mode='markers',
                    marker=dict(
                        colorscale=colorscale, cmin=zmin, cmax=zmax, showscale=True,
                        colorbar=dict(title=dict(text="基準", font=dict(size=12, color="white")),
                                     tickvals=tickvals, tickfont=dict(color="white", size=10),
                                     thickness=12, x=0.92, xpad=0)
                    ),
                    showlegend=False
                ))

            fig_heat.add_shape(type="rect", x0=z_x_start+grid_side, x1=z_x_start+4*grid_side, y0=z_y_start+grid_side, y1=z_y_start+4*grid_side, line=dict(color="#ff2222", width=6))
            fig_heat.update_layout(width=900, height=650, xaxis=dict(range=[-320, 320], visible=False), yaxis=dict(range=[-40, 520], visible=False), margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_heat, use_container_width=True)

            # ---------------------------------
            # 2. 打撃位置（捕手目線：9分割ガイド）
            # ---------------------------------
            st.subheader(f"📍 {target_metric}：インパクトポイント")
            fig_catcher = go.Figure()
            fig_catcher.add_shape(type="rect", x0=-150, x1=150, y0=-50, y1=200, fillcolor="#8B4513", line_width=0, layer="below")
            fig_catcher.add_shape(type="path", path="M -30 15 L 30 15 L 30 8 L 0 0 L -30 8 Z", fillcolor="white", line=dict(color="#444", width=2))
            
            scale_factor, y_offset = 1.2, 40
            sz_x_min, sz_x_max, sz_y_min, sz_y_max = -35, 35, 35, 115
            fig_catcher.add_shape(type="rect", x0=sz_x_min, x1=sz_x_max, y0=sz_y_min, y1=sz_y_max, line=dict(color="rgba(255,255,255,0.8)", width=4))

            for i in range(1, 3):
                vx = sz_x_min + (sz_x_max - sz_x_min) * (i / 3)
                fig_catcher.add_shape(type="line", x0=vx, x1=vx, y0=sz_y_min, y1=sz_y_max, line=dict(color="rgba(255,255,255,0.3)", width=1.5, dash="dot"))
                vy = sz_y_min + (sz_y_max - sz_y_min) * (i / 3)
                fig_catcher.add_shape(type="line", x0=sz_x_min, x1=sz_x_max, y0=vy, y1=vy, line=dict(color="rgba(255,255,255,0.3)", width=1.5, dash="dot"))

            if not vdf.empty:
                plot_data = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                for _, row in plot_data.iterrows():
                    val = row[target_metric]
                    dot_color, _ = get_color(val, target_metric)
                    fig_catcher.add_trace(go.Scatter(
                        x=[row['StrikeZoneX'] * scale_factor], 
                        y=[row['StrikeZoneY'] + y_offset], 
                        mode='markers',
                        marker=dict(size=14, color=dot_color, line=dict(width=1.2, color="white")),
                        text=f"{target_metric}: {val}", hoverinfo='text', showlegend=False
                    ))

            fig_catcher.update_layout(width=900, height=550, xaxis=dict(range=[-120, 120], visible=False), yaxis=dict(range=[-20, 180], visible=False), margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_catcher, use_container_width=True)
            st.dataframe(vdf)
