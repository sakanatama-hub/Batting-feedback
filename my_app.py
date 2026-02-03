import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import requests
import base64

# --- 基本設定 ---
PW = "1189" 
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

# --- GitHub連携関数 ---
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
    
    # 日付を文字列に変換して保存
    save_df = new_df.copy()
    if 'DateTime' in save_df.columns:
        save_df['DateTime'] = save_df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    csv_content = save_df.to_csv(index=False)
    b64_content = base64.b64encode(csv_content.encode()).decode()
    data = {"message": "Update batting data", "content": b64_content}
    if sha: data["sha"] = sha
    put_res = requests.put(url, headers=headers, json=data)
    return put_res.status_code in [200, 201]

# --- 共通ユーティリティ ---
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
    f_color = "black" if intensity < 0.4 else "white"
    return color, f_color

def get_3x3_grid(df, metric):
    grid = np.zeros((3, 3)); counts = np.zeros((3, 3))
    valid = df.dropna(subset=['StrikeZoneX', 'StrikeZoneY', metric])
    for _, row in valid.iterrows():
        c = 0 if row['StrikeZoneX'] < -9.6 else 1 if row['StrikeZoneX'] <= 9.6 else 2
        r = 0 if row['StrikeZoneY'] > 88.3 else 1 if row['StrikeZoneY'] > 66.6 else 2
        grid[r, c] += row[metric]; counts[r, c] += 1
    return np.where(counts > 0, grid / counts, 0)

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

    # --- TAB 1: 個人分析 (インパクトポイント修正済み) ---
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
                
                vdf = pdf[(pdf['Date_Only'] >= date_range[0]) & (pdf['Date_Only'] <= date_range[1])].copy() if isinstance(date_range, tuple) and len(date_range) == 2 else pdf.copy()
                metrics = [c for c in pdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
                with c3: target_metric = st.selectbox("分析指標", metrics, key="m_tab1")

                if not vdf.empty:
                    st.subheader(f"📊 {target_metric}：期間内平均")
                    fig_heat = go.Figure()
                    fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
                    L_x, L_y, R_x, R_y = 125, 140, -125, 140
                    fig_heat.add_shape(type="path", path=f"M {R_x} {R_y} L -450 600 L 450 600 L {L_x} {L_y} Z", fillcolor="#8B4513", line_width=0, layer="below")
                    fig_heat.add_shape(type="circle", x0=-120, x1=120, y0=-50, y1=160, fillcolor="#8B4513", line_width=0, layer="below")
                    fig_heat.add_shape(type="path", path="M -25 70 L 25 70 L 25 45 L 0 5 L -25 45 Z", fillcolor="white", line=dict(color="#444", width=3), layer="below")
                    
                    grid_side = 55; z_x_start, z_y_start = -(grid_side * 2.5), 180 
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
                            fig_heat.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color, line=dict(color="#222", width=1))
                            if val > 0:
                                txt = f"{val:.3f}" if "時間" in target_metric else f"{val:.1f}"
                                fig_heat.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=txt, showarrow=False, font=dict(size=14, color=f_color, weight="bold"))
                    
                    fig_heat.add_shape(type="rect", x0=z_x_start + grid_side, x1=z_x_start + grid_side * 4, y0=z_y_start + grid_side, y1=z_y_start + grid_side * 4, line=dict(color="red", width=4), layer="above")
                    fig_heat.update_layout(width=900, height=650, xaxis=dict(range=[-320, 320], visible=False), yaxis=dict(range=[-40, 520], visible=False), margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_heat, use_container_width=True, key="p_heat_main")

                    st.subheader(f"📍 {target_metric}：インパクトポイント")
                    fig_point = go.Figure()
                    fig_point.add_shape(type="rect", x0=-250, x1=250, y0=-50, y1=300, fillcolor="#8B4513", line_width=0, layer="below")
                    fig_point.add_shape(type="path", path="M -30 15 L 30 15 L 30 8 L 0 0 L -30 8 Z", fillcolor="white", line=dict(color="#444", width=2))
                    
                    bx = 75 if hand == "左" else -75
                    fig_point.add_shape(type="rect", x0=bx-15, x1=bx+15, y0=20, y1=160, fillcolor="rgba(200,200,200,0.4)", line_width=0)
                    fig_point.add_shape(type="circle", x0=bx-10, x1=bx+10, y0=165, y1=195, fillcolor="rgba(200,200,200,0.4)", line_width=0)
                    fig_point.add_shape(type="rect", x0=-35, x1=35, y0=35, y1=135, line=dict(color="rgba(255,255,255,0.8)", width=4))
                    
                    sc, y_off = 1.2, 40
                    for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                        dot_color, _ = get_color(row[target_metric], target_metric)
                        fig_point.add_trace(go.Scatter(x=[row['StrikeZoneX'] * sc], y=[row['StrikeZoneY'] + y_off], mode='markers', marker=dict(size=14, color=dot_color, line=dict(width=1.2, color="white")), showlegend=False))
                    
                    fig_point.update_layout(height=750, xaxis=dict(range=[-250, 250], visible=False), yaxis=dict(range=[-20, 300], visible=False), margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_point, use_container_width=True, key="p_point_main")

    # --- TAB 2: 比較分析 (修正済み) ---
    with tab2:
        st.title("⚔️ 選手間比較分析")
        if not db_df.empty:
            all_metrics = [c for c in db_df.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            comp_metric = st.selectbox("比較する指標を選択", all_metrics, key="m_tab2")
            is_time = "スイング時間" in comp_metric
            
            st.subheader("🥇 指標別トップ3")
            top3_names = db_df.groupby('Player Name')[comp_metric].mean().sort_values(ascending=is_time).head(3).index.tolist()
            t_cols = st.columns(3)
            for i, name in enumerate(top3_names):
                with t_cols[i]:
                    st.write(f"**{i+1}位: {name}**")
                    grid = get_3x3_grid(db_df[db_df['Player Name'] == name], comp_metric)
                    fig = go.Figure(data=go.Heatmap(z=grid, x=['外','中','内'] if PLAYER_HANDS[name]=="左" else ['内','中','外'], y=['高','中','低'], colorscale='RdBu' if is_time else 'Blues', reversescale=is_time, showscale=False))
                    for r in range(3):
                        for c in range(3):
                            v = grid[r, c]
                            if v > 0:
                                fig.add_annotation(x=c, y=r, text=f"{v:.1f}", showarrow=False, font=dict(color="black", weight="bold", size=16))
                    fig.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(side="top"), yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig, use_container_width=True, key=f"top3_{name}_{i}")

            st.markdown("---")
            st.subheader("🆚 2名ピックアップ比較")
            ca, cb = st.columns(2)
            with ca: player_a = st.selectbox("選手Aを選択", PLAYERS, key="compare_a")
            with cb: player_b = st.selectbox("選手Bを選択", PLAYERS, key="compare_b")
            if player_a and player_b:
                limit = 0.010 if is_time else 5.0
                g_a, g_b = get_3x3_grid(db_df[db_df['Player Name'] == player_a], comp_metric), get_3x3_grid(db_df[db_df['Player Name'] == player_b], comp_metric)
                p_cols = st.columns(2)
                for idx, (name, mine, yours) in enumerate([(player_a, g_a, g_b), (player_b, g_b, g_a)]):
                    with p_cols[idx]:
                        fig_pair = go.Figure()
                        for r in range(3):
                            for c in range(3):
                                v, ov = mine[r,c], yours[r,c]
                                diff = abs(v - ov) if (v > 0 and ov > 0) else 0
                                lw, lc = (5, "yellow") if diff >= limit else (1, "gray")
                                better = (v < ov) if is_time else (v > ov)
                                fc = "red" if better else "blue"
                                fig_pair.add_shape(type="rect", x0=c-0.5, x1=c+0.5, y0=r-0.5, y1=r+0.5, line=dict(color=lc, width=lw), fillcolor="white")
                                if v > 0: fig_pair.add_annotation(x=c, y=r, text=f"{v:.1f}", showarrow=False, font=dict(color=fc, weight="bold", size=16))
                        fig_pair.update_layout(height=400, margin=dict(t=30), xaxis=dict(tickvals=[0,1,2], ticktext=['外','中','内'] if PLAYER_HANDS[name]=="左" else ['内','中','外'], side="top"), yaxis=dict(tickvals=[0,1,2], ticktext=['高','中','低'], autorange="reversed"))
                        st.plotly_chart(fig_pair, use_container_width=True, key=f"pair_{name}_{idx}")

    # --- TAB 3: データ登録 (選手名・日付選択を復活！✨) ---
    with tab3:
        st.title("📝 データ登録")
        
        c1, c2 = st.columns(2)
        with c1:
            reg_player = st.selectbox("登録する選手を選択", PLAYERS, key="reg_p_tab3")
        with c2:
            reg_date = st.date_input("打撃日を選択", value=datetime.date.today(), key="reg_d_tab3")
        
        uploaded_file = st.file_uploader("Excelファイルをアップロード (.xlsx)", type=["xlsx"])
        
        if uploaded_file is not None:
            try:
                input_df = pd.read_excel(uploaded_file)
                st.write("📋 読み込みプレビュー:")
                st.dataframe(input_df.head())
                
                if st.button("GitHubへ保存"):
                    # 選択された選手名と日付を各行にセット
                    input_df['Player Name'] = reg_player
                    # DateTime列を作成（日付のみ、または必要なら時刻も）
                    input_df['DateTime'] = pd.to_datetime(reg_date)
                    
                    # 既存データに結合
                    updated_db = pd.concat([db_df, input_df], ignore_index=True)
                    
                    if save_to_github(updated_db):
                        st.success(f"✅ {reg_player} 選手のデータを {reg_date} 付で保存しました！")
                        st.rerun() # 画面を更新して最新データを反映
                    else:
                        st.error("❌ GitHubへの保存に失敗しました。")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {e}")
