import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import datetime
import base64
import requests
from streamlit_gsheets import GSheetsConnection

# --- 基本設定 ---
PW = "TOYOTABASEBALLCLUB"
# 閲覧用のURL
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1uXTl0qap2MWW2b1Y-dTUl5UZ7ierJvWv9znmLzCDnBk/edit"
# 書き込み用のURL (先ほどコピーしていただいたもの)
GAS_URL = "https://script.google.com/macros/s/AKfycbzl5UzwgcbsIzFRZgaW3oeq5w6RJ1atDc8Ojs3UBi_BYte0noqvDTGihNbehVTGQgFc/exec"

PLAYERS = [
    "#1 熊田 任洋", "#2 逢澤 崚介", "#3 三塚 武蔵", "#4 北村 祥治", "#5 前田 健伸",
    "#6 佐藤 勇基", "#7 西村 友哉", "#8 和田 佳大", "#9 今泉 颯太", "#10 福井 章吾",
    "#22 高祖 健輔", "#23 箱山 遥人", "#24 坂巻 尚哉", "#26 西村 彰浩", "#27 小畑 尋規",
    "#28 宮崎 仁斗", "#29 徳本 健太朗", "#39 柳 元珍", "#99 尾瀬 雄大"
]

LOCAL_IMAGE_PATH = "捕手目線.png"

def get_encoded_bg(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return None

def check_auth():
    if "ok" not in st.session_state:
        st.session_state["ok"] = False
    if st.session_state["ok"]:
        return True
    st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("パスワードを入力", type="password")
    if st.button("ログイン"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
        else:
            st.error("パスワードが違います")
    return False

if check_auth():
    # スプレッドシート接続（読み込み用）
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    @st.cache_data(ttl=10)
    def load_data():
        # 一番左のシートを読み込む
        return conn.read(spreadsheet=SPREADSHEET_URL)

    try:
        db_df = load_data()
    except:
        st.error("データの読み込みに失敗しました。")
        st.stop()

    mode = st.sidebar.radio("メニュー", ["📊 データ分析", "📥 新規登録"])

    if mode == "📊 データ分析":
        st.header("📊 打撃データ分析")
        if db_df.empty:
            st.warning("スプレッドシートにデータがありません。")
        else:
            target_player = st.sidebar.selectbox("選手を選択", PLAYERS)
            db_df['DateTime'] = pd.to_datetime(db_df['DateTime'], errors='coerce')
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            
            if pdf.empty:
                st.info(f"{target_player} 選手のデータはまだありません。")
            else:
                pdf['Date_Only'] = pdf['DateTime'].dt.date
                d_range = st.sidebar.date_input("分析期間", value=(pdf['Date_Only'].min(), pdf['Date_Only'].max()))
                
                if isinstance(d_range, tuple) and len(d_range) == 2:
                    vdf = pdf[(pdf['Date_Only'] >= d_range[0]) & (pdf['Date_Only'] <= d_range[1])].copy()
                    metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c and "ID" not in c]
                    target_metric = st.sidebar.selectbox("表示する数値", metrics)

                    if not vdf.empty and target_metric:
                        vdf['StrikeZoneX'] = pd.to_numeric(vdf['StrikeZoneX'], errors='coerce')
                        vdf['StrikeZoneY'] = pd.to_numeric(vdf['StrikeZoneY'], errors='coerce')
                        clean_df = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])

                        def get_grid_pos(x, y):
                            if y > 110: r = 0
                            elif 88.2 < y <= 110: r = 1
                            elif 66.6 < y <= 88.2: r = 2
                            elif 45 <= y <= 66.6: r = 3
                            else: r = 4
                            if x < -28.8: c = 0
                            elif -28.8 <= x < -9.6: c = 1
                            elif -9.6 <= x <= 9.6: c = 2
                            elif 9.6 < x <= 28.8: c = 3
                            else: c = 4
                            return r, c

                        grid = np.zeros((5, 5)); counts = np.zeros((5, 5))
                        for _, row in clean_df.iterrows():
                            r, c = get_grid_pos(row['StrikeZoneX'], row['StrikeZoneY'])
                            grid[r, c] += row[target_metric]; counts[r, c] += 1
                        
                        display_grid = np.where(counts > 0, grid / counts, 0)

                        fig = go.Figure(data=go.Heatmap(
                            z=np.flipud(display_grid),
                            x=['極内','内','中','外','極外'], y=['極高','高','中','低','極低'],
                            colorscale='YlOrRd', text=np.flipud(np.round(display_grid, 1)),
                            texttemplate="%{text}", showscale=True
                        ))
                        bg_img = get_encoded_bg(LOCAL_IMAGE_PATH)
                        if bg_img:
                            fig.add_layout_image(dict(source=bg_img, xref="x", yref="y", x=-0.5, y=4.5, sizex=5, sizey=5, sizing="stretch", opacity=0.4, layer="below"))
                        fig.update_layout(width=700, height=700)
                        st.plotly_chart(fig)

    elif mode == "📥 新規登録":
        st.header("📥 新規データ登録")
        target_player = st.selectbox("登録する選手", PLAYERS)
        uploaded_file = st.file_uploader("CSVファイルをアップロード", type="csv")
        
        if st.button("スプレッドシートへ保存"):
            if uploaded_file is not None:
                try:
                    new_df = pd.read_csv(uploaded_file)
                    # 選手名と日付を追加
                    new_df['Player Name'] = target_player
                    new_df['DateTime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # スプレッドシートの列順に合わせてデータを整理
                    # (スプレッドシートの1行目と同じ項目のみを抽出)
                    cols = db_df.columns.tolist()
                    # もし新しいCSVにない列があれば空にする
                    for c in cols:
                        if c not in new_df.columns:
                            new_df[c] = ""
                    
                    upload_data = new_df[cols].values.tolist()
                    
                    # GAS経由でデータを送信
                    response = requests.post(GAS_URL, json=upload_data)
                    
                    if "Success" in response.text:
                        st.success(f"{target_player} 選手のデータを保存しました！")
                        st.balloons()
                        st.cache_data.clear()
                    else:
                        st.error(f"保存に失敗しました。GASの設定を確認してください。: {response.text}")
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
            else:
                st.warning("ファイルを選択してください。")
