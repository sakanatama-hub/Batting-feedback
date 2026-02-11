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

# --- 共通ユーティリティ (色定義) ---
def get_color(val, metric_name, row_idx=None, eff_val=None):
    if val == 0 or pd.isna(val):
        return "rgba(255, 255, 255, 0.1)", "white"
    
    # 手の最大スピードのみ、判定にeff_val(効率)を使用。それ以外はvalを使用。
    if "手の最大スピード" in metric_name:
        eff = eff_val if eff_val is not None else val
        if eff < 2.7: return "rgba(0, 128, 0, 0.9)", "white"
        elif eff < 3.0: return "rgba(144, 238, 144, 0.9)", "black"
        elif 3.0 <= eff <= 3.2:
            dist = abs(eff - 3.1)
            intensity = 1.0 - (dist / 0.1) if dist <= 0.1 else 0.0
            gb = int(255 * (1 - intensity))
            return f"rgba(255, {gb}, {gb}, 0.9)", "white" if intensity > 0.5 else "black"
        elif eff <= 3.4: return "rgba(173, 216, 230, 0.9)", "black"
        else: return "rgba(0, 0, 255, 0.9)", "white"

    if "パワー" in metric_name:
        if val < 3: return "rgba(0, 0, 255, 0.9)", "white"
        elif val <= 3.5: return "rgba(173, 216, 230, 0.9)", "black"
        elif val <= 4: return "rgba(255, 255, 255, 0.9)", "black"
        elif val <= 4.5: return "rgba(255, 182, 193, 0.9)", "black"
        else: return "rgba(255, 0, 0, 0.9)", "white"

    if "体の回転によるバットの加速の大きさ" in metric_name:
        if val <= 5: return "rgba(0, 0, 255, 0.9)", "white"
        elif val <= 10: return "rgba(173, 216, 230, 0.9)", "black"
        elif val <= 14: return "rgba(255, 255, 255, 0.9)", "black"
        elif val <= 20: return "rgba(255, 182, 193, 0.9)", "black"
        else: return "rgba(255, 0, 0, 0.9)", "white"

    if "体とバットの角度" in metric_name:
        if 85 <= val <= 95:
            intensity = 1.0 - (abs(val-90)/5.0)
            gb = int(255*(1-intensity))
            return f"rgba(255, {gb}, {gb}, 0.9)", "white" if intensity > 0.5 else "black"
        elif val < 85: return "rgba(200, 255, 200, 0.9)", "black"
        else: return "rgba(200, 200, 255, 0.9)", "black"

    if "アッパースイング度" in metric_name and row_idx is not None:
        if row_idx == 0: base, low, high = 6.5, 3.0, 10.0
        elif row_idx == 1: base, low, high = 11.5, 8.0, 15.0
        else: base, low, high = 15.0, 10.0, 20.0
        if low <= val <= high:
            intensity = 1.0 - (abs(val-base)/((high-low)/2))
            return f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)", "black"
        elif val < low: return "rgba(200, 255, 200, 0.9)", "black"
        else: return "rgba(200, 200, 255, 0.9)", "black"

    if "バットスピード" in metric_name:
        if val < 100: return "rgba(0, 0, 255, 0.9)", "white"
        elif val <= 110: return "rgba(255, 255, 255, 0.9)", "black"
        elif val < 120: return "rgba(255, 180, 180, 0.9)", "black"
        else: return "rgba(255, 0, 0, 0.9)", "white"

    if "スイング時間" in metric_name:
        if val < 0.14: return "rgba(255, 0, 0, 0.9)", "white"
        elif val < 0.15: return "rgba(255, 180, 180, 0.9)", "black"
        elif val < 0.16: return "rgba(255, 255, 255, 0.9)", "black"
        elif val < 0.17: return "rgba(180, 180, 255, 0.9)", "black"
        else: return "rgba(0, 0, 255, 0.9)", "white"

    return "rgba(200, 200, 255, 0.9)", "black"

def get_3x3_grid(df, metric):
    grid = np.zeros((3, 3)); counts = np.zeros((3, 3)); eff_grid = np.zeros((3, 3))
    if metric not in df.columns: return grid, None
    df_c = df.copy()
    df_c['StrikeZoneX'] = pd.to_numeric(df_c['StrikeZoneX'], errors='coerce')
    df_c['StrikeZoneY'] = pd.to_numeric(df_c['StrikeZoneY'], errors='coerce')
    
    is_hand = "手の最大スピード" in metric and "バットスピード (km/h)" in df_c.columns
    df_c[metric] = pd.to_numeric(df_c[metric], errors='coerce')
    if is_hand:
        df_c['eff_calc'] = pd.to_numeric(df_c["バットスピード (km/h)"], errors='coerce') / df_c[metric]

    valid = df_c.dropna(subset=['StrikeZoneX', 'StrikeZoneY', metric])
    for _, row in valid.iterrows():
        c = 0 if row['StrikeZoneX'] < SZ_X_TH1 else 1 if row['StrikeZoneX'] <= SZ_X_TH2 else 2
        r = 0 if row['StrikeZoneY'] > SZ_Y_TH2 else 1 if row['StrikeZoneY'] > SZ_Y_TH1 else 2
        grid[r, c] += row[metric]
        counts[r, c] += 1
        if is_hand: eff_grid[r, c] += row['eff_calc']
    
    final_v = np.where(counts > 0, grid / counts, 0)
    final_e = np.where(counts > 0, eff_grid / counts, 0) if is_hand else None
    return final_v, final_e

st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
if "ok" not in st.session_state: st.session_state["ok"] = False

if not st.session_state["ok"]:
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("PASSWORD", type="password")
    if st.button("LOGIN"):
        if val == PW:
            st.session_state["ok"] = True; st.rerun()
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
                pdf['Date_Only'] = pd.to_datetime(pdf['DateTime'].str[:10], errors='coerce').dt.date
                valid_dates = pdf['Date_Only'].dropna()
                min_date = min(valid_dates) if not valid_dates.empty else datetime.date(2024,1,1)
                max_date = max(valid_dates) if not valid_dates.empty else datetime.date.today()
                with c2: date_range = st.date_input("分析期間", value=(min_date, max_date), key="range_tab1")
                with c3: sel_conds = st.multiselect("打撃条件 (U列)", all_possible_conds, default=all_possible_conds, key="cond_tab1")
                with c4:
                    all_cols = pdf.columns.tolist()
                    try: v_idx = pdf.columns.get_loc("オンプレーンスコア"); candidates = all_cols[v_idx:]
                    except: candidates = [c for c in all_cols if any(x in c for x in ["速度", "角度", "時間"])]
                    valid_metrics = [c for c in candidates if any(ord(char) > 255 for char in c)]
                    priority = ["バットスピード (km/h)", "スイング時間 (秒)", "アッパースイング度 (°)"]
                    sorted_metrics = [m for m in priority if m in valid_metrics] + [m for m in valid_metrics if m not in priority]
                    target_metric = st.selectbox("分析指標", sorted_metrics, key="m_tab1")

                mask = (pdf['スイング条件_str'].isin(sel_conds))
                if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                    mask &= (pdf['Date_Only'] >= date_range[0]) & (pdf['Date_Only'] <= date_range[1])
                vdf = pdf[mask].copy()

                if not vdf.empty:
                    vdf[target_metric] = pd.to_numeric(vdf[target_metric], errors='coerce')
                    is_hand_metric = "手の最大スピード" in target_metric and "バットスピード (km/h)" in vdf.columns
                    if is_hand_metric:
                        vdf['eff_calc'] = pd.to_numeric(vdf['バットスピード (km/h)'], errors='coerce') / vdf[target_metric]
                    
                    m_avg = vdf[target_metric].mean()
                    st.metric(label="期間内 平均", value=f"{m_avg:.3f}" if "時間" in target_metric else f"{m_avg:.1f}")

                    st.subheader(f"📊 {target_metric}：ゾーン別平均")
                    vdf['StrikeZoneX'] = pd.to_numeric(vdf['StrikeZoneX'], errors='coerce')
                    vdf['StrikeZoneY'] = pd.to_numeric(vdf['StrikeZoneY'], errors='coerce')
                    fig_heat = go.Figure()
                    fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", layer="below")
                    grid_side = 55; z_x_start, z_y_start = -(grid_side * 2.5), 180
                    
                    grid_val = np.zeros((5, 5)); grid_count = np.zeros((5, 5)); grid_eff = np.zeros((5, 5))
                    for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                        r = 0 if row['StrikeZoneY'] > SZ_Y_MAX else 1 if row['StrikeZoneY'] > SZ_Y_TH2 else 2 if row['StrikeZoneY'] > SZ_Y_TH1 else 3 if row['StrikeZoneY'] > SZ_Y_MIN else 4
                        c = 0 if row['StrikeZoneX'] < SZ_X_MIN else 1 if row['StrikeZoneX'] < SZ_X_TH1 else 2 if row['StrikeZoneX'] <= SZ_X_TH2 else 3 if row['StrikeZoneX'] <= SZ_X_MAX else 4
                        grid_val[r, c] += row[target_metric]; grid_count[r, c] += 1
                        if is_hand_metric: grid_eff[r, c] += row['eff_calc']
                    
                    for r in range(5):
                        for c in range(5):
                            if grid_count[r, c] > 0:
                                v_h = grid_val[r, c]/grid_count[r, c]; e_h = grid_eff[r, c]/grid_count[r, c] if is_hand_metric else None
                                color, f_c = get_color(v_h, target_metric, row_idx=max(0,min(2,r-1)), eff_val=e_h)
                                fig_heat.add_shape(type="rect", x0=z_x_start+c*grid_side, x1=z_x_start+(c+1)*grid_side, y0=z_y_start+(4-r)*grid_side, y1=z_y_start+(5-r)*grid_side, fillcolor=color)
                                txt = f"{v_h:.3f}" if "時間" in target_metric else f"{v_h:.1f}"
                                fig_heat.add_annotation(x=z_x_start+(c+0.5)*grid_side, y=z_y_start+(4.5-r)*grid_side, text=txt, showarrow=False, font=dict(color=f_c, weight="bold"))
                    fig_heat.update_layout(width=800, height=600, xaxis=dict(visible=False), yaxis=dict(visible=False))
                    st.plotly_chart(fig_heat, use_container_width=True)

    with tab2:
        st.title("⚔️ 選手間比較分析")
        if not db_df.empty:
            all_cols = db_df.columns.tolist()
            valid_comp_metrics = [c for c in all_cols if any(ord(char) > 255 for char in c)]
            c1, c2 = st.columns(2)
            with c1: comp_metric = st.selectbox("比較指標", valid_comp_metrics, key="m_tab2")
            with c2: 
                all_conds_c = sorted([str(x) for x in db_df['スイング条件'].fillna("未設定").unique()])
                sel_conds_c = st.multiselect("打撃条件", all_conds_c, default=all_conds_c, key="cond_tab2")
            
            fdf = db_df[db_df['スイング条件'].fillna("未設定").astype(str).isin(sel_conds_c)].copy()
            if not fdf.empty:
                st.subheader("🥇 指標別トップ3")
                fdf[comp_metric] = pd.to_numeric(fdf[comp_metric], errors='coerce')
                is_time = "時間" in comp_metric
                top3 = fdf.groupby('Player Name')[comp_metric].mean().sort_values(ascending=is_time).head(3)
                t_cols = st.columns(3)
                for i, (name, val) in enumerate(top3.items()):
                    with t_cols[i]:
                        st.markdown(f"**{i+1}位: {name}**")
                        st.write(f"{val:.3f}" if is_time else f"{val:.1f}")
                        grid, eff_grid = get_3x3_grid(fdf[fdf['Player Name'] == name], comp_metric)
                        fig = go.Figure()
                        for r_idx in range(3):
                            for c_idx in range(3):
                                v = grid[r_idx, c_idx]; e = eff_grid[r_idx, c_idx] if eff_grid is not None else None
                                color, f_c = get_color(v, comp_metric, row_idx=r_idx, eff_val=e)
                                fig.add_shape(type="rect", x0=c_idx, x1=c_idx+1, y0=2-r_idx, y1=3-r_idx, fillcolor=color)
                                if v > 0: fig.add_annotation(x=c_idx+0.5, y=2.5-r_idx, text=f"{v:.1f}", showarrow=False, font=dict(color=f_c))
                        fig.update_layout(width=250, height=250, xaxis=dict(visible=False), yaxis=dict(visible=False))
                        st.plotly_chart(fig, use_container_width=True, key=f"top3_{i}")

    with tab3:
        st.title("📝 データ登録")
        c1, c2 = st.columns(2)
        with c1: reg_player = st.selectbox("登録選手", PLAYERS, key="reg_p")
        with c2: reg_date = st.date_input("打撃日", value=datetime.date.today())
        uploaded_file = st.file_uploader("Excelアップロード", type=["xlsx"])
        if uploaded_file and st.button("GitHub保存"):
            try:
                in_df = pd.read_excel(uploaded_file)
                in_df['DateTime'] = reg_date.strftime('%Y-%m-%d') + ' ' + in_df.iloc[:,0].astype(str).str.strip()
                in_df['Player Name'] = reg_player
                old_db = load_data_from_github()
                updated_db = pd.concat([old_db, in_df], ignore_index=True) if not old_db.empty else in_df
                ok, msg = save_to_github(updated_db)
                if ok: st.success("✅ 保存完了！"); st.balloons()
                else: st.error(f"❌ 保存失敗: {message}")
            except Exception as e: st.error(f"❌ エラー: {e}")
