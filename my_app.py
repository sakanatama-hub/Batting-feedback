import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import requests
import base64
import re  # 背番号抽出用

# --- 基本設定 ---
PW = "1189" 
GITHUB_USER = "sakanatama-hub"
GITHUB_REPO = "Batting-feedback"
GITHUB_FILE_PATH = "data.csv"
GITHUB_GAME_FILE_PATH = "game_data.csv" # 追加：試合用パス
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- ストライクゾーン定義 (cm) ---
SZ_X_MIN, SZ_X_MAX = -28.8, 28.8
SZ_X_TH1, SZ_X_TH2 = -9.6, 9.6
SZ_Y_MIN, SZ_Y_MAX = 45.0, 110.0
SZ_Y_TH1, SZ_Y_TH2 = 66.6, 88.3

PLAYER_HANDS = {"#1 熊田 任洋": "左", "#2 逢澤 崚介": "左", "#3 三塚 武蔵": "左", "#4 北村 祥治": "右", "#5 前田 健伸": "左", "#6 佐藤 勇基": "右", "#7 西村 友哉": "右", "#8 和田 佳大": "左", "#9 今泉 颯太": "右", "#10 福井 章吾": "左", "#22 高祖 健輔": "左", "#23 箱山 遥人": "右", "#24 坂巻 尚哉": "右", "#26 西村 彰浩": "左", "#27 小畑 尋規": "右", "#28 宮崎 仁斗": "右", "#29 徳本 健太朗": "左", "#39 柳 元珍": "左", "#99 尾瀬 雄大": "左"}
PLAYERS = list(PLAYER_HANDS.keys())

# --- 追加：コース文字列を座標に変換する関数 ---
def convert_course_to_coord(course_str):
    if pd.isna(course_str):
        return None, None
    course_str = str(course_str)
    
    # 横位置(X)の判定
    x = 0
    if "内" in course_str:
        x = -19.2  # SZ_X_TH1より外側（インコース）
    elif "外" in course_str:
        x = 19.2   # SZ_X_TH2より外側（アウトコース）
    else:
        x = 0      # 真ん中
        
    # 高さ(Y)の判定
    y = 77.5   # 真ん中の高さ（デフォルト）
    if "高め" in course_str:
        y = 99.1  # SZ_Y_TH2より上
    elif "低め" in course_str:
        y = 55.8  # SZ_Y_TH1より下
        
    return x, y

# --- GitHub連携関数 (引数にpathを追加) ---
def load_data_from_github(path):
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{path}?nocache={datetime.datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url, dtype=str)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

def save_to_github(new_df, path):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}"
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
    
    white_metrics = ["バット角度", "バットの角度", "打球方向", "飛距離"]
    if any(m in metric_name for m in white_metrics):
        return "#FFFFFF", "black"

    if "打球角度" in metric_name:
        center = 15.0
        if 8.0 <= val <= 22.0:
            dist = abs(val - center)
            intensity = 1.0 - (dist / 7.0) 
            gb_val = int(255 * (1 - intensity))
            return f"rgba(255, {gb_val}, {gb_val}, 0.9)", "white" if intensity > 0.5 else "black"
        elif val < 8.0:
            dist = min(abs(8.0 - val), 15.0)
            intensity = dist / 15.0
            rb_val = int(255 * (1 - intensity))
            return f"rgba({rb_val}, 255, {rb_val}, 0.9)", "black"
        else:
            dist = min(abs(val - 22.0), 15.0)
            intensity = dist / 15.0
            rg_val = int(255 * (1 - intensity))
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
            dist = abs(eff - 3.1)
            intensity = 1.0 - (dist / 0.1) if dist <= 0.1 else 0.0
            gb_val = int(255 * (1 - intensity))
            return f"rgba(255, {gb_val}, {gb_val}, 0.9)", "white" if intensity > 0.5 else "black"
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

    if "アッパースイング度" in metric_name and row_idx is not None:
        if row_idx == 0: base, low, high = 6.5, 3.0, 10.0
        elif row_idx == 1: base, low, high = 11.5, 8.0, 15.0
        else: base, low, high = 15.0, 10.0, 20.0
        if low <= val <= high:
            intensity = 1.0 - (abs(val - base) / ((high - low) / 2))
            return f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)", "black"
        elif val < low:
            intensity = min((low - val) / 15.0, 1.0)
            return f"rgba({int(255*(1-intensity))}, 255, {int(255*(1-intensity))}, 0.9)", "black"
        else:
            intensity = min((val - high) / 15.0, 1.0)
            return f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)", "black"

    if "バットスピード" in metric_name:
        if val < 100: return "rgba(0, 0, 255, 0.9)", "white"
        elif 100 <= val <= 110: return "rgba(255, 255, 255, 0.9)", "black"
        elif 110 < val < 120:
            intensity = (val - 110) / 10
            gb_val = int(255 * (1 - intensity))
            return f"rgba(255, {gb_val}, {gb_val}, 0.9)", "black" if intensity < 0.6 else "white"
        else: return "rgba(255, 0, 0, 0.9)", "white"

    if "スイング時間" in metric_name:
        if val < 0.14: return "rgba(255, 0, 0, 0.9)", "white"
        elif 0.14 <= val < 0.15: return "rgba(255, 180, 180, 0.9)", "black"
        elif 0.15 <= val < 0.16: return "rgba(255, 255, 255, 0.9)", "black"
        elif 0.16 <= val < 0.17: return "rgba(180, 180, 255, 0.9)", "black"
        else: return "rgba(0, 0, 255, 0.9)", "white"

    base, sensitivity = 105, 30
    diff = val - base
    intensity = min(abs(diff) / sensitivity, 1.0)
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

# --- 背番号ソート用関数 ---
def sort_players_by_number(player_list):
    def extract_num(s):
        match = re.search(r'#(\d+)', s)
        return int(match.group(1)) if match else 999
    return sorted(player_list, key=extract_num)

# --- アプリケーション本体 ---
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
    # 1. データの読み込み（練習と試合を完全に分離）
    db_practice = load_data_from_github(GITHUB_FILE_PATH)      # 練習データ
    db_game = load_data_from_github(GITHUB_GAME_FILE_PATH)     # 試合データ

    # 2. タブ1・2（練習分析）で使うメイン変数を「練習データのみ」に設定
    db_df = db_practice.copy() if not db_practice.empty else pd.DataFrame()

    # 3. タブの定義（ここが抜けているか、順番が違うとエラーになります）
    tab1, tab2, tab3, tab4 = st.tabs(["👤 個人分析", "⚔️ 比較分析", "📝 データ登録", "🏟️ 試合分析"])

    # --- 以下、各タブの中身が続く ---
    with tab1:
        st.title("🔵 個人別打撃分析")
        # (以下、元々のtab1のコード...)

    with tab1:
        st.title("🔵 個人別打撃分析")
        if not db_df.empty:
            player_col = 'Player Name' if 'Player Name' in db_df.columns else db_df.columns[-1]
            cond_col = 'スイング条件' if 'スイング条件' in db_df.columns else 'スイング条件_str'
            db_df[cond_col] = db_df[cond_col].fillna("未設定").astype(str).str.strip()
            
            all_possible_conds = sorted(db_df[cond_col].unique().tolist())
            existing_players = sort_players_by_number(db_df[player_col].dropna().unique().tolist())

            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            with c1: 
                target_player = st.selectbox("選手を選択", existing_players, key="p_tab1")
            
            pdf = db_df[db_df[player_col] == target_player].copy()
            if not pdf.empty:
                pdf['Date_Only_Str'] = pdf['DateTime'].astype(str).str.extract(r'(\d{4}-\d{2}-\d{2})')[0]
                pdf['Date_Only'] = pd.to_datetime(pdf['Date_Only_Str'], errors='coerce').dt.date
                valid_dates = pdf['Date_Only'].dropna()
                min_date = min(valid_dates) if not valid_dates.empty else datetime.date(2024,1,1)
                max_date = max(valid_dates) if not valid_dates.empty else datetime.date.today()
                
                with c2: date_range = st.date_input("分析期間", value=(min_date, max_date), key="range_tab1")
                with c3: sel_conds = st.multiselect("打撃条件 (U列)", all_possible_conds, default=all_possible_conds, key="cond_tab1")
                with c4:
                    keywords = ["スコア", "速度", "角度", "効率", "パワー", "時間", "スピード", "飛距離", "G)", "度"]
                    valid_metrics = [c for c in pdf.columns if any(k in str(c) for k in keywords)]
                    valid_metrics = [c for c in valid_metrics if pd.to_numeric(pdf[c], errors='coerce').dropna().any()]
                    priority = ["バットスピード (km/h)", "スイング時間 (秒)", "アッパースイング度 (°)"]
                    sorted_metrics = [m for m in priority if m in valid_metrics] + [m for m in valid_metrics if m not in priority]
                    target_metric = st.selectbox("分析指標", sorted_metrics, key="m_tab1")

                mask = (pdf[cond_col].isin(sel_conds))
                if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                    mask &= (pdf['Date_Only'] >= date_range[0]) & (pdf['Date_Only'] <= date_range[1])
                
                vdf = pdf[mask].copy()

                if vdf.empty:
                    st.warning(f"⚠️ 一致するデータがありません。")
                else:
                    if "手の最大スピード" in target_metric and "バットスピード (km/h)" in vdf.columns:
                        vdf[target_metric] = pd.to_numeric(vdf['バットスピード (km/h)'], errors='coerce') / pd.to_numeric(vdf[target_metric], errors='coerce')
                    else:
                        vdf[target_metric] = pd.to_numeric(vdf[target_metric], errors='coerce')
                    
                    valid_vals = vdf[target_metric].dropna()
                    if not valid_vals.empty:
                        m_max = valid_vals.min() if "時間" in target_metric else valid_vals.max()
                        m_avg = valid_vals.mean()
                        col_m1, col_m2, col_m3 = st.columns([2, 2, 4])
                        with col_m1:
                            label = "MIN" if "時間" in target_metric else "MAX"
                            st.metric(label=f"期間内 {label}", value=f"{m_max:.3f}" if "時間" in target_metric or "手の最大スピード" in target_metric else f"{m_max:.1f}")
                        with col_m2:
                            st.metric(label="期間内 平均", value=f"{m_avg:.3f}" if "時間" in target_metric or "手の最大スピード" in target_metric else f"{m_avg:.1f}")
                        with col_m3:
                            st.info(f"💡 {len(vdf)}件のスイングを分析中")

                    st.subheader(f"📊 {target_metric}：ゾーン別平均")
                    vdf['StrikeZoneX'] = pd.to_numeric(vdf['StrikeZoneX'], errors='coerce')
                    vdf['StrikeZoneY'] = pd.to_numeric(vdf['StrikeZoneY'], errors='coerce')
                    hand = PLAYER_HANDS.get(target_player, "右")
                    fig_heat = go.Figure()
                    fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
                    L_x, L_y, R_x, R_y = 125, 140, -125, 140
                    fig_heat.add_shape(type="path", path=f"M {R_x} {R_y} L -450 600 L 450 600 L {L_x} {L_y} Z", fillcolor="#8B4513", line_width=0, layer="below")
                    fig_heat.add_shape(type="circle", x0=-120, x1=120, y0=-50, y1=160, fillcolor="#8B4513", line_width=0, layer="below")
                    fig_heat.add_shape(type="path", path="M -25 70 L 25 70 L 25 45 L 0 5 L -25 45 Z", fillcolor="white", line=dict(color="#444", width=3), layer="below")
                    grid_side = 55; z_x_start, z_y_start = -(grid_side * 2.5), 180
                    
                    grid_val = np.zeros((5, 5)); grid_count = np.zeros((5, 5))
                    for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                        r = 0 if row['StrikeZoneY'] > SZ_Y_MAX else 1 if row['StrikeZoneY'] > SZ_Y_TH2 else 2 if row['StrikeZoneY'] > SZ_Y_TH1 else 3 if row['StrikeZoneY'] > SZ_Y_MIN else 4
                        c = 0 if row['StrikeZoneX'] < SZ_X_MIN else 1 if row['StrikeZoneX'] < SZ_X_TH1 else 2 if row['StrikeZoneX'] <= SZ_X_TH2 else 3 if row['StrikeZoneX'] <= SZ_X_MAX else 4
                        grid_val[r, c] += row[target_metric]; grid_count[r, c] += 1
                    display_grid = np.where(grid_count > 0, grid_val / grid_count, 0)
                    
                    for r in range(5):
                        for c in range(5):
                            x0, x1 = z_x_start + c * grid_side, z_x_start + (c + 1) * grid_side
                            y0, y1 = z_y_start + (4 - r) * grid_side, z_y_start + (5 - r) * grid_side
                            val_h = display_grid[r, c]
                            color, f_color = get_color(val_h, target_metric, row_idx=max(0, min(2, r - 1)))
                            fig_heat.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color, line=dict(color="#222", width=1))
                            if val_h > 0:
                                txt = f"{val_h:.2f}" if "手の最大スピード" in target_metric else (f"{val_h:.3f}" if "時間" in target_metric else f"{val_h:.1f}")
                                fig_heat.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=txt, showarrow=False, font=dict(size=14, color=f_color, weight="bold"))
                    fig_heat.add_shape(type="rect", x0=z_x_start+grid_side, x1=z_x_start+4*grid_side, y0=z_y_start+grid_side, y1=z_y_start+4*grid_side, line=dict(color="red", width=4), layer="above")
                    fig_heat.update_layout(width=900, height=650, xaxis=dict(range=[-320, 320], visible=False), yaxis=dict(range=[-40, 520], visible=False), margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_heat, use_container_width=True)

                    st.subheader(f"📍 {target_metric}：インパクトポイント")
                    fig_point = go.Figure()
                    fig_point.add_shape(type="rect", x0=-250, x1=250, y0=-50, y1=300, fillcolor="#8B4513", line_width=0, layer="below")
                    fig_point.add_shape(type="path", path="M -30 15 L 30 15 L 30 8 L 0 0 L -30 8 Z", fillcolor="white", line=dict(color="#444", width=2))
                    bx = 75 if hand == "左" else -75
                    fig_point.add_shape(type="rect", x0=bx-15, x1=bx+15, y0=20, y1=160, fillcolor="rgba(200,200,200,0.4)", line_width=0)
                    fig_point.add_shape(type="circle", x0=bx-10, x1=bx+10, y0=165, y1=195, fillcolor="rgba(200,200,200,0.4)", line_width=0)
                    fig_point.add_shape(type="rect", x0=SZ_X_MIN, x1=SZ_X_MAX, y0=SZ_Y_MIN, y1=SZ_Y_MAX, line=dict(color="rgba(255,255,255,0.8)", width=4))
                    for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                        plot_x = row['StrikeZoneX']
                        r_pt = 0 if row['StrikeZoneY'] > SZ_Y_TH2 else 1 if row['StrikeZoneY'] > SZ_Y_TH1 else 2
                        dot_color, _ = get_color(row[target_metric], target_metric, row_idx=r_pt)
                        fig_point.add_trace(go.Scatter(x=[plot_x], y=[row['StrikeZoneY']], mode='markers', marker=dict(size=14, color=dot_color, line=dict(width=1.2, color="white")), showlegend=False))
                    fig_point.update_layout(height=750, xaxis=dict(range=[-130, 130], visible=False), yaxis=dict(range=[-20, 230], visible=False), margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_point, use_container_width=True)

                    st.subheader(f"📈 {target_metric}：月別推移")
                    pdf_for_graph = pdf.copy()
                    if "手の最大スピード" in target_metric and "バットスピード (km/h)" in pdf_for_graph.columns:
                        pdf_for_graph[target_metric] = pd.to_numeric(pdf_for_graph['バットスピード (km/h)'], errors='coerce') / pd.to_numeric(pdf_for_graph[target_metric], errors='coerce')
                    else:
                        pdf_for_graph[target_metric] = pd.to_numeric(pdf_for_graph[target_metric], errors='coerce')
                    pdf_for_graph['Month_Name'] = pd.to_datetime(pdf_for_graph['Date_Only']).dt.month.astype(str) + "月"
                    pdf_for_graph['Month_Sort'] = pd.to_datetime(pdf_for_graph['Date_Only']).dt.strftime('%Y-%m')
                    graph_df = pdf_for_graph[pdf_for_graph[cond_col].isin(sel_conds)].dropna(subset=[target_metric])
                    if not graph_df.empty:
                        monthly_stats = graph_df.groupby(['Month_Sort', 'Month_Name'])[target_metric].agg(['mean', 'max', 'min']).reset_index()
                        monthly_stats = monthly_stats.sort_values('Month_Sort')
                        fig_trend = go.Figure()
                        is_time = "時間" in target_metric
                        trend_best_label = "月間最速(MIN)" if is_time else "月間最大(MAX)"
                        trend_best_val = monthly_stats['min'] if is_time else monthly_stats['max']
                        fig_trend.add_trace(go.Scatter(x=monthly_stats['Month_Name'], y=trend_best_val, name=trend_best_label, line=dict(color='#FF4B4B', width=4), mode='lines+markers'))
                        fig_trend.add_trace(go.Scatter(x=monthly_stats['Month_Name'], y=monthly_stats['mean'], name="月間平均", line=dict(color='#0068C9', width=3, dash='dot'), mode='lines+markers'))
                        fig_trend.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20), hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), yaxis=dict(rangemode="tozero"), xaxis=dict(type='category'))
                        st.plotly_chart(fig_trend, use_container_width=True)

    with tab2:
        st.title("⚔️ 選手間比較分析")
        if not db_df.empty:
            player_col = 'Player Name' if 'Player Name' in db_df.columns else db_df.columns[-1]
            existing_players = sort_players_by_number(db_df[player_col].dropna().unique().tolist())
            
            keywords = ["スコア", "速度", "角度", "効率", "パワー", "時間", "スピード", "飛距離", "G)", "度"]
            all_metrics_c = [c for c in db_df.columns if any(k in str(c) for k in keywords)]
            all_metrics_c = [c for c in all_metrics_c if pd.to_numeric(db_df[c], errors='coerce').dropna().any()]
            
            priority = ["バットスピード (km/h)", "スイング時間 (秒)", "アッパースイング度 (°)"]
            sorted_comp_metrics = [m for m in priority if m in all_metrics_c] + [m for m in all_metrics_c if m not in priority]

            c1, c2 = st.columns(2)
            with c1: comp_metric = st.selectbox("比較指標", sorted_comp_metrics, key="m_tab2")
            with c2:
                cond_col = 'スイング条件' if 'スイング条件' in db_df.columns else 'スイング条件_str'
                all_conds_c = sorted([str(x) for x in db_df[cond_col].unique().tolist()])
                sel_conds_c = st.multiselect("打撃条件で絞り込む", all_conds_c, default=all_conds_c, key="cond_tab2")
            
            db_df_c = db_df.copy()
            db_df_c[cond_col] = db_df_c[cond_col].fillna("未設定").astype(str).str.strip()
            fdf = db_df_c[db_df_c[cond_col].isin(sel_conds_c)].copy()
            
            if not fdf.empty and comp_metric:
                if "手の最大スピード" in comp_metric:
                    fdf[comp_metric] = pd.to_numeric(fdf['バットスピード (km/h)'], errors='coerce') / pd.to_numeric(fdf[comp_metric], errors='coerce')
                else:
                    fdf[comp_metric] = pd.to_numeric(fdf[comp_metric], errors='coerce')
                fdf['StrikeZoneY'] = pd.to_numeric(fdf['StrikeZoneY'], errors='coerce')
                is_time = "スイング時間" in comp_metric
                is_upper = "アッパースイング度" in comp_metric

                st.subheader(f"🥇 {'理想範囲への的中率' if is_upper else '指標別'} トップ3")
                
                if is_upper:
                    def check_success(row):
                        val, y = row[comp_metric], row['StrikeZoneY']
                        if pd.isna(val) or pd.isna(y): return None
                        if y > SZ_Y_TH2: return 3.0 <= val <= 10.0
                        elif y > SZ_Y_TH1: return 8.0 <= val <= 15.0
                        else: return 10.0 <= val <= 20.0
                    fdf['is_success'] = fdf.apply(check_success, axis=1)
                    top3_series = fdf.groupby(player_col)['is_success'].mean().sort_values(ascending=False).head(3)
                    top3_scores = [f"{s*100:.1f}%" for s in top3_series.values]
                else:
                    top3_series = fdf.groupby(player_col)[comp_metric].mean().sort_values(ascending=is_time).head(3)
                    top3_scores = [f"{s:.2f}" if "手の最大スピード" in comp_metric else (f"{s:.3f}" if is_time else f"{s:.1f}") for s in top3_series.values]

                top3_names = top3_series.index.tolist()
                podium_order = [1, 0, 2] if len(top3_names) >= 3 else list(range(len(top3_names)))
                t_cols = st.columns(3)
                for i, idx in enumerate(podium_order):
                    if idx < len(top3_names):
                        name, score_str, rank = top3_names[idx], top3_scores[idx], idx + 1
                        with t_cols[i]:
                            st.markdown(f"<div style='text-align: center; background-color: #333; padding: 5px; border-radius: 5px;'><span style='font-size: 1.1rem; font-weight: bold; color: white;'>{rank}位: {name}</span><br><span style='font-size: 0.9rem; color: #ddd;'>{score_str}</span></div>", unsafe_allow_html=True)
                            grid, _ = get_3x3_grid(fdf[fdf[player_col] == name], comp_metric)
                            fig = go.Figure()
                            for r_idx in range(3):
                                for c_idx in range(3):
                                    v = grid[r_idx, c_idx]; color, f_color = get_color(v, comp_metric, row_idx=r_idx)
                                    fig.add_shape(type="rect", x0=c_idx-0.5, x1=c_idx+0.5, y0=2.5-r_idx, y1=1.5-r_idx, fillcolor=color, line=dict(color="#222", width=2))
                                    if v > 0: fig.add_annotation(x=c_idx, y=2-r_idx, text=f"{v:.2f}" if "手の最大スピード" in comp_metric else (f"{v:.3f}" if is_time else f"{v:.1f}"), showarrow=False, font=dict(color=f_color, weight="bold", size=14))
                            fig.update_layout(height=350, margin=dict(l=5, r=5, t=5, b=5), xaxis=dict(visible=False, range=[-0.6, 2.6]), yaxis=dict(visible=False, range=[-0.6, 2.6]), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                            st.plotly_chart(fig, use_container_width=True, key=f"top3_{rank}", config={'displayModeBar': False})

                st.markdown("---")
                st.subheader("🆚 2名ピックアップ比較")
                ca, cb = st.columns(2)
                with ca: player_a = st.selectbox("選手Aを選択", existing_players, key="compare_a")
                with cb: player_b = st.selectbox("選手Bを選択", existing_players, key="compare_b")
                if player_a and player_b:
                    limit = 0.05 if "手の最大スピード" in comp_metric else (0.010 if is_time else 5.0)
                    g_a, _ = get_3x3_grid(fdf[fdf[player_col] == player_a], comp_metric)
                    g_b, _ = get_3x3_grid(fdf[fdf[player_col] == player_b], comp_metric)
                    p_cols = st.columns(2)
                    for idx, (name, mine, yours) in enumerate([(player_a, g_a, g_b), (player_b, g_b, g_a)]):
                        with p_cols[idx]:
                            st.write(f"**{name} の傾向**")
                            fig_pair = go.Figure()
                            for r_idx in range(3):
                                for c_idx in range(3):
                                    v, ov = mine[r_idx, c_idx], yours[r_idx, c_idx]
                                    diff = abs(v - ov) if (v > 0 and ov > 0) else 0
                                    lw, lc = (5, "yellow") if diff >= limit else (1, "gray")
                                    if is_time: font_c = "red" if (v < ov and v > 0 and ov > 0) else "blue" if (v > ov and v > 0 and ov > 0) else "black"
                                    else: font_c = "red" if (v > ov and v > 0 and ov > 0) else "blue" if (v < ov and v > 0 and ov > 0) else "black"
                                    fig_pair.add_shape(type="rect", x0=c_idx-0.5, x1=c_idx+0.5, y0=2.5-r_idx, y1=1.5-r_idx, fillcolor="white", line=dict(color=lc, width=lw))
                                    if v > 0: fig_pair.add_annotation(x=c_idx, y=2-r_idx, text=f"{v:.2f}" if "手の最大スピード" in comp_metric else (f"{v:.3f}" if is_time else f"{v:.1f}"), showarrow=False, font=dict(color=font_c, weight="bold", size=16))
                            fig_pair.update_layout(height=400, margin=dict(t=30), xaxis=dict(tickvals=[0,1,2], ticktext=['左','中','右'], side="top"), yaxis=dict(tickvals=[0,1,2], ticktext=['高','中','低']))
                            st.plotly_chart(fig_pair, use_container_width=True, key=f"pair_{idx}")

    with tab3:
        st.title("📝 データ登録")
        sub_tab_practice, sub_tab_game = st.tabs(["🏋️ 練習データ登録", "🏟️ 試合データ登録"])
        reg_players_sorted = sort_players_by_number(PLAYERS)
        
        with sub_tab_practice:
            c1, c2 = st.columns(2)
            with c1: p_reg_player = st.selectbox("登録する選手を選択", reg_players_sorted, key="reg_p_practice")
            with c2: p_reg_date = st.date_input("打撃日を選択", value=datetime.date.today(), key="reg_d_practice")
            p_uploaded_file = st.file_uploader("練習のExcelファイルをアップロード (.xlsx)", type=["xlsx"], key="file_practice")
            if p_uploaded_file is not None:
                try:
                    input_df = pd.read_excel(p_uploaded_file)
                    input_df['試合区別'] = "練習"
                    if st.button("練習データをGitHubへ保存"):
                        with st.spinner('保存中...'):
                            time_col_name = input_df.columns[0]
                            cmap = {time_col_name: 'time_col', 'ExitVelocity': '打球速度', 'PitchBallVelocity': '投球速度', 'LaunchAngle': '打球角度', 'ExitDirection': '打球方向', 'Spin': '回転数', 'Distance': '飛距離', 'SpinDirection': '回転方向'}
                            input_df = input_df.rename(columns=cmap)
                            date_str = p_reg_date.strftime('%Y-%m-%d')
                            input_df['DateTime'] = date_str + ' ' + input_df['time_col'].astype(str).str.strip()
                            input_df['Player Name'] = p_reg_player
                            if 'スイング条件' not in input_df.columns: input_df['スイング条件'] = "未設定"
                            # --- 修正：練習用パスへ保存 ---
                            latest_db = load_data_from_github(GITHUB_FILE_PATH)
                            updated_db = pd.concat([latest_db, input_df], ignore_index=True) if not latest_db.empty else input_df
                            success, message = save_to_github(updated_db, GITHUB_FILE_PATH)
                            if success: st.success("✅ 練習データを保存しました！"); st.balloons()
                            else: st.error(f"❌ 失敗: {message}")
                except Exception as e: st.error(f"❌ エラー: {e}")

        with sub_tab_game:
            c1, c2, c3 = st.columns(3)
            with c1: g_reg_player = st.selectbox("登録する選手を選択", reg_players_sorted, key="reg_p_game")
            with c2: g_reg_date = st.date_input("打撃日を選択", value=datetime.date.today(), key="reg_d_game")
            with c3: game_category = st.selectbox("試合区別", ["オープン戦", "紅白戦", "JAVA大会", "二大大会", "二大大会予選", "その他"], key="reg_cat_game")
            g_uploaded_file = st.file_uploader("試合のExcelファイルをアップロード (.xlsx)", type=["xlsx"], key="file_game")
            if g_uploaded_file is not None:
                try:
                    input_df = pd.read_excel(g_uploaded_file)
                    input_df['試合区別'] = game_category
                    
                    # --- 追加修正：試合データの「コース」列を解析して座標列を作る ---
                    if 'コース' in input_df.columns:
                        coords = input_df['コース'].apply(convert_course_to_coord)
                        input_df['StrikeZoneX'] = [c[0] for c in coords]
                        input_df['StrikeZoneY'] = [c[1] for c in coords]
                    
                    if st.button("試合データをGitHubへ保存"):
                        with st.spinner('保存中...'):
                            time_col_name = input_df.columns[0]
                            cmap = {time_col_name: 'time_col', 'ExitVelocity': '打球速度', 'PitchBallVelocity': '投球速度', 'LaunchAngle': '打球角度', 'ExitDirection': '打球方向', 'Spin': '回転数', 'Distance': '飛距離', 'SpinDirection': '回転方向'}
                            input_df = input_df.rename(columns=cmap)
                            date_str = g_reg_date.strftime('%Y-%m-%d')
                            input_df['DateTime'] = date_str + ' ' + input_df['time_col'].astype(str).str.strip()
                            input_df['Player Name'] = g_reg_player
                            if 'スイング条件' not in input_df.columns: input_df['スイング条件'] = "未設定"
                            # --- 修正：試合用パスへ保存 ---
                            latest_db = load_data_from_github(GITHUB_GAME_FILE_PATH)
                            updated_db = pd.concat([latest_db, input_df], ignore_index=True) if not latest_db.empty else input_df
                            success, message = save_to_github(updated_db, GITHUB_GAME_FILE_PATH)
                            if success: st.success(f"✅ [{game_category}] データを保存しました！"); st.balloons()
                            else: st.error(f"❌ 失敗: {message}")
                except Exception as e: st.error(f"❌ エラー: {e}")

       # --- タブ4：試合分析 (構成入れ替え：ヒートマップ → 詳細データ) ---
    with tab4:
        st.title("🏟️ 試合分析")
        if not db_game.empty:
    # 1. 選手選択
    game_player_col = 'Player Name' if 'Player Name' in db_game.columns else db_game.columns[-1]
    game_players = sort_players_by_number(db_game[game_player_col].dropna().unique().tolist())
    
    c1, c2, c3 = st.columns([2, 3, 3])
    with c1:
        target_game_player = st.selectbox("分析する選手を選択", game_players, key="p_tab4")
    
    gdf = db_game[db_game[game_player_col] == target_game_player].copy()
    
    if not gdf.empty:
        # 2. 試合種別の選択
        game_cats = sorted(gdf['試合区別'].dropna().unique().tolist())
        with c2:
            selected_cat = st.selectbox("試合種別を選択", game_cats, key="cat_tab4")
        
        cat_filtered_df = gdf[gdf['試合区別'] == selected_cat].copy()
        
        # 3. 対戦相手の選択
        opponent_col = cat_filtered_df.columns[0]
        cat_filtered_df['Match_Label'] = cat_filtered_df[opponent_col].astype(str) + " (" + cat_filtered_df['DateTime'].astype(str).str[:10] + ")"
        
        # --- ここを修正：選択肢の先頭に「全試合合計」を追加 ---
        match_options = ["全試合合計"] + sorted(cat_filtered_df['Match_Label'].unique().tolist(), reverse=True)

        with c3:
            selected_match = st.selectbox("試合（対戦相手）を選択", match_options, key="match_tab4")

        # 4. 最終的な試合データの抽出
        # --- ここを修正：全試合合計が選ばれた場合の分岐処理 ---
        if selected_match == "全試合合計":
            final_gdf = cat_filtered_df.copy()
            display_title = f"📊 {selected_cat} 全試合合計データ ({len(final_gdf['Match_Label'].unique())}試合)"
        else:
            final_gdf = cat_filtered_df[cat_filtered_df['Match_Label'] == selected_match].copy()
            display_title = f"⚡️ {selected_match}"

        if not final_gdf.empty:
            st.markdown(f"### {display_title}")
            
            # --- A. 指標サマリー ---
            col_m1, col_m2 = st.columns(2)
            if '打球速度' in final_gdf.columns:
                final_gdf['打球速度'] = pd.to_numeric(final_gdf['打球速度'], errors='coerce')
                max_v = final_gdf['打球速度'].max()
                # ラベルを状況に応じて変更
                label_v = "期間中 最大速度" if selected_match == "全試合合計" else "試合中 最大速度"
                col_m1.metric(label_v, f"{max_v:.1f} km/h")
            
            if '結果' in final_gdf.columns:
                hits = len(final_gdf[final_gdf['結果'].str.contains('安打|本塁打|二塁打|三塁打', na=False)])
                label_h = "通算安打数" if selected_match == "全試合合計" else "この試合の安打数"
                col_m2.metric(label_h, f"{hits}")

            # --- B. ヒートマップ表示 ---
            st.markdown("---")
            heatmap_title = "🎯 期間中コース別平均 (3x3)" if selected_match == "全試合合計" else "🎯 試合用コース別ヒートマップ (3x3)"
            st.subheader(heatmap_title)
            
            # (以下、ヒートマップのロジックは final_gdf を使うので変更なしで動作します)
            keywords_h = ["速度", "角度", "効率", "パワー", "時間", "スピード", "飛距離", "度"]
            valid_metrics_h = [c for c in final_gdf.columns if any(k in str(c) for k in keywords_h)]
            valid_metrics_h = [c for c in valid_metrics_h if pd.to_numeric(final_gdf[c], errors='coerce').dropna().any()]
            
            if valid_metrics_h:
                target_metric_h = st.selectbox("表示する指標を選択", valid_metrics_h, key="m_tab4_h")
                
                final_gdf[target_metric_h] = pd.to_numeric(final_gdf[target_metric_h], errors='coerce')
                final_gdf['StrikeZoneX'] = pd.to_numeric(final_gdf['StrikeZoneX'], errors='coerce')
                final_gdf['StrikeZoneY'] = pd.to_numeric(final_gdf['StrikeZoneY'], errors='coerce')
                
                vdf_h = final_gdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric_h]).copy()
                
                if not vdf_h.empty:
                    import plotly.graph_objects as go
                    import numpy as np
                    fig_heat_g = go.Figure()
                    fig_heat_g.add_shape(type="rect", x0=-200, x1=200, y0=20, y1=130, fillcolor="#222", line_width=1, layer="below")
                    
                    grid_val_g = np.zeros((3, 3)); grid_count_g = np.zeros((3, 3))
                    for _, row in vdf_h.iterrows():
                        c = 0 if row['StrikeZoneX'] < SZ_X_TH1 else 1 if row['StrikeZoneX'] <= SZ_X_TH2 else 2
                        r = 0 if row['StrikeZoneY'] > SZ_Y_TH2 else 1 if row['StrikeZoneY'] > SZ_Y_TH1 else 2
                        grid_val_g[r, c] += row[target_metric_h]; grid_count_g[r, c] += 1
                    
                    display_grid_g = np.where(grid_count_g > 0, grid_val_g / grid_count_g, 0)
                    
                    for r_idx in range(3):
                        for c_idx in range(3):
                            x0, x1 = -150 + c_idx*100, -50 + c_idx*100
                            y0, y1 = 90 - r_idx*35, 125 - r_idx*35
                            v = display_grid_g[r_idx, c_idx]; cnt = int(grid_count_g[r_idx, c_idx])
                            # get_color関数が定義されている前提
                            color, f_color = get_color(v, target_metric_h, row_idx=r_idx)
                            fig_heat_g.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color, line=dict(color="#444", width=2))
                            if v > 0:
                                txt = f"{v:.2f}" if "手の最大スピード" in target_metric_h else (f"{v:.3f}" if "時間" in target_metric_h else f"{v:.1f}")
                                fig_heat_g.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2 + 5, text=txt, showarrow=False, font=dict(size=18, color=f_color, weight="bold"))
                                fig_heat_g.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2 - 10, text=f"{cnt}打席", showarrow=False, font=dict(size=11, color=f_color))
                    
                    fig_heat_g.update_layout(width=500, height=500, xaxis=dict(visible=False, range=[-210, 210]), yaxis=dict(visible=False, range=[10, 140]), plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=10,t=10,b=10))
                    st.plotly_chart(fig_heat_g, config={'displayModeBar': False})
                else:
                    st.warning("有効なコースデータがありません。")

            # --- C. 詳細データ一覧 ---
            st.markdown("---")
            st.write(f"🔍 **詳細データ一覧 ({'全試合' if selected_match == '全試合合計' else '選択試合'})**")
            cols_idx = list(range(1, 6)) + list(range(9, len(final_gdf.columns) - 1))
            display_df = final_gdf.iloc[:, cols_idx]
            st.dataframe(display_df, use_container_width=True)

        else:
            st.warning("条件に一致するデータがありません。")
