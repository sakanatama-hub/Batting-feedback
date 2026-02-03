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

# ストライクゾーン定義 (cm)
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

# --- データ処理関数 ---
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
    save_df = new_df.copy()
    if 'DateTime' in save_df.columns:
        save_df['DateTime'] = save_df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    csv_content = save_df.to_csv(index=False)
    b64_content = base64.b64encode(csv_content.encode()).decode()
    data = {"message": "Update batting data", "content": b64_content}
    if sha:
        data["sha"] = sha
    put_res = requests.put(url, headers=headers, json=data)
    return put_res.status_code in [200, 201]

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
        grid[r, c] += row[metric]; counts[r, c] += 1
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

    with tab1:
        st.title("🔵 個人別打撃分析")
        if not db_df.empty:
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            with c1: target_player = st.selectbox("選手を選択", PLAYERS)
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            if not pdf.empty:
                pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
                with c2: date_range = st.date_input("分析期間", value=(pdf['Date_Only'].min(), pdf['Date_Only'].max()))
                with c3:
                    sel_conds = st.multiselect("打撃条件", pdf['スイング条件'].unique().tolist(), default=pdf['スイング条件'].unique().tolist())
                with c4:
                    v_idx = pdf.columns.get_loc("オンプレーンスコア")
                    target_metric = st.selectbox("分析指標", pdf.columns[v_idx:].tolist())

                vdf = pdf[(pdf['Date_Only'] >= date_range[0]) & (pdf['Date_Only'] <= date_range[1]) & (pdf['スイング条件'].isin(sel_conds))].copy() if isinstance(date_range, tuple) and len(date_range) == 2 else pdf.copy()

                if not vdf.empty:
                    st.subheader(f"📊 {target_metric}：コース別平均")
                    fig_heat = go.Figure()
                    fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
                    fig_heat.add_shape(type="path", path="M -25 70 L 25 70 L 25 45 L 0 5 L -25 45 Z", fillcolor="white", line=dict(color="#444", width=3))

                    # --- 9:8 比率調整 (1マス 横60:縦53.3) ---
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
                    
                    # 赤枠
                    fig_heat.add_shape(type="rect", x0=z_x_start+grid_w, x1=z_x_start+4*grid_w, y0=z_y_start+grid_h, y1=z_y_start+4*grid_h, line=dict(color="red", width=4))
                    fig_heat.update_layout(width=900, height=600, xaxis=dict(range=[-320, 320], visible=False), yaxis=dict(range=[-40, 520], visible=False), margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_heat, use_container_width=True)

                    # インパクトポイント
                    st.subheader(f"📍 {target_metric}：インパクトポイント")
                    fig_point = go.Figure()
                    fig_point.add_shape(type="rect", x0=-250, x1=250, y0=-50, y1=300, fillcolor="#8B4513", line_width=0, layer="below")
                    fig_point.add_shape(type="rect", x0=SZ_X_MIN, x1=SZ_X_MAX, y0=SZ_Y_MIN, y1=SZ_Y_MAX, line=dict(color="white", width=4))
                    for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                        dot_color, _ = get_color(row[target_metric], target_metric)
                        fig_point.add_trace(go.Scatter(x=[row['StrikeZoneX']], y=[row['StrikeZoneY']], mode='markers', marker=dict(size=14, color=dot_color, line=dict(width=1, color="white")), showlegend=False))
                    
                    # 9:8 比率のための補正
                    visual_ratio = (8/9) / ((SZ_Y_MAX - SZ_Y_MIN) / (SZ_X_MAX - SZ_X_MIN))
                    fig_point.update_layout(height=700, xaxis=dict(range=[-130, 130], visible=False), yaxis=dict(range=[-20, 230], visible=False, scaleanchor="x", scaleratio=visual_ratio), margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_point, use_container_width=True)

    with tab2:
        st.title("⚔️ 比較分析")
        if not db_df.empty:
            v_idx = db_df.columns.get_loc("オンプレーンスコア")
            comp_metric = st.selectbox("比較指標", db_df.columns[v_idx:].tolist(), key="c_m")
            fdf = db_df.copy()
            is_time = "スイング時間" in comp_metric
            top3_names = fdf.groupby('Player Name')[comp_metric].mean().sort_values(ascending=is_time).head(3).index.tolist()
            t_cols = st.columns(3)
            for i, name in enumerate(top3_names):
                with t_cols[i]:
                    st.write(f"**{i+1}位: {name}**")
                    grid = get_3x3_grid(fdf[fdf['Player Name'] == name], comp_metric)
                    fig = go.Figure(data=go.Heatmap(z=grid, x=['外','中','内'] if PLAYER_HANDS[name]=="左" else ['内','中','外'], y=['高','中','低'], colorscale='RdBu' if is_time else 'Blues', reversescale=is_time, showscale=False))
                    fig.update_layout(height=300, margin=dict(l=10,r=10,t=30,b=10), yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig, use_container_width=True, key=f"t3_{i}")

            st.markdown("---")
            ca, cb = st.columns(2)
            pa, pb = ca.selectbox("選手A", PLAYERS, key="pa"), cb.selectbox("選手B", PLAYERS, key="pb")
            if pa and pb:
                ga, gb = get_3x3_grid(fdf[fdf['Player Name'] == pa], comp_metric), get_3x3_grid(fdf[fdf['Player Name'] == pb], comp_metric)
                p_cols = st.columns(2)
                for idx, (name, mine, yours) in enumerate([(pa, ga, gb), (pb, gb, ga)]):
                    with p_cols[idx]:
                        fig_p = go.Figure()
                        for r in range(3):
                            for c in range(3):
                                v, ov = mine[r, c], yours[r, c]
                                fig_p.add_shape(type="rect", x0=c-0.5, x1=c+0.5, y0=r-0.5, y1=r+0.5, fillcolor="white", line=dict(color="gray"))
                                if v > 0: fig_p.add_annotation(x=c, y=r, text=f"{v:.1f}", showarrow=False, font=dict(color="red" if ((v<ov) if is_time else (v>ov)) else "blue", weight="bold"))
                        fig_p.update_layout(height=400, title=name, yaxis=dict(autorange="reversed"))
                        st.plotly_chart(fig_p, use_container_width=True, key=f"cp_{idx}")

    with tab3:
        st.title("📝 データ登録")
        c1, c2 = st.columns(2)
        reg_p = c1.selectbox("選手選択", PLAYERS, key="rp")
        reg_d = c2.date_input("打撃日", value=datetime.date.today())
        up = st.file_uploader("Excelアップロード", type=["xlsx"])
        if up and st.button("GitHubへ保存"):
            try:
                idf = pd.read_excel(up)
                idf = idf.rename(columns={'time':'time_col','ExitVelocity':'打球速度','PitchBallVelocity':'投球速度','LaunchAngle':'打球角度','ExitDirection':'打球方向','Spin':'回転数','Distance':'飛距離','SpinDirection':'回転方向'})
                idf['Player Name'], idf['DateTime'] = reg_p, pd.to_datetime(reg_d.strftime('%Y-%m-%d') + ' ' + idf['time_col'].astype(str))
                if save_to_github(pd.concat([db_df, idf], ignore_index=True)): st.success("保存完了！"); st.rerun()
            except Exception as e: st.error(f"エラー: {e}")
