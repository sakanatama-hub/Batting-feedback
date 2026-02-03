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

# --- GitHub連携関数 (デバッグ強化) ---
def load_data_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}?nocache={datetime.datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        return df
    except:
        return pd.DataFrame()

def save_to_github(new_df):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. 現在のファイルのSHAを取得
    res = requests.get(url, headers=headers)
    sha = None
    if res.status_code == 200:
        sha = res.json().get("sha")
    
    # 2. データをCSV文字列に変換（DateTimeは文字列として保持）
    csv_content = new_df.to_csv(index=False)
    b64_content = base64.b64encode(csv_content.encode('utf-8-sig')).decode() # Excel対策でBOM付きUTF-8
    
    # 3. アップロード用データ
    payload = {
        "message": f"Update data: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": b64_content
    }
    if sha:
        payload["sha"] = sha
        
    # 4. 書き込みリクエスト実行
    put_res = requests.put(url, headers=headers, json=payload)
    
    if put_res.status_code in [200, 201]:
        return True, "成功"
    else:
        # 失敗した理由を詳細に返す
        return False, f"HTTP {put_res.status_code}: {put_res.text}"

# --- (中略: get_color, get_3x3_grid, UI基本設定は変更なしのため省略。ロジックは維持) ---
# --- 以下の TAB 3 の部分を重点的に差し替えてください ---

# --- (UI設定部分) ---
st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
if "ok" not in st.session_state: st.session_state["ok"] = False

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

    # --- TAB 1, TAB 2 は以前のコードと同じため、TAB 3 のみ記述します ---
    # (※実際には以前のコードの TAB 1, 2 もそのまま残してください)

    with tab3:
        st.title("📝 データ登録")
        c1, c2 = st.columns(2)
        with c1: reg_player = st.selectbox("登録する選手を選択", list(PLAYER_HANDS.keys()), key="reg_p_tab3")
        with c2: reg_date = st.date_input("打撃日を選択", value=datetime.date.today(), key="reg_d_tab3")
        uploaded_file = st.file_uploader("Excelファイルをアップロード (.xlsx)", type=["xlsx"])
        
        if uploaded_file is not None:
            try:
                input_df = pd.read_excel(uploaded_file)
                time_col_name = input_df.columns[0]
                
                # 指標名のマッピング
                cmap = {time_col_name: 'time_col', 'ExitVelocity': '打球速度', 'PitchBallVelocity': '投球速度', 'LaunchAngle': '打球角度', 'ExitDirection': '打球方向', 'Spin': '回転数', 'Distance': '飛距離', 'SpinDirection': '回転方向'}
                input_df = input_df.rename(columns=cmap)
                
                if st.button("GitHubへ保存"):
                    # 進行状況表示
                    with st.spinner('データを送信中...'):
                        input_df['time_col'] = input_df['time_col'].astype(str)
                        date_str = reg_date.strftime('%Y-%m-%d')
                        # DateTime列を文字列として作成
                        input_df['DateTime'] = date_str + ' ' + input_df['time_col']
                        input_df['Player Name'] = reg_player
                        
                        # 既存データ読み込み
                        current_db = load_data_from_github()
                        
                        # 結合
                        if not current_db.empty:
                            updated_db = pd.concat([current_db, input_df], ignore_index=True)
                        else:
                            updated_db = input_df
                        
                        # 保存実行
                        success, message = save_to_github(updated_db)
                        
                        if success:
                            st.success(f"✅ {reg_player} 選手のデータを保存しました！GitHubを確認してください。")
                            st.balloons()
                        else:
                            st.error(f"❌ 保存に失敗しました。理由: {message}")
                            st.info("※GitHubのトークン権限(Repo)が正しいか確認してください。")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {e}")
