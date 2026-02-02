import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import requests
import base64
import io

# --- 基本設定 ---
PW = "TOYOTABASEBALLCLUB"
GITHUB_USER = "sakanatama-hub"
GITHUB_REPO = "Batting-feedback"
GITHUB_FILE_PATH = "data.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

PLAYER_HANDS = {
    "#1 熊田 任洋": "左", "#2 逢澤 崚介": "左", "#3 三塚 武蔵": "左", 
    "#4 北村 祥治": "右", "#5 前田 健伸": "左", "#6 佐藤 勇基": "右", 
    "#7 西村 友哉": "右", "#8 和田 佳大": "左", "#9 今泉 颯太": "右", 
    "#10 福井 章吾": "左", "#22 高祖 健輔": "左", "#23 箱山 遥人": "右", 
    "#24 坂巻 尚哉": "右", "#26 西村 彰浩": "左", "#27 小畑 尋規": "右", 
    "#28 宮崎 仁斗": "右", "#29 徳本 健太朗": "左", "#39 柳 元珍": "左", 
    "#99 尾瀬 雄大": "左"
}
PLAYERS = list(PLAYER_HANDS.keys())

def load_data_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}?nocache={datetime.datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        return df
    except:
        return pd.DataFrame()

def save_to_github(new_df):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    csv_content = new_df.to_csv(index=False)
    b64_content = base64.b64encode(csv_content.encode()).decode()
    data = {"message": "Update batting data", "content": b64_content}
    if sha: data["sha"] = sha
    put_res = requests.put(url, headers=headers, json=data)
    return put_res.status_code in [200, 201]

def get_color(val, metric_name):
    if val == 0 or pd.isna(val): return "rgba(255, 255, 255, 0.1)", "white"
    if "スイング時間" in metric_name:
        base, sensitivity = 0.15, 0.05
    elif "アッパースイング度" in metric_name:
        base, sensitivity = 10.5, 15
    else:
        base, sensitivity = 105, 30
    diff = val - base
    intensity = min(abs(diff) / sensitivity, 1.0)
    if "スイング時間" in metric_name:
        color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff < 0 else f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
    else:
        color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff > 0 else f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
    return color, ("black" if intensity < 0.4 else "white")

# --- UI設定 ---
st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
if "ok" not in st.session_state: st.session_state["ok"] = False

if not st.session_state["ok"]:
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("PASSWORD", type="password")
    if st.button("LOGIN"):
        if val == PW: st.session_state["ok"] = True; st.rerun()
else:
    db_df = load_data_from_github()
    tab1, tab2, tab3 = st.tabs(["👤 個人分析", "⚔️ 比較分析", "📝 データ登録"])

    with tab1:
        st.title("🔵 個人別打撃分析")
        if not db_df.empty:
            c1, c2, c3 = st.columns([2, 3, 3])
            with c1: target_player = st.selectbox("選手を選択", PLAYERS, key="p_tab1")
            hand = PLAYER_HANDS[target_player]
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            if not pdf.empty:
                pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
                with c2:
                    date_range = st.date_input("分析期間を選択", value=(pdf['Date_Only'].min(), pdf['Date_Only'].max()), key="range_tab1")
                
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_date, end_date = date_range
                    vdf = pdf[(pdf['Date_Only'] >= start_date) & (pdf['Date_Only'] <= end_date)].copy()
                else:
                    vdf = pd.DataFrame()

                metrics = [c for c in pdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
                with c3: target_metric = st.selectbox("分析指標", metrics if metrics else ["データなし"], key="m_tab1")

                if not vdf.empty:
                    st.subheader(f"📊 {target_metric}：期間内平均")
                    fig_heat = go.Figure()
                    fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
                    L_x, L_y, R_x, R_y = 125, 140, -125, 140
                    fig_heat.add_shape(type="path", path=f"M {R_x} {R_y} L -450 600 L 450 600 L {L_x} {L_y} Z", fillcolor="#8B4513", line_width=0, layer="below")
                    fig_heat.add_shape(type="circle", x0=-120, x1=120, y0=-50, y1=160, fillcolor="#8B4513", line_width=0, layer="below")
                    fig_heat.add_shape(type="path", path="M -25 70 L 25 70 L 25 45 L 0 5 L -25 45 Z", fillcolor="white", line=dict(color="#444", width=3), layer="below")
                    box_style = dict(fillcolor="rgba(255, 255, 255, 0.1)", line=dict(color="rgba(255,255,255,0.8)", width=4), layer="below")
                    fig_heat.add_shape(type="path", path="M 130 20 L 65 20 L 60 140 L 125 140 Z", **box_style)
                    fig_heat.add_shape(type="path", path="M -130 20 L -65 20 L -60 140 L -125 140 Z", **box_style)
                    
                    grid_side = 55
                    z_x_start, z_y_start = -(grid_side * 2.5), 180 
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
                            logic_c = c if hand == "右" else (4 - c)
                            x0, x1 = z_x_start + c * grid_side, z_x_start + (c+1) * grid_side
                            y0, y1 = z_y_start + (4-r) * grid_side, z_y_start + (5-r) * grid_side
                            val = display_grid[r, logic_c]
                            color, f_color = get_color(val, target_metric)
                            fig_heat.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color, line=dict(color="#222", width=1.5))
                            if val > 0:
                                txt = f"{val:.3f}" if "時間" in target_metric else f"{val:.1f}"
                                fig_heat.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=txt, showarrow=False, font=dict(size=18, color=f_color, weight="bold"))
                    
                    fig_heat.update_layout(width=900, height=650, xaxis=dict(range=[-320, 320], visible=False), yaxis=dict(range=[-40, 520], visible=False), margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_heat, use_container_width=True)

                    st.subheader(f"📍 {target_metric}：インパクトポイント")
                    fig_point = go.Figure()
                    fig_point.add_shape(type="rect", x0=-150, x1=150, y0=-50, y1=200, fillcolor="#8B4513", line_width=0, layer="below")
                    fig_point.add_shape(type="path", path="M -30 15 L 30 15 L 30 8 L 0 0 L -30 8 Z", fillcolor="white", line=dict(color="#444", width=2))
                    sc, y_off = 1.2, 40
                    bx = 75 if hand == "左" else -75
                    fig_point.add_shape(type="rect", x0=bx-15, x1=bx+15, y0=20, y1=140, fillcolor="rgba(200,200,200,0.4)", line_width=0)
                    fig_point.add_shape(type="circle", x0=bx-10, x1=bx+10, y0=145, y1=175, fillcolor="rgba(200,200,200,0.4)", line_width=0)
                    fig_point.add_shape(type="rect", x0=-35, x1=35, y0=35, y1=115, line=dict(color="rgba(255,255,255,0.8)", width=4))
                    
                    plot_data = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                    for _, row in plot_data.iterrows():
                        dot_color, _ = get_color(row[target_metric], target_metric)
                        fig_point.add_trace(go.Scatter(x=[row['StrikeZoneX'] * sc], y=[row['StrikeZoneY'] + y_off], mode='markers', marker=dict(size=14, color=dot_color, line=dict(width=1.2, color="white")), text=f"{row[target_metric]}", hoverinfo='text', showlegend=False))
                    fig_point.update_layout(width=900, height=550, xaxis=dict(range=[-150, 150], visible=False), yaxis=dict(range=[-20, 200], visible=False), margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_point, use_container_width=True)

    with tab2:
        st.title("⚔️ 選手間比較分析（上位3名）")
        if not db_df.empty:
            all_metrics = [c for c in db_df.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            comp_metric = st.selectbox("比較する指標を選択", all_metrics, key="m_tab2")
            
            ascending_flag = ("スイング時間" in comp_metric)
            top3_names = db_df.groupby('Player Name')[comp_metric].mean().sort_values(ascending=ascending_flag).head(3).index.tolist()
            
            cols = st.columns(3)
            for i, name in enumerate(top3_names):
                with cols[i]:
                    st.subheader(f"{i+1}位: {name}")
                    p_data = db_df[db_df['Player Name'] == name]
                    grid = np.zeros((3, 3)); counts = np.zeros((3, 3))
                    
                    for _, row in p_data.dropna(subset=['StrikeZoneX', 'StrikeZoneY', comp_metric]).iterrows():
                        c = 0 if row['StrikeZoneX'] < -9.6 else 1 if row['StrikeZoneX'] <= 9.6 else 2
                        r = 0 if row['StrikeZoneY'] > 88.3 else 1 if row['StrikeZoneY'] > 66.6 else 2
                        grid[r, c] += row[comp_metric]; counts[r, c] += 1
                    
                    avg_grid = np.where(counts > 0, grid / counts, 0)
                    hand_label = PLAYER_HANDS[name]
                    x_labels = ['内', '中', '外'] if hand_label == "右" else ['外', '中', '内']
                    
                    # カラースケールの設定
                    is_time = "スイング時間" in comp_metric
                    c_scale = 'RdBu' if is_time else 'Blues'
                    
                    fig = go.Figure(data=go.Heatmap(
                        z=avg_grid, x=x_labels, y=['高', '中', '低'],
                        colorscale=c_scale,
                        reversescale=True if is_time else False, showscale=False
                    ))
                    
                    # マスの最大値・最小値を取得して文字色判定に使用
                    max_val = avg_grid.max()
                    min_val = avg_grid[avg_grid > 0].min() if any(avg_grid > 0) else 0
                    
                    for r in range(3):
                        for c in range(3):
                            val = avg_grid[r, c]
                            if val > 0:
                                # 💡 文字色ロジックの改善: 背景色が濃い(端に近い)場合は白、薄い場合は黒
                                # スイング時間の場合は小さいほど濃い(赤)、速度などの場合は大きいほど濃い(青)
                                if is_time:
                                    font_color = "white" if val < (min_val + (max_val - min_val) * 0.3) else "black"
                                else:
                                    font_color = "white" if val > (min_val + (max_val - min_val) * 0.7) else "black"
                                
                                txt = f"{val:.3f}" if is_time else f"{val:.1f}"
                                fig.add_annotation(x=c, y=r, text=txt, showarrow=False, font=dict(color=font_color, weight="bold"))

                    fig.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20), xaxis=dict(side="top"))
                    st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.title("📝 Excelデータ一括登録")
        with st.expander("登録設定", expanded=True):
            col1, col2 = st.columns(2)
            with col1: reg_player = st.selectbox("登録する選手を選択", PLAYERS, key="reg_p_tab3")
            with col2: reg_date = st.date_input("登録する日付を選択", datetime.date.today(), key="reg_d_tab3")
        uploaded_file = st.file_uploader("Excelファイルをアップロード (.xlsx)", type=["xlsx"])
        if uploaded_file is not None:
            try:
                input_df = pd.read_excel(uploaded_file)
                if st.button("GitHubへ保存"):
                    input_df['Player Name'] = reg_player
                    input_df['DateTime'] = reg_date.strftime('%Y-%m-%d')
                    updated_db = pd.concat([db_df, input_df], ignore_index=True)
                    if save_to_github(updated_db):
                        st.success("登録完了！")
                        st.balloons()
            except Exception as e:
                st.error(f"エラー: {e}")
