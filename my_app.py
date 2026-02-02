import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import requests
import base64
import io

# --- 基本設定 (変更なし) ---
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
    data = {"message": "Update batting data via Excel", "content": b64_content}
    if sha: data["sha"] = sha
    put_res = requests.put(url, headers=headers, json=data)
    return put_res.status_code in [200, 201]

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
    tab1, tab2 = st.tabs(["📊 データ分析", "📝 データ登録"])

    # (分析タブの内容は省略)

    with tab2:
        st.title("📝 Excelデータ一括登録")
        
        with st.expander("登録設定", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                reg_player = st.selectbox("登録する選手を選択", PLAYERS, key="reg_p")
            with col2:
                reg_date = st.date_input("登録する日付を選択", datetime.date.today(), key="reg_d")
        
        uploaded_file = st.file_uploader("Excelファイルをアップロードしてください (.xlsx)", type=["xlsx"])
        
        if uploaded_file is not None:
            try:
                # Excel読み込み
                input_df = pd.read_excel(uploaded_file)
                st.write("📋 アップロードされたデータプレビュー:")
                st.dataframe(input_df.head())
                
                if st.button("このデータをGitHubに保存する"):
                    # データの整形
                    # 画面で選んだ選手名と日付を適用
                    input_df['Player Name'] = reg_player
                    # 時間の列がある場合は日付と結合、ない場合は日付のみ
                    if 'DateTime' in input_df.columns:
                        # Excel側のDateTimeから時間情報だけ抜き出し、選択した日付と合体させる処理など
                        pass 
                    else:
                        input_df['DateTime'] = reg_date.strftime('%Y-%m-%d')
                    
                    # 既存のデータと結合
                    final_df = pd.concat([db_df, input_df], ignore_index=True)
                    
                    # GitHubへ保存
                    if save_to_github(final_df):
                        st.success(f"✅ {reg_player}のデータを{len(input_df)}件登録しました！")
                        st.balloons()
                    else:
                        st.error("❌ GitHubへの保存に失敗しました。トークンや権限を確認してください。")
            
            except Exception as e:
                st.error(f"⚠️ エラーが発生しました: {e}")
