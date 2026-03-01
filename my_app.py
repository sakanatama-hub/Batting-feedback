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
GITHUB_FILE_PATH = "data.csv"         # 練習データ保存用
GITHUB_GAME_FILE_PATH = "game_data.csv" # 試合データ保存用
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- ストライクゾーン定義 (cm) ---
SZ_X_MIN, SZ_X_MAX = -28.8, 28.8
SZ_X_TH1, SZ_X_TH2 = -9.6, 9.6
SZ_Y_MIN, SZ_Y_MAX = 45.0, 110.0
SZ_Y_TH1, SZ_Y_TH2 = 66.6, 88.3

# 保存済みの選手名・利き手データ
PLAYER_HANDS = {"#1 熊田 任洋": "左", "#2 逢澤 崚介": "左", "#3 三塚 武蔵": "左", "#4 北村 祥治": "右", "#5 前田 健伸": "左", "#6 佐藤 勇基": "右", "#7 西村 友哉": "右", "#8 和田 佳大": "左", "#9 今泉 颯太": "右", "#10 福井 章吾": "左", "#22 高祖 健輔": "左", "#23 箱山 遥人": "右", "#24 坂巻 尚哉": "右", "#26 西村 彰浩": "左", "#27 小畑 尋規": "右", "#28 宮崎 仁斗": "右", "#29 徳本 健太朗": "左", "#39 柳 元珍": "左", "#99 尾瀬 雄大": "左"}
PLAYERS = list(PLAYER_HANDS.keys())

# --- 共通関数 ---

def convert_course_to_coord(course_str):
    """試合データの『コース』文字列を座標(X, Y)に変換する"""
    if pd.isna(course_str): return None, None
    course_str = str(course_str)
    # X座標（左右）
    x = 0
    if "内" in course_str: x = -19.2
    elif "外" in course_str: x = 19.2
    # Y座標（高さ）
    y = 77.5
    if "高め" in course_str: y = 99.1
    elif "低め" in course_str: y = 55.8
    return x, y

def load_data_from_github(file_path):
    """GitHubからCSVを読み込む"""
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{file_path}?nocache={datetime.datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url, dtype=str)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

def save_to_github(new_df, file_path):
    """GitHubへCSVを保存する"""
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
    """#番号順に選手リストをソート"""
    def extract_num(s):
        match = re.search(r'#(\d+)', s)
        return int(match.group(1)) if match else 999
    return sorted(player_list, key=extract_num)

def get_color(val, metric_name, row_idx=None, eff_val=None):
    """指標に応じたヒートマップの色分けロジック"""
    if val == 0 or pd.isna(val): return "rgba(255, 255, 255, 0.1)", "white"
    
    # 常に白背景にする指標
    white_metrics = ["バット角度", "バットの角度", "打球方向", "飛距離"]
    if any(m in metric_name for m in white_metrics): return "#FFFFFF", "black"
    
    # 打球角度 (15度を理想とする)
    if "打球角度" in metric_name:
        center = 15.0
        if 8.0 <= val <= 22.0:
            intensity = 1.0 - (abs(val - center) / 7.0)
            return f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)", "white" if intensity > 0.5 else "black"
        elif val < 8.0:
            return "rgba(144, 238, 144, 0.9)", "black" # 緑（ゴロ）
        else:
            return "rgba(173, 216, 230, 0.9)", "black" # 青（フライ）

    # 打球速度
    if "打球速度" in metric_name:
        if val < 140: return "rgba(0, 0, 255, 0.9)", "white"
        elif val <= 152: return "rgba(255, 255, 255, 0.9)", "black"
        else: return "rgba(255, 0, 0, 0.9)", "white"

    # その他汎用的な色分け
    base, sensitivity = 105, 30
    diff = val - base
    intensity = min(abs(diff) / sensitivity, 1.0)
    color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff > 0 else f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
    return color, "black" if intensity < 0.4 else "white"

# --- メインアプリ ---
st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")

if "ok" not in st.session_state: st.session_state["ok"] = False

if not st.session_state["ok"]:
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("PASSWORD", type="password")
    if st.button("LOGIN"):
        if val == PW: st.session_state["ok"] = True; st.rerun()
else:
    # 練習データをデフォルトDBとして読み込む
    db_df = load_data_from_github(GITHUB_FILE_PATH)
    
    tab1, tab2, tab3, tab4 = st.tabs(["👤 個人分析", "⚔️ 比較分析", "📝 データ登録", "🏟️ 試合分析"])

    # --- タブ1: 個人分析 ---
    with tab1:
        st.title("🔵 個人別打撃分析")
        if not db_df.empty:
            player_col = 'Player Name'
            cond_col = 'スイング条件'
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
                    st.subheader(f"📊 {target_metric}：ゾーン別平均 (5x5)")
                    vdf['StrikeZoneX'] = pd.to_numeric(vdf['StrikeZoneX'], errors='coerce')
                    vdf['StrikeZoneY'] = pd.to_numeric(vdf['StrikeZoneY'], errors='coerce')
                    vdf[target_metric] = pd.to_numeric(vdf[target_metric], errors='coerce')
                    
                    fig_heat = go.Figure()
                    # 芝生背景風
                    fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
                    
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
                            color, f_color = get_color(val_h, target_metric)
                            fig_heat.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color, line=dict(color="#222", width=1))
                            if val_h > 0: fig_heat.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=f"{val_h:.1f}", showarrow=False, font=dict(color=f_color))
                    
                    fig_heat.update_layout(width=700, height=500, xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=0,r=0,t=0,b=0))
                    st.plotly_chart(fig_heat)
                else:
                    st.warning("条件に一致するデータがありません。")

    # --- タブ2: 比較分析 ---
    with tab2:
        st.title("⚔️ 選手間比較分析")
        st.info("タブ1と同様のロジックで複数選手の傾向を比較する機能をここに実装します。")

    # --- タブ3: データ登録 (ここが修正の肝) ---
    with tab3:
        st.title("📝 データ登録")
        sub_tab_practice, sub_tab_game = st.tabs(["🏋️ 練習データ登録", "🏟️ 試合データ登録"])
        reg_players_sorted = sort_players_by_number(PLAYERS)
        
        # 指標のリネームマップ
        cmap = {'ExitVelocity': '打球速度', 'PitchBallVelocity': '投球速度', 'LaunchAngle': '打球角度', 
                'ExitDirection': '打球方向', 'Spin': '回転数', 'Distance': '飛距離', 'SpinDirection': '回転方向'}

        # --- 練習データ登録 ---
        with sub_tab_practice:
            c1, c2 = st.columns(2)
            with c1: p_reg_player = st.selectbox("登録する選手を選択", reg_players_sorted, key="reg_p_practice")
            with c2: p_reg_date = st.date_input("打撃日を選択", value=datetime.date.today(), key="reg_d_practice")
            p_uploaded_file = st.file_uploader("練習のExcelファイルをアップロード (.xlsx)", type=["xlsx"], key="file_practice")
            
            if p_uploaded_file:
                try:
                    input_df = pd.read_excel(p_uploaded_file)
                    input_df['試合区別'] = "練習"
                    if st.button("練習データをGitHubへ保存"):
                        with st.spinner('保存中...'):
                            time_col = input_df.columns[0]
                            input_df = input_df.rename(columns={time_col: 'time_col', **cmap})
                            date_str = p_reg_date.strftime('%Y-%m-%d')
                            input_df['DateTime'] = date_str + ' ' + input_df['time_col'].astype(str).str.strip()
                            input_df['Player Name'] = p_reg_player
                            if 'スイング条件' not in input_df.columns: input_df['スイング条件'] = "未設定"
                            
                            # 練習用ファイル(data.csv)をロードして結合
                            latest_db = load_data_from_github(GITHUB_FILE_PATH)
                            updated_db = pd.concat([latest_db, input_df], ignore_index=True)
                            success, msg = save_to_github(updated_db, GITHUB_FILE_PATH)
                            if success: st.success("✅ 練習データを保存しました！"); st.balloons()
                            else: st.error(f"❌ 失敗: {msg}")
                except Exception as e: st.error(f"❌ エラー: {e}")

        # --- 試合データ登録 ---
        with sub_tab_game:
            c1, c2, c3 = st.columns(3)
            with c1: g_reg_player = st.selectbox("登録する選手を選択", reg_players_sorted, key="reg_p_game")
            with c2: g_reg_date = st.date_input("打撃日を選択", value=datetime.date.today(), key="reg_d_game")
            with c3: game_category = st.selectbox("試合区別", ["オープン戦", "紅白戦", "JAVA大会", "二大大会", "二大大会予選", "その他"], key="reg_cat_game")
            g_uploaded_file = st.file_uploader("試合のExcelファイルをアップロード (.xlsx)", type=["xlsx"], key="file_game")
            
            if g_uploaded_file:
                try:
                    input_df = pd.read_excel(g_uploaded_file)
                    input_df['試合区別'] = game_category
                    
                    # --- 試合データ特有：『コース』列を解析して座標を作る ---
                    if 'コース' in input_df.columns:
                        coords = input_df['コース'].apply(convert_course_to_coord)
                        input_df['StrikeZoneX'] = [c[0] for c in coords]
                        input_df['StrikeZoneY'] = [c[1] for c in coords]
                    
                    if st.button("試合データをGitHubへ保存"):
                        with st.spinner('保存中...'):
                            time_col = input_df.columns[0]
                            input_df = input_df.rename(columns={time_col: 'time_col', **cmap})
                            date_str = g_reg_date.strftime('%Y-%m-%d')
                            input_df['DateTime'] = date_str + ' ' + input_df['time_col'].astype(str).str.strip()
                            input_df['Player Name'] = g_reg_player
                            if 'スイング条件' not in input_df.columns: input_df['スイング条件'] = "未設定"
                            
                            # 試合用ファイル(game_data.csv)をロードして結合
                            latest_db = load_data_from_github(GITHUB_GAME_FILE_PATH)
                            updated_db = pd.concat([latest_db, input_df], ignore_index=True)
                            success, msg = save_to_github(updated_db, GITHUB_GAME_FILE_PATH)
                            if success: st.success(f"✅ [{game_category}] データを保存しました！"); st.balloons()
                            else: st.error(f"❌ 失敗: {msg}")
                except Exception as e: st.error(f"❌ エラー: {e}")

    # --- タブ4: 試合分析 ---
    with tab4:
        st.title("🏟️ 試合分析")
        # 試合専用CSVを読み込む
        game_db = load_data_from_github(GITHUB_GAME_FILE_PATH)
        if not game_db.empty:
            st.write(f"📈 登録済み試合データ ({len(game_db)}件)")
            # 簡易表示
            st.dataframe(game_db[['DateTime', 'Player Name', '試合区別', 'コース', 'バットスピード (km/h)']].head(20))
            
            st.divider()
            st.info("ここに試合データに基づいたヒートマップや、コース別の打率傾向などを実装可能です。")
        else:
            st.info("試合データがまだ登録されていません。「データ登録」タブから試合データをアップロードしてください。")
