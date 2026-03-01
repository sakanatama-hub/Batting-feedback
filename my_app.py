import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import requests
import base64
import re

# --- 基本設定 ---
PW = "1189" 
GITHUB_USER = "sakanatama-hub"
GITHUB_REPO = "Batting-feedback"
GITHUB_FILE_PATH = "data.csv"         # 練習用
GITHUB_GAME_FILE_PATH = "game_data.csv" # 試合用
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- ストライクゾーン定義 (cm) ---
SZ_X_MIN, SZ_X_MAX = -28.8, 28.8
SZ_X_TH1, SZ_X_TH2 = -9.6, 9.6
SZ_Y_MIN, SZ_Y_MAX = 45.0, 110.0
SZ_Y_TH1, SZ_Y_TH2 = 66.6, 88.3

PLAYER_HANDS = {"#1 熊田 任洋": "左", "#2 逢澤 崚介": "左", "#3 三塚 武蔵": "左", "#4 北村 祥治": "右", "#5 前田 健伸": "左", "#6 佐藤 勇基": "右", "#7 西村 友哉": "右", "#8 和田 佳大": "左", "#9 今泉 颯太": "右", "#10 福井 章吾": "左", "#22 高祖 健輔": "左", "#23 箱山 遥人": "右", "#24 坂巻 尚哉": "右", "#26 西村 彰浩": "左", "#27 小畑 尋規": "右", "#28 宮崎 仁斗": "右", "#29 徳本 健太朗": "左", "#39 柳 元珍": "左", "#99 尾瀬 雄大": "左"}
PLAYERS = list(PLAYER_HANDS.keys())

# --- 共通関数 ---
def convert_course_to_coord(course_str):
    if pd.isna(course_str): return None, None
    course_str = str(course_str)
    x = 0
    if "内" in course_str: x = -19.2
    elif "外" in course_str: x = 19.2
    y = 77.5
    if "高め" in course_str: y = 99.1
    elif "低め" in course_str: y = 55.8
    return x, y

def load_data_from_github(file_path):
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{file_path}?nocache={datetime.datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url, dtype=str)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

def save_to_github(new_df, file_path):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    save_df = new_df.copy()
    for col in save_df.columns:
        save_df[col] = save_df[col].astype(str).replace('nan', '').replace('NaT', '')
    csv_content = save_df.to_csv(index=False)
    b64_content = base64.b64encode(csv_content.encode('utf-8-sig')).decode()
    data = {"message": f"Update {file_path}", "content": b64_content}
    if sha: data["sha"] = sha
    put_res = requests.put(url, headers=headers, json=data)
    return (True, "成功") if put_res.status_code in [200, 201] else (False, f"エラー {put_res.status_code}")

def sort_players_by_number(player_list):
    def extract_num(s):
        match = re.search(r'#(\d+)', s)
        return int(match.group(1)) if match else 999
    return sorted(player_list, key=extract_num)

# --- 判定・色分けロジック ---
def get_color(val, metric_name, row_idx=None, eff_val=None):
    if val == 0 or pd.isna(val): return "rgba(255, 255, 255, 0.1)", "white"
    white_metrics = ["バット角度", "バットの角度", "打球方向", "飛距離"]
    if any(m in metric_name for m in white_metrics): return "#FFFFFF", "black"
    if "打球角度" in metric_name:
        center = 15.0
        if 8.0 <= val <= 22.0:
            dist = abs(val - center); intensity = 1.0 - (dist / 7.0); gb_val = int(255 * (1 - intensity))
            return f"rgba(255, {gb_val}, {gb_val}, 0.9)", "white" if intensity > 0.5 else "black"
        elif val < 8.0:
            dist = min(abs(8.0 - val), 15.0); intensity = dist / 15.0; rb_val = int(255 * (1 - intensity))
            return f"rgba({rb_val}, 255, {rb_val}, 0.9)", "black"
        else:
            dist = min(abs(val - 22.0), 15.0); intensity = dist / 15.0; rg_val = int(255 * (1 - intensity))
            return f"rgba({rg_val}, {rg_val}, 255, 0.9)", "white" if intensity > 0.5 else "black"
    if "打球速度" in metric_name:
        if val < 140: return "rgba(0, 0, 255, 0.9)", "white"
        elif 140 <= val < 145: return "rgba(173, 216, 230, 0.9)", "black"
        elif 145 <= val <= 152: return "rgba(255, 255, 255, 0.9)", "black"
        elif 153 <= val <= 160: return "rgba(255, 182, 193, 0.9)", "black"
        else: return "rgba(255, 0, 0, 0.9)", "white"
    if "手の最大スピード" in metric_name:
        eff = eff_val if eff_val is not None else val
        if eff < 2.7: return "rgba(0, 128, 0, 0.9)", "white"
        elif eff < 3.0: return "rgba(144, 238, 144, 0.9)", "black"
        elif 3.0 <= eff <= 3.2:
            dist = abs(eff - 3.1); intensity = 1.0 - (dist / 0.1) if dist <= 0.1 else 0.0; gb_val = int(255 * (1 - intensity))
            return f"rgba(255, {gb_val}, {gb_val}, 0.9)", "white" if intensity > 0.5 else "black"
        elif eff <= 3.4: return "rgba(173, 216, 230, 0.9)", "black"
        else: return "rgba(0, 0, 255, 0.9)", "white"
    if "パワー" in metric_name:
        if val < 3: return "rgba(0, 0, 255, 0.9)", "white"
        elif val <= 3.5: return "rgba(173, 216, 230, 0.9)", "black"
        elif val <= 4: return "rgba(255, 255, 255, 0.9)", "black"
        elif val <= 4.5: return "rgba(255, 182, 193, 0.9)", "black"
        else: return "rgba(255, 0, 0, 0.9)", "white"
    if "アッパースイング度" in metric_name and row_idx is not None:
        if row_idx == 0: base, low, high = 6.5, 3.0, 10.0
        elif row_idx == 1: base, low, high = 11.5, 8.0, 15.0
        else: base, low, high = 15.0, 10.0, 20.0
        if low <= val <= high:
            intensity = 1.0 - (abs(val - base) / ((high - low) / 2))
            return f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)", "black"
        elif val < low:
            intensity = min((low - val) / 15.0, 1.0); return f"rgba({int(255*(1-intensity))}, 255, {int(255*(1-intensity))}, 0.9)", "black"
        else:
            intensity = min((val - high) / 15.0, 1.0); return f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)", "black"
    if "バットスピード" in metric_name:
        if val < 100: return "rgba(0, 0, 255, 0.9)", "white"
        elif 100 <= val <= 110: return "rgba(255, 255, 255, 0.9)", "black"
        elif 110 < val < 120:
            intensity = (val - 110) / 10; gb_val = int(255 * (1 - intensity))
            return f"rgba(255, {gb_val}, {gb_val}, 0.9)", "black" if intensity < 0.6 else "white"
        else: return "rgba(255, 0, 0, 0.9)", "white"
    if "スイング時間" in metric_name:
        if val < 0.14: return "rgba(255, 0, 0, 0.9)", "white"
        elif 0.14 <= val < 0.15: return "rgba(255, 180, 180, 0.9)", "black"
        elif 0.15 <= val < 0.16: return "rgba(255, 255, 255, 0.9)", "black"
        elif 0.16 <= val < 0.17: return "rgba(180, 180, 255, 0.9)", "black"
        else: return "rgba(0, 0, 255, 0.9)", "white"
    base, sensitivity = 105, 30; diff = val - base; intensity = min(abs(diff) / sensitivity, 1.0)
    color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff > 0 else f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
    f_color = "black" if intensity < 0.4 else "white"
    return color, f_color

def get_3x3_grid(df, metric):
    grid = np.zeros((3, 3)); counts = np.zeros((3, 3)); eff_grid = np.zeros((3, 3))
    if metric not in df.columns: return grid, None
    df_c = df.copy()
    df_c['StrikeZoneX'] = pd.to_numeric(df_c['StrikeZoneX'], errors='coerce')
    df_c['StrikeZoneY'] = pd.to_numeric(df_c['StrikeZoneY'], errors='coerce')
    is_hand = "手の最大スピード" in metric and "バットスピード (km/h)" in df_c.columns
    df_c[metric] = pd.to_numeric(df_c[metric], errors='coerce')
    if is_hand: df_c['eff_calc'] = pd.to_numeric(df_c['バットスピード (km/h)'], errors='coerce') / df_c[metric]
    valid = df_c.dropna(subset=['StrikeZoneX', 'StrikeZoneY', metric])
    for _, row in valid.iterrows():
        c = 0 if row['StrikeZoneX'] < SZ_X_TH1 else 1 if row['StrikeZoneX'] <= SZ_X_TH2 else 2
        r = 0 if row['StrikeZoneY'] > SZ_Y_TH2 else 1 if row['StrikeZoneY'] > SZ_Y_TH1 else 2
        grid[r, c] += row[metric]; counts[r, c] += 1
        if is_hand: eff_grid[r, c] += row['eff_calc']
    return np.where(counts > 0, grid / counts, 0), (np.where(counts > 0, eff_grid / counts, 0) if is_hand else None)

# --- メインアプリ ---
st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
if "ok" not in st.session_state: st.session_state["ok"] = False

if not st.session_state["ok"]:
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("PASSWORD", type="password")
    if st.button("LOGIN"):
        if val == PW: st.session_state["ok"] = True; st.rerun()
else:
    db_df = load_data_from_github(GITHUB_FILE_PATH)
    tab1, tab2, tab3, tab4 = st.tabs(["👤 個人分析", "⚔️ 比較分析", "📝 データ登録", "🏟️ 試合分析"])

    # --- Tab 1: 個人分析 (完全復元版) ---
    with tab1:
        st.title("🔵 個人別打撃分析")
        if not db_df.empty:
            player_col = 'Player Name'; cond_col = 'スイング条件'
            db_df[cond_col] = db_df[cond_col].fillna("未設定").astype(str).str.strip()
            existing_players = sort_players_by_number(db_df[player_col].dropna().unique().tolist())
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            with c1: target_player = st.selectbox("選手を選択", existing_players, key="p_tab1")
            pdf = db_df[db_df[player_col] == target_player].copy()
            if not pdf.empty:
                pdf['Date_Only_Str'] = pdf['DateTime'].astype(str).str.extract(r'(\d{4}-\d{2}-\d{2})')[0]
                pdf['Date_Only'] = pd.to_datetime(pdf['Date_Only_Str'], errors='coerce').dt.date
                with c2: date_range = st.date_input("分析期間", value=(min(pdf['Date_Only']), max(pdf['Date_Only'])), key="range_tab1")
                with c3: sel_conds = st.multiselect("打撃条件", sorted(db_df[cond_col].unique()), default=sorted(db_df[cond_col].unique()), key="cond_tab1")
                with c4:
                    keywords = ["スコア", "速度", "角度", "効率", "パワー", "時間", "スピード", "飛距離", "G)", "度"]
                    valid_metrics = [c for c in pdf.columns if any(k in str(c) for k in keywords)]
                    target_metric = st.selectbox("分析指標", valid_metrics, key="m_tab1")
                
                mask = (pdf[cond_col].isin(sel_conds))
                if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                    mask &= (pdf['Date_Only'] >= date_range[0]) & (pdf['Date_Only'] <= date_range[1])
                vdf = pdf[mask].copy()
                if not vdf.empty:
                    if "手の最大スピード" in target_metric and "バットスピード (km/h)" in vdf.columns:
                        vdf[target_metric] = pd.to_numeric(vdf['バットスピード (km/h)'], errors='coerce') / pd.to_numeric(vdf[target_metric], errors='coerce')
                    else: vdf[target_metric] = pd.to_numeric(vdf[target_metric], errors='coerce')
                    vdf['StrikeZoneX'] = pd.to_numeric(vdf['StrikeZoneX'], errors='coerce'); vdf['StrikeZoneY'] = pd.to_numeric(vdf['StrikeZoneY'], errors='coerce')
                    
                    st.subheader(f"📊 {target_metric}：ゾーン別平均 (5x5)")
                    fig_heat = go.Figure()
                    fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
                    grid_side = 55; z_x_start, z_y_start = -(grid_side * 2.5), 180; grid_val = np.zeros((5, 5)); grid_count = np.zeros((5, 5))
                    for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                        r = 0 if row['StrikeZoneY'] > SZ_Y_MAX else 1 if row['StrikeZoneY'] > SZ_Y_TH2 else 2 if row['StrikeZoneY'] > SZ_Y_TH1 else 3 if row['StrikeZoneY'] > SZ_Y_MIN else 4
                        c = 0 if row['StrikeZoneX'] < SZ_X_MIN else 1 if row['StrikeZoneX'] < SZ_X_TH1 else 2 if row['StrikeZoneX'] <= SZ_X_TH2 else 3 if row['StrikeZoneX'] <= SZ_X_MAX else 4
                        grid_val[r, c] += row[target_metric]; grid_count[r, c] += 1
                    display_grid = np.where(grid_count > 0, grid_val / grid_count, 0)
                    for r in range(5):
                        for c in range(5):
                            x0, x1 = z_x_start + c * grid_side, z_x_start + (c + 1) * grid_side; y0, y1 = z_y_start + (4 - r) * grid_side, z_y_start + (5 - r) * grid_side
                            val_h = display_grid[r, c]; color, f_color = get_color(val_h, target_metric, row_idx=max(0, min(2, r - 1)))
                            fig_heat.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color, line=dict(color="#222", width=1))
                            if val_h > 0: fig_heat.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=f"{val_h:.1f}", showarrow=False, font=dict(color=f_color, weight="bold"))
                    fig_heat.update_layout(width=800, height=600, xaxis=dict(visible=False, range=[-320, 320]), yaxis=dict(visible=False, range=[-50, 520]))
                    st.plotly_chart(fig_heat)

                    st.subheader("🎯 インパクト位置（ミートポイント）")
                    fig_imp = go.Figure()
                    fig_imp.add_shape(type="rect", x0=SZ_X_MIN, x1=SZ_X_MAX, y0=SZ_Y_MIN, y1=SZ_Y_MAX, line=dict(color="white", width=2))
                    fig_imp.add_shape(type="line", x0=SZ_X_TH1, x1=SZ_X_TH1, y0=SZ_Y_MIN, y1=SZ_Y_MAX, line=dict(color="gray", width=1, dash="dash"))
                    fig_imp.add_shape(type="line", x0=SZ_X_TH2, x1=SZ_X_TH2, y0=SZ_Y_MIN, y1=SZ_Y_MAX, line=dict(color="gray", width=1, dash="dash"))
                    fig_imp.add_shape(type="line", x0=SZ_X_MIN, x1=SZ_X_MAX, y0=SZ_Y_TH1, y1=SZ_Y_TH1, line=dict(color="gray", width=1, dash="dash"))
                    fig_imp.add_shape(type="line", x0=SZ_X_MIN, x1=SZ_X_MAX, y0=SZ_Y_TH2, y1=SZ_Y_TH2, line=dict(color="gray", width=1, dash="dash"))
                    vdf['Hand'] = vdf['Player Name'].map(PLAYER_HANDS).fillna("右")
                    colors = vdf['Hand'].map({"右": "red", "左": "blue"})
                    fig_imp.add_trace(go.Scatter(x=vdf['StrikeZoneX'], y=vdf['StrikeZoneY'], mode='markers', marker=dict(color=colors, size=10, opacity=0.7), text=vdf['DateTime']))
                    fig_imp.update_layout(width=500, height=600, xaxis=dict(range=[-50, 50], title="横 (cm)"), yaxis=dict(range=[30, 130], title="高さ (cm)"), plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_imp)

    # --- Tab 2: 比較分析 (完全復元版) ---
    with tab2:
        st.title("⚔️ 選手間比較分析")
        if not db_df.empty:
            all_metrics = [c for c in db_df.columns if any(k in str(c) for k in keywords)]
            c1, c2 = st.columns(2)
            with c1: comp_metric = st.selectbox("比較指標", all_metrics, key="m_tab2")
            with c2: sel_conds_c = st.multiselect("打撃条件", sorted(db_df[cond_col].unique()), default=sorted(db_df[cond_col].unique()), key="cond_tab2")
            fdf = db_df[db_df[cond_col].isin(sel_conds_c)].copy()
            if not fdf.empty:
                fdf[comp_metric] = pd.to_numeric(fdf[comp_metric], errors='coerce')
                st.subheader(f"🥇 {comp_metric} 平均値ランキング")
                is_time = "時間" in comp_metric
                ranking = fdf.groupby('Player Name')[comp_metric].mean().sort_values(ascending=is_time)
                st.dataframe(ranking.to_frame(name="平均値").style.background_gradient(cmap='Reds' if not is_time else 'Reds_r'))

                st.subheader(f"🚀 {comp_metric} トップ3の詳細（ゾーン別）")
                top3_names = ranking.head(3).index.tolist()
                t_cols = st.columns(3)
                for i, name in enumerate(top3_names):
                    with t_cols[i]:
                        st.write(f"**{i+1}位: {name}**")
                        grid, _ = get_3x3_grid(fdf[fdf['Player Name'] == name], comp_metric)
                        fig = go.Figure()
                        for r in range(3):
                            for c in range(3):
                                v = grid[r, c]; color, fc = get_color(v, comp_metric, row_idx=r)
                                fig.add_shape(type="rect", x0=c, x1=c+1, y0=2-r, y1=3-r, fillcolor=color, line=dict(color="white"))
                                if v > 0: fig.add_annotation(x=c+0.5, y=2.5-r, text=f"{v:.1f}", showarrow=False, font=dict(color=fc, size=14))
                        fig.update_layout(width=250, height=250, xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=5,r=5,t=5,b=5))
                        st.plotly_chart(fig, key=f"comp_top_{i}")

    # --- Tab 3: 最新データ登録 (練習/試合分離 & コース座標変換) ---
    with tab3:
        st.title("📝 データ登録")
        sub_tab_practice, sub_tab_game = st.tabs(["🏋️ 練習データ登録", "🏟️ 試合データ登録"])
        reg_players_sorted = sort_players_by_number(PLAYERS)
        cmap = {'ExitVelocity': '打球速度', 'PitchBallVelocity': '投球速度', 'LaunchAngle': '打球角度', 'ExitDirection': '打球方向', 'Spin': '回転数', 'Distance': '飛距離', 'SpinDirection': '回転方向'}

        with sub_tab_practice:
            c1, c2 = st.columns(2)
            with c1: p_reg_player = st.selectbox("登録選手", reg_players_sorted, key="reg_p_p")
            with c2: p_reg_date = st.date_input("打撃日", value=datetime.date.today(), key="reg_d_p")
            p_file = st.file_uploader("練習のExcelをアップロード", type=["xlsx"], key="f_p")
            if p_file and st.button("練習データをGitHubへ保存", key="btn_p"):
                with st.spinner('保存中...'):
                    df = pd.read_excel(p_file)
                    df['試合区別'] = "練習"; df['Player Name'] = p_reg_player
                    df = df.rename(columns={df.columns[0]: 'time_col', **cmap})
                    df['DateTime'] = p_reg_date.strftime('%Y-%m-%d') + ' ' + df['time_col'].astype(str)
                    if 'スイング条件' not in df.columns: df['スイング条件'] = "未設定"
                    old = load_data_from_github(GITHUB_FILE_PATH)
                    success, msg = save_to_github(pd.concat([old, df], ignore_index=True), GITHUB_FILE_PATH)
                    if success: st.success("✅ 練習データを保存しました！"); st.balloons()

        with sub_tab_game:
            c1, c2, c3 = st.columns(3)
            with c1: g_reg_player = st.selectbox("登録選手", reg_players_sorted, key="reg_p_g")
            with c2: g_reg_date = st.date_input("打撃日", value=datetime.date.today(), key="reg_d_g")
            with c3: g_cat = st.selectbox("試合区分", ["オープン戦", "紅白戦", "JAVA大会", "二大大会", "二大大会予選", "その他"], key="reg_cat_g")
            g_file = st.file_uploader("試合のExcelをアップロード", type=["xlsx"], key="f_g")
            if g_file and st.button("試合データをGitHubへ保存", key="btn_g"):
                with st.spinner('保存中...'):
                    df = pd.read_excel(g_file)
                    df['試合区別'] = g_cat; df['Player Name'] = g_reg_player
                    if 'コース' in df.columns:
                        coords = df['コース'].apply(convert_course_to_coord)
                        df['StrikeZoneX'] = [c[0] for c in coords]; df['StrikeZoneY'] = [c[1] for c in coords]
                    df = df.rename(columns={df.columns[0]: 'time_col', **cmap})
                    df['DateTime'] = g_reg_date.strftime('%Y-%m-%d') + ' ' + df['time_col'].astype(str)
                    if 'スイング条件' not in df.columns: df['スイング条件'] = "未設定"
                    old = load_data_from_github(GITHUB_GAME_FILE_PATH)
                    success, msg = save_to_github(pd.concat([old, df], ignore_index=True), GITHUB_GAME_FILE_PATH)
                    if success: st.success(f"✅ [{g_cat}] データを保存しました！"); st.balloons()

    # --- Tab 4: 試合分析 ---
    with tab4:
        st.title("🏟️ 試合分析")
        game_db = load_data_from_github(GITHUB_GAME_FILE_PATH)
        if not game_db.empty:
            st.write(f"📈 登録済み試合データ ({len(game_db)}件)")
            st.dataframe(game_db.sort_values('DateTime', ascending=False).head(20))
        else:
            st.info("試合データがまだ登録されていません。")
