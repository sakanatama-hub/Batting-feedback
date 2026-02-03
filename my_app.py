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

# --- ストライクゾーン定義 (cm) ---
SZ_X_MIN, SZ_X_MAX = -28.8, 28.8
SZ_X_TH1, SZ_X_TH2 = -9.6, 9.6
SZ_Y_MIN, SZ_Y_MAX = 45.0, 110.0
SZ_Y_TH1, SZ_Y_TH2 = 66.6, 88.3

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
            # 安全に日付型へ変換 (errors='coerce' で不正値は NaT になる)
            df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
            # NaT (日付として無効な行) を削除
            df = df.dropna(subset=['DateTime'])
        return df
    except:
        return pd.DataFrame()

def save_to_github(new_df):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    save_df = new_df.copy()
    if 'DateTime' in save_df.columns:
        # 再度、日付型であることを保証してから文字列フォーマットを適用
        save_df['DateTime'] = pd.to_datetime(save_df['DateTime'], errors='coerce')
        save_df = save_df.dropna(subset=['DateTime'])
        save_df['DateTime'] = save_df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    csv_content = save_df.to_csv(index=False)
    b64_content = base64.b64encode(csv_content.encode()).decode()
    data = {"message": "Update batting data", "content": b64_content}
    if sha:
        data["sha"] = sha
    put_res = requests.put(url, headers=headers, json=data)
    return put_res.status_code in [200, 201]

# --- 共通ユーティリティ ---
def get_color(val, metric_name):
    if val == 0 or pd.isna(val):
        return "rgba(255, 255, 255, 0.1)", "white"
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
    grid = np.zeros((3, 3))
    counts = np.zeros((3, 3))
    valid = df.dropna(subset=['StrikeZoneX', 'StrikeZoneY', metric])
    for _, row in valid.iterrows():
        c = 0 if row['StrikeZoneX'] < SZ_X_TH1 else 1 if row['StrikeZoneX'] <= SZ_X_TH2 else 2
        r = 0 if row['StrikeZoneY'] > SZ_Y_TH2 else 1 if row['StrikeZoneY'] > SZ_Y_TH1 else 2
        grid[r, c] += row[metric]
        counts[r, c] += 1
    return np.where(counts > 0, grid / counts, 0)

# --- UI設定 ---
st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
if "ok" not in st.session_state:
    st.session_state["ok"] = False

if not st.session_state["ok"]:
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("PASSWORD", type="password")
    if st.button("LOGIN"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
else:
    db_df = load_data_from_github()
    tab1, tab2, tab3 = st.tabs(["👤 個人分析", "⚔️ 比較分析", "📝 データ登録"])

    # --- TAB 1: 個人分析 ---
    with tab1:
        st.title("🔵 個人別打撃分析")
        if not db_df.empty:
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            with c1:
                target_player = st.selectbox("選手を選択", PLAYERS, key="p_tab1")
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            if not pdf.empty:
                # 日付計算前に型を再確認
                pdf['DateTime'] = pd.to_datetime(pdf['DateTime'], errors='coerce')
                pdf = pdf.dropna(subset=['DateTime'])
                pdf['Date_Only'] = pdf['DateTime'].dt.date
                
                with c2:
                    date_range = st.date_input("分析期間", value=(pdf['Date_Only'].min(), pdf['Date_Only'].max()), key="range_tab1")
                with c3:
                    all_conds = pdf['スイング条件'].unique().tolist()
                    sel_conds = st.multiselect("打撃条件", all_conds, default=all_conds, key="cond_tab1")
                with c4:
                    v_idx = pdf.columns.get_loc("オンプレーンスコア")
                    all_metrics = pdf.columns[v_idx:].tolist()
                    priority = ["バットスピード (km/h)", "スイング時間 (秒)", "アッパースイング度 (°)"]
                    sorted_metrics = [m for m in priority if m in all_metrics] + [m for m in all_metrics if m not in priority]
                    target_metric = st.selectbox("分析指標", sorted_metrics, key="m_tab1")

                vdf = pdf[(pdf['Date_Only'] >= date_range[0]) & (pdf['Date_Only'] <= date_range[1]) & (pdf['スイング条件'].isin(sel_conds))].copy() if isinstance(date_range, tuple) and len(date_range) == 2 else pdf.copy()

                if not vdf.empty:
                    st.subheader(f"📊 {target_metric}：コース別平均")
                    fig_heat = go.Figure()
                    fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
                    
                    # --- 9:8 比率調整 ---
                    grid_w, grid_h = 60, 53.3
                    z_x_start, z_y_start = -(grid_w * 2.5), 180

                    def get_grid_pos(x, y):
                        r = 0 if y > SZ_Y_MAX else 1 if y > SZ_Y_TH2 else 2 if y > SZ_Y_TH1 else 3 if y > SZ_Y_MIN else 4
                        c = 0 if x < SZ_X_MIN else 1 if x < SZ_X_TH1 else 2 if x <= SZ_X_TH2 else 3 if x <= SZ_X_MAX else 4
                        return r, c
                    
                    grid_val = np.zeros((5, 5)); grid_count = np.zeros((5, 5))
                    for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                        r, c = get_grid_pos(row['StrikeZoneX'], row['StrikeZoneY'])
                        grid_val[r, c] += row[target_metric]; grid_count[r, c] += 1
                    display_grid = np.where(grid_count > 0, grid_val / grid_count, 0)
                    
                    hand = PLAYER_HANDS[target_player]
                    for r in range(5):
                        for c in range(5):
                            logic_c = c if hand == "右" else (4 - c)
                            x0, x1 = z_x_start + c * grid_w, z_x_start + (c + 1) * grid_w
                            y0, y1 = z_y_start + (4 - r) * grid_h, z_y_start + (5 - r) * grid_h
                            val = display_grid[r, logic_c]
                            color, f_color = get_color(val, target_metric)
                            fig_heat.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color, line=dict(color="#222", width=1))
                            if val > 0:
                                txt = f"{val:.3f}" if "時間" in target_metric else f"{val:.1f}"
                                fig_heat.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=txt, showarrow=False, font=dict(size=14, color=f_color, weight="bold"))
                    
                    fig_heat.add_shape(type="rect", x0=z_x_start+grid_w, x1=z_x_start+4*grid_w, y0=z_y_start+grid_h, y1=z_y_start+4*grid_h, line=dict(color="red", width=4))
                    fig_heat.update_layout(width=900, height=600, xaxis=dict(range=[-320, 320], visible=False), yaxis=dict(range=[-40, 520], visible=False), margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_heat, use_container_width=True)

    # --- TAB 2: 比較分析 ---
    with tab2:
        st.title("⚔️ 選手間比較分析")
        if not db_df.empty:
            v_idx = db_df.columns.get_loc("オンプレーンスコア")
            comp_metric = st.selectbox("比較指標", db_df.columns[v_idx:].tolist(), key="m_tab2")
            is_time = "スイング時間" in comp_metric
            top3_names = db_df.groupby('Player Name')[comp_metric].mean().sort_values(ascending=is_time).head(3).index.tolist()
            t_cols = st.columns(3)
            for i, name in enumerate(top3_names):
                with t_cols[i]:
                    st.write(f"**{i+1}位: {name}**")
                    grid = get_3x3_grid(db_df[db_df['Player Name'] == name], comp_metric)
                    fig = go.Figure(data=go.Heatmap(z=grid, x=['外','中','内'] if PLAYER_HANDS[name]=="左" else ['内','中','外'], y=['高','中','低'], colorscale='RdBu' if is_time else 'Blues', reversescale=is_time, showscale=False))
                    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig, use_container_width=True, key=f"top3_{i}")

    # --- TAB 3: データ登録 ---
    with tab3:
        st.title("📝 データ登録")
        c1, c2 = st.columns(2)
        with c1: reg_player = st.selectbox("登録する選手を選択", PLAYERS, key="reg_p_tab3")
        with c2: reg_date = st.date_input("打撃日を選択", value=datetime.date.today(), key="reg_d_tab3")
        
        uploaded_file = st.file_uploader("Excelファイルをアップロード (.xlsx)", type=["xlsx"])
        
        if uploaded_file is not None:
            try:
                input_df = pd.read_excel(uploaded_file)
                cmap = {'time': 'time_col', 'ExitVelocity': '打球速度', 'PitchBallVelocity': '投球速度', 'LaunchAngle': '打球角度', 'ExitDirection': '打球方向', 'Spin': '回転数', 'Distance': '飛距離', 'SpinDirection': '回転方向'}
                input_df = input_df.rename(columns=cmap)
                
                if st.button("GitHubへ保存"):
                    input_df['Player Name'] = reg_player
                    date_str = reg_date.strftime('%Y-%m-%d')
                    # 安全な日時結合 (errors='coerce' で変換不能な行を排除)
                    input_df['DateTime'] = pd.to_datetime(date_str + ' ' + input_df['time_col'].astype(str), errors='coerce')
                    input_df = input_df.dropna(subset=['DateTime'])
                    
                    updated_db = pd.concat([db_df, input_df], ignore_index=True)
                    if save_to_github(updated_db):
                        st.success(f"✅ {reg_player} 選手のデータを保存しました！")
                        st.rerun()
            except Exception as e:
                st.error(f"❌ エラー: {e}")
