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

PLAYER_HANDS = {"#1 熊田 任洋": "左", "#2 逢澤 崚介": "左", "#3 三塚 武蔵": "左", "#4 北村 祥治": "右", "#5 前田 健伸": "左", "#6 佐藤 勇基": "右", "#7 西村 友哉": "右", "#8 和田 佳大": "左", "#9 今泉 颯太": "右", "#10 福井 章吾": "左", "#22 高祖 健輔": "左", "#23 箱山 遥人": "右", "#24 坂巻 尚哉": "右", "#26 西村 彰浩": "左", "#27 小畑 尋規": "右", "#28 宮崎 仁斗": "右", "#29 徳本 健太朗": "左", "#39 柳 元珍": "左", "#99 尾瀬 雄大": "左"}
PLAYERS = list(PLAYER_HANDS.keys())

# --- GitHub連携関数 ---
def load_data_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}?nocache={datetime.datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url, dtype=str)
        return df
    except:
        return pd.DataFrame()

def save_to_github(new_df):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    save_df = new_df.copy()
    for col in save_df.columns:
        save_df[col] = save_df[col].astype(str).replace('nan', '').replace('NaT', '')
    csv_content = save_df.to_csv(index=False)
    b64_content = base64.b64encode(csv_content.encode('utf-8-sig')).decode()
    data = {"message": f"Update data {datetime.datetime.now()}", "content": b64_content}
    if sha:
        data["sha"] = sha
    put_res = requests.put(url, headers=headers, json=data)
    return (True, "成功") if put_res.status_code in [200, 201] else (False, f"エラー {put_res.status_code}")

# --- 共通ユーティリティ (加速の大きさの色定義を修正版) ---
def get_color(val, metric_name, row_idx=None):
    if val == 0 or pd.isna(val):
        return "rgba(255, 255, 255, 0.1)", "white"

    # 体の回転によるバットの加速の大きさ (初動) (G)
    if "バットの加速の大きさ" in metric_name:
        if val >= 4.5:
            color = "rgba(255, 0, 0, 0.9)"
            f_color = "white"
        elif 4.0 <= val < 4.5:
            color = "rgba(255, 180, 180, 0.9)"
            f_color = "black"
        elif 3.5 <= val < 4.0:
            color = "rgba(255, 255, 255, 0.9)"
            f_color = "black"
        elif 2.5 <= val < 3.5:
            color = "rgba(180, 180, 255, 0.9)"
            f_color = "black"
        else:
            color = "rgba(0, 0, 255, 0.9)"
            f_color = "white"
        return color, f_color

    # 体とバットの角度 (インパクト)
    if "体とバットの角度" in metric_name:
        if 85 <= val <= 95:
            intensity = 1.0 - (abs(val - 90) / 5.0)
            gb_val = int(255 * (1 - intensity))
            color = f"rgba(255, {gb_val}, {gb_val}, 0.9)"
            f_color = "white" if intensity > 0.5 else "black"
        elif val < 85:
            intensity = min(max((85 - val) / 10.0, 0.0), 1.0)
            rb_val = int(255 * (1 - intensity))
            color = f"rgba({rb_val}, 255, {rb_val}, 0.9)"
            f_color = "black"
        else:
            intensity = min(max((val - 95) / 10.0, 0.0), 1.0)
            rg_val = int(255 * (1 - intensity))
            color = f"rgba({rg_val}, {rg_val}, 255, 0.9)"
            f_color = "white" if intensity > 0.5 else "black"
        return color, f_color

    # アッパースイング度判定
    if "アッパースイング度" in metric_name and row_idx is not None:
        if row_idx == 0: base, low, high = 6.5, 3.0, 10.0
        elif row_idx == 1: base, low, high = 11.5, 8.0, 15.0
        else: base, low, high = 15.0, 10.0, 20.0
        if low <= val <= high:
            sensitivity = (high - low) / 2
            intensity = 1.0 - (abs(val - base) / sensitivity)
            color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)"
        elif val < low:
            diff = low - val
            intensity = min(diff / 15.0, 1.0)
            color = f"rgba({int(255*(1-intensity))}, 255, {int(255*(1-intensity))}, 0.9)"
        else:
            diff = val - high
            intensity = min(diff / 15.0, 1.0)
            color = f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
        return color, "black"

    # バットスピード
    if "バットスピード" in metric_name:
        if val < 100: color = "rgba(0, 0, 255, 0.9)"; f_color = "white"
        elif 100 <= val <= 110: color = "rgba(255, 255, 255, 0.9)"; f_color = "black"
        elif 110 < val < 120:
            intensity = (val - 110) / 10
            gb_val = int(255 * (1 - intensity))
            color = f"rgba(255, {gb_val}, {gb_val}, 0.9)"; f_color = "black" if intensity < 0.6 else "white"
        else: color = "rgba(255, 0, 0, 0.9)"; f_color = "white"
        return color, f_color

    # スイング時間
    if "スイング時間" in metric_name:
        if val < 0.14: color = "rgba(255, 0, 0, 0.9)"; f_color = "white"
        elif 0.14 <= val < 0.15: color = "rgba(255, 180, 180, 0.9)"; f_color = "black"
        elif 0.15 <= val < 0.16: color = "rgba(255, 255, 255, 0.9)"; f_color = "black"
        elif 0.16 <= val < 0.17: color = "rgba(180, 180, 255, 0.9)"; f_color = "black"
        else: color = "rgba(0, 0, 255, 0.9)"; f_color = "white"
        return color, f_color

    # その他
    base, sensitivity = 105, 30
    diff = val - base
    intensity = min(abs(diff) / sensitivity, 1.0)
    color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff > 0 else f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
    f_color = "black" if intensity < 0.4 else "white"
    return color, f_color

def get_3x3_grid(df, metric):
    grid = np.zeros((3, 3))
    counts = np.zeros((3, 3))
    if metric not in df.columns: return grid
    df_c = df.copy()
    df_c['StrikeZoneX'] = pd.to_numeric(df_c['StrikeZoneX'], errors='coerce')
    df_c['StrikeZoneY'] = pd.to_numeric(df_c['StrikeZoneY'], errors='coerce')
    df_c[metric] = pd.to_numeric(df_c[metric], errors='coerce')
    valid = df_c.dropna(subset=['StrikeZoneX', 'StrikeZoneY', metric])
    for _, row in valid.iterrows():
        c = 0 if row['StrikeZoneX'] < SZ_X_TH1 else 1 if row['StrikeZoneX'] <= SZ_X_TH2 else 2
        r = 0 if row['StrikeZoneY'] > SZ_Y_TH2 else 1 if row['StrikeZoneY'] > SZ_Y_TH1 else 2
        grid[r, c] += row[metric]
        counts[r, c] += 1
    return np.where(counts > 0, grid / counts, 0)

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
            db_df['スイング条件_str'] = db_df['スイング条件'].fillna("未設定").astype(str).str.strip()
            all_possible_conds = sorted(db_df['スイング条件_str'].unique().tolist())
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            with c1: target_player = st.selectbox("選手を選択", PLAYERS, key="p_tab1")
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            if not pdf.empty:
                pdf['Date_Only_Str'] = pdf['DateTime'].str[:10]
                pdf['Date_Only'] = pd.to_datetime(pdf['Date_Only_Str'], errors='coerce').dt.date
                valid_dates = pdf['Date_Only'].dropna()
                min_date = min(valid_dates) if not valid_dates.empty else datetime.date(2024,1,1)
                max_date = max(valid_dates) if not valid_dates.empty else datetime.date.today()
                with c2: date_range = st.date_input("分析期間", value=(min_date, max_date), key="range_tab1")
                with c3: sel_conds = st.multiselect("打撃条件 (U列)", all_possible_conds, default=all_possible_conds, key="cond_tab1")
                with c4:
                    all_cols = pdf.columns.tolist()
                    try: v_idx = pdf.columns.get_loc("オンプレーンスコア"); candidates = all_cols[v_idx:]
                    except: candidates = [c for c in all_cols if any(x in c for x in ["速度", "角度", "時間"])]
                    valid_metrics = [c for c in candidates if pd.to_numeric(pdf[c], errors='coerce').dropna().any() and any(ord(char) > 255 for char in c)]
                    priority = ["バットスピード (km/h)", "スイング時間 (秒)", "アッパースイング度 (°)"]
                    sorted_metrics = [m for m in priority if m in valid_metrics] + [m for m in valid_metrics if m not in priority]
                    target_metric = st.selectbox("分析指標", sorted_metrics, key="m_tab1")

                mask = (pdf['スイング条件_str'].isin(sel_conds))
                if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                    mask &= (pdf['Date_Only'] >= date_range[0]) & (pdf['Date_Only'] <= date_range[1])
                vdf = pdf[mask].copy()
                if not vdf.empty:
                    vdf[target_metric] = pd.to_numeric(vdf[target_metric], errors='coerce')
                    valid_vals = vdf[target_metric].dropna()
                    if not valid_vals.empty:
                        m_best = valid_vals.min() if "時間" in target_metric else valid_vals.max()
                        m_avg = valid_vals.mean()
                        col_m1, col_m2, col_m3 = st.columns([2, 2, 4])
                        with col_m1: st.metric(label="期間内 BEST", value=f"{m_best:.3f}" if "時間" in target_metric else f"{m_best:.1f}")
                        with col_m2: st.metric(label="期間内 平均", value=f"{m_avg:.3f}" if "時間" in target_metric else f"{m_avg:.1f}")
                        with col_m3: st.info(f"💡 {len(vdf)}件のスイングを分析中")

                    st.subheader(f"📊 {target_metric}：ゾーン別平均")
                    vdf['StrikeZoneX'] = pd.to_numeric(vdf['StrikeZoneX'], errors='coerce')
                    vdf['StrikeZoneY'] = pd.to_numeric(vdf['StrikeZoneY'], errors='coerce')
                    fig_heat = go.Figure()
                    fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
                    fig_heat.add_shape(type="path", path="M -125 140 L -450 600 L 450 600 L 125 140 Z", fillcolor="#8B4513", line_width=0, layer="below")
                    fig_heat.add_shape(type="circle", x0=-120, x1=120, y0=-50, y1=160, fillcolor="#8B4513", line_width=0, layer="below")
                    fig_heat.add_shape(type="path", path="M -25 70 L 25 70 L 25 45 L 0 5 L -25 45 Z", fillcolor="white", line=dict(color="#444", width=3), layer="below")
                    grid_side = 55; z_x_start, z_y_start = -(grid_side * 2.5), 180
                    def get_grid_pos(x, y):
                        r = 0 if y > SZ_Y_MAX else 1 if y > SZ_Y_TH2 else 2 if y > SZ_Y_TH1 else 3 if y > SZ_Y_MIN else 4
                        c = 0 if x < SZ_X_MIN else 1 if x < SZ_X_TH1 else 2 if x <= SZ_X_TH2 else 3 if x <= SZ_X_MAX else 4
                        return r, c
                    grid_val = np.zeros((5, 5)); grid_count = np.zeros((5, 5))
                    for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                        r, c = get_grid_pos(row['StrikeZoneX'], row['StrikeZoneY'])
                        grid_val[r, c] += row[target_metric]; grid_count[r, c] += 1
                    display_grid = np.where(grid_count > 0, grid_val / grid_count, 0)
                    for r in range(5):
                        for c in range(5):
                            x0, x1 = z_x_start + c * grid_side, z_x_start + (c + 1) * grid_side
                            y0, y1 = z_y_start + (4 - r) * grid_side, z_y_start + (5 - r) * grid_side
                            val = display_grid[r, c]
                            mapped_r = max(0, min(2, r - 1))
                            color, f_color = get_color(val, target_metric, row_idx=mapped_r)
                            fig_heat.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color, line=dict(color="#222", width=1))
                            if val > 0:
                                txt = f"{val:.3f}" if "時間" in target_metric else f"{val:.1f}"
                                fig_heat.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=txt, showarrow=False, font=dict(size=14, color=f_color, weight="bold"))
                    fig_heat.add_shape(type="rect", x0=z_x_start+grid_side, x1=z_x_start+4*grid_side, y0=z_y_start+grid_side, y1=z_y_start+4*grid_side, line=dict(color="red", width=4), layer="above")
                    fig_heat.update_layout(width=900, height=650, xaxis=dict(range=[-320, 320], visible=False), yaxis=dict(range=[-40, 520], visible=False), margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_heat, use_container_width=True)

                    st.subheader(f"📍 {target_metric}：インパクトポイント")
                    fig_point = go.Figure()
                    fig_point.add_shape(type="rect", x0=-250, x1=250, y0=-50, y1=300, fillcolor="#8B4513", line_width=0, layer="below")
                    fig_point.add_shape(type="path", path="M -30 15 L 30 15 L 30 8 L 0 0 L -30 8 Z", fillcolor="white", line=dict(color="#444", width=2))
                    bx = 75 if PLAYER_HANDS.get(target_player, "右") == "左" else -75
                    fig_point.add_shape(type="rect", x0=bx-15, x1=bx+15, y0=20, y1=160, fillcolor="rgba(200,200,200,0.4)", line_width=0)
                    fig_point.add_shape(type="circle", x0=bx-10, x1=bx+10, y0=165, y1=195, fillcolor="rgba(200,200,200,0.4)", line_width=0)
                    fig_point.add_shape(type="rect", x0=SZ_X_MIN, x1=SZ_X_MAX, y0=SZ_Y_MIN, y1=SZ_Y_MAX, line=dict(color="rgba(255,255,255,0.8)", width=4))
                    for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                        r_pt = 0 if row['StrikeZoneY'] > SZ_Y_TH2 else 1 if row['StrikeZoneY'] > SZ_Y_TH1 else 2
                        dot_color, _ = get_color(row[target_metric], target_metric, row_idx=r_pt)
                        fig_point.add_trace(go.Scatter(x=[row['StrikeZoneX']], y=[row['StrikeZoneY']], mode='markers', marker=dict(size=14, color=dot_color, line=dict(width=1.2, color="white")), showlegend=False))
                    fig_point.update_layout(height=750, xaxis=dict(range=[-130, 130], visible=False), yaxis=dict(range=[-20, 230], visible=False))
                    st.plotly_chart(fig_point, use_container_width=True)

    with tab2:
        st.title("⚔️ 比較分析")
        if not db_df.empty:
            all_cols = db_df.columns.tolist()
            try: v_idx = db_df.columns.get_loc("オンプレーンスコア"); all_metrics = all_cols[v_idx:]
            except: all_metrics = [c for c in all_cols if any(x in c for x in ["速度", "角度", "時間"])]
            valid_comp_metrics = [c for c in all_metrics if pd.to_numeric(db_df[c], errors='coerce').dropna().any() and any(ord(char) > 255 for char in c)]
            c1, c2 = st.columns(2)
            with c1: comp_metric = st.selectbox("比較指標", valid_comp_metrics, key="m_tab2")
            with c2: 
                all_conds_c = sorted([str(x) for x in db_df['スイング条件'].fillna("未設定").astype(str).str.strip().unique().tolist()])
                sel_conds_c = st.multiselect("打撃条件", all_conds_c, default=all_conds_c, key="cond_tab2")
            fdf = db_df[db_df['スイング条件'].fillna("未設定").astype(str).str.strip().isin(sel_conds_c)].copy()
            if not fdf.empty and comp_metric:
                fdf[comp_metric] = pd.to_numeric(fdf[comp_metric], errors='coerce')
                fdf['StrikeZoneY'] = pd.to_numeric(fdf['StrikeZoneY'], errors='coerce')
                is_time = "スイング時間" in comp_metric
                is_upper = "アッパースイング度" in comp_metric
                
                if is_upper:
                    def check_success(row):
                        val, y = row[comp_metric], row['StrikeZoneY']
                        if pd.isna(val) or pd.isna(y): return None
                        if y > SZ_Y_TH2: return 3.0 <= val <= 10.0
                        elif y > SZ_Y_TH1: return 8.0 <= val <= 15.0
                        else: return 10.0 <= val <= 20.0
                    fdf['is_success'] = fdf.apply(check_success, axis=1)
                    top3_series = fdf.groupby('Player Name')['is_success'].mean().sort_values(ascending=False).head(3)
                    top3_scores = [f"{s*100:.1f}%" for s in top3_series.values]
                else:
                    top3_series = fdf.groupby('Player Name')[comp_metric].mean().sort_values(ascending=is_time).head(3)
                    top3_scores = [f"{s:.3f}" if is_time else f"{s:.1f}" for s in top3_series.values]
                
                st.subheader(f"🥇 {'成功率' if is_upper else '平均'} トップ3")
                t_cols = st.columns(3)
                podium = [1, 0, 2] if len(top3_series) >= 3 else list(range(len(top3_series)))
                for i, idx in enumerate(podium):
                    if idx < len(top3_series):
                        name, score = top3_series.index[idx], top3_scores[idx]
                        with t_cols[i]:
                            st.markdown(f"<div style='text-align: center; background-color: #333; padding: 5px; border-radius: 5px;'><span style='font-size: 1.1rem; font-weight: bold; color: white;'>{idx+1}位: {name}</span><br><span style='font-size: 0.9rem; color: #ddd;'>{score}</span></div>", unsafe_allow_html=True)
                            grid = get_3x3_grid(fdf[fdf['Player Name'] == name], comp_metric)
                            fig = go.Figure()
                            for r_idx in range(3):
                                for c_idx in range(3):
                                    v = grid[r_idx, c_idx]; color, f_color = get_color(v, comp_metric, row_idx=r_idx)
                                    fig.add_shape(type="rect", x0=c_idx-0.5, x1=c_idx+0.5, y0=2.5-r_idx, y1=1.5-r_idx, fillcolor=color, line=dict(color="#222", width=2))
                                    if v > 0: fig.add_annotation(x=c_idx, y=2-r_idx, text=f"{v:.3f}" if is_time else f"{v:.1f}", showarrow=False, font=dict(color=f_color, weight="bold", size=14))
                            fig.update_layout(height=300, margin=dict(l=5, r=5, t=5, b=5), xaxis=dict(visible=False), yaxis=dict(visible=False))
                            st.plotly_chart(fig, use_container_width=True, key=f"top3_{idx}")

                st.markdown("---")
                st.subheader("🆚 2名ピックアップ比較")
                ca, cb = st.columns(2)
                with ca: player_a = st.selectbox("選手A", PLAYERS, key="compare_a")
                with cb: player_b = st.selectbox("選手B", PLAYERS, key="compare_b")
                if player_a and player_b:
                    limit = 0.010 if is_time else 5.0
                    g_a, g_b = get_3x3_grid(fdf[fdf['Player Name'] == player_a], comp_metric), get_3x3_grid(fdf[fdf['Player Name'] == player_b], comp_metric)
                    p_cols = st.columns(2)
                    for idx, (name, mine, yours) in enumerate([(player_a, g_a, g_b), (player_b, g_b, g_a)]):
                        with p_cols[idx]:
                            st.write(f"**{name}**")
                            fig_pair = go.Figure()
                            for r_idx in range(3):
                                for c_idx in range(3):
                                    v, ov = mine[r_idx, c_idx], yours[r_idx, c_idx]
                                    diff = abs(v - ov) if (v > 0 and ov > 0) else 0
                                    lw, lc = (5, "yellow") if diff >= limit else (1, "gray")
                                    if is_time: font_c = "red" if (v < ov and v > 0 and ov > 0) else "blue" if (v > ov and v > 0 and ov > 0) else "black"
                                    else: font_c = "red" if (v > ov and v > 0 and ov > 0) else "blue" if (v < ov and v > 0 and ov > 0) else "black"
                                    fig_pair.add_shape(type="rect", x0=c_idx-0.5, x1=c_idx+0.5, y0=2.5-r_idx, y1=1.5-r_idx, fillcolor="white", line=dict(color=lc, width=lw))
                                    if v > 0: fig_pair.add_annotation(x=c_idx, y=2-r_idx, text=f"{v:.3f}" if is_time else f"{v:.1f}", showarrow=False, font=dict(color=font_c, weight="bold", size=16))
                            fig_pair.update_layout(height=400, xaxis=dict(tickvals=[0,1,2], ticktext=['左','中','右'], side="top"), yaxis=dict(tickvals=[0,1,2], ticktext=['高','中','低']))
                            st.plotly_chart(fig_pair, use_container_width=True, key=f"pair_{idx}")

    with tab3:
        st.title("📝 データ登録")
        c1, c2 = st.columns(2)
        with c1: reg_player = st.selectbox("選手", PLAYERS, key="reg_p")
        with c2: reg_date = st.date_input("日付", value=datetime.date.today(), key="reg_d")
        uploaded_file = st.file_uploader("Excelアップロード", type=["xlsx"])
        if uploaded_file and st.button("GitHubへ追加保存"):
            try:
                input_df = pd.read_excel(uploaded_file)
                time_col = input_df.columns[0]
                input_df = input_df.rename(columns={time_col: 'time_col'})
                input_df['DateTime'] = reg_date.strftime('%Y-%m-%d') + ' ' + input_df['time_col'].astype(str)
                input_df['Player Name'] = reg_player
                if 'スイング条件' not in input_df.columns: input_df['スイング条件'] = "未設定"
                latest_db = load_data_from_github()
                updated_db = pd.concat([latest_db, input_df], ignore_index=True) if not latest_db.empty else input_df
                success, msg = save_to_github(updated_db)
                if success: st.success("✅ 保存完了！"); st.balloons()
                else: st.error(f"❌ 保存失敗: {msg}")
            except Exception as e: st.error(f"❌ エラー: {e}")
