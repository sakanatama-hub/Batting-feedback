import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import datetime
import base64
from streamlit_gsheets import GSheetsConnection

# --- 基本設定 ---
PW = "TOYOTABASEBALLCLUB"
# URLを一番シンプルな形に修正しました
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1uXTl0qap2MWW2b1Y-dTUl5UZ7ierJvWv9znmLzCDnBk/edit"

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
    # --- スプレッドシート接続 ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def load_data():
        # タブ名が「data」でも「シート1」でも読み込めるようにエラー回避設定にしました
        try:
            return conn.read(spreadsheet=SPREADSHEET_URL, worksheet="data")
        except:
            return conn.read(spreadsheet=SPREADSHEET_URL, worksheet="シート1")

    try:
        db_df = load_data()
    except Exception as e:
        st.error(f"スプレッドシートが読み込めません。共有設定が『リンクを知っている全員』になっているか確認してください。")
        st.stop()

    if not db_df.empty:
        db_df['DateTime'] = pd.to_datetime(db_df['DateTime'], errors='coerce')

    mode = st.sidebar.radio("機能", ["分析・表示", "データ登録"])

    if mode == "分析・表示":
        st.header("📊 打撃データ分析 (Spreadsheet版)")
        bg_img = get_encoded_bg(LOCAL_IMAGE_PATH)
        
        if not db_df.empty:
            sp = st.sidebar.selectbox("選手", PLAYERS)
            pdf = db_df[db_df['Player Name'] == sp].copy()
            
            if not pdf.empty:
                pdf['D_Only'] = pdf['DateTime'].dt.date
                min_d = pdf['D_Only'].min() if not pd.isnull(pdf['D_Only'].min()) else datetime.date.today()
                max_d = pdf['D_Only'].max() if not pd.isnull(pdf['D_Only'].max()) else datetime.date.today()
                
                st.sidebar.write("---")
                date_range = st.sidebar.date_input("分析期間", value=(min_d, max_d))
                
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_d, end_d = date_range
                    vdf = pdf[(pdf['D_Only'] >= start_d) & (pdf['D_Only'] <= end_d)].copy()
                    
                    if not vdf.empty:
                        # 指標の自動取得
                        numeric_cols = vdf.select_dtypes(include=[np.number]).columns.tolist()
                        avail_m = [c for c in numeric_cols if "Zone" not in c]
                        
                        if avail_m and 'StrikeZoneX' in vdf.columns:
                            tm = st.sidebar.selectbox("指標選択", avail_m)
                            
                            # 数値変換
                            vdf['StrikeZoneX'] = pd.to_numeric(vdf['StrikeZoneX'], errors='coerce')
                            vdf['StrikeZoneY'] = pd.to_numeric(vdf['StrikeZoneY'], errors='coerce')
                            vdf[tm] = pd.to_numeric(vdf[tm], errors='coerce')
                            c_df = vdf.dropna(subset=[tm, 'StrikeZoneX', 'StrikeZoneY'])

                            # グリッド計算
                            def get_full_zone(x, y):
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

                            grid_data = np.zeros((5, 5))
                            counts = np.zeros((5, 5))
                            for _, row in c_df.iterrows():
                                r, c = get_full_zone(row['StrikeZoneX'], row['StrikeZoneY'])
                                grid_data[r, c] += row[tm]
                                counts[r, c] += 1
                            final_grid = np.where(counts > 0, grid_data / counts, 0)

                            # 図の描画
                            fig = go.Figure(data=go.Heatmap(
                                z=np.flipud(final_grid),
                                x=['極内','内','中','外','極外'],
                                y=['極高','高','中','低','極低'],
                                colorscale='YlOrRd', showscale=True, xgap=2, ygap=2
                            ))
                            if bg_img:
                                fig.add_layout_image(dict(source=bg_img, xref="x", yref="y", x=-0.5, y=4.5, sizex=5, sizey=5, sizing="stretch", opacity=0.5, layer="below"))
                            
                            fig.update_layout(width=700, height=700)
                            st.plotly_chart(fig)
                        else:
                            st.warning("表示できる数値データがありません。")
                    else:
                        st.info("選択された期間にデータがありません。")

    elif mode == "データ登録":
        st.header("📥 データ登録")
        pn = st.selectbox("選手名", PLAYERS)
        f = st.file_uploader("CSVアップロード", type=["csv"])
        
        if st.button("スプレッドシートに保存") and f:
            new_data = pd.read_csv(f)
            new_data['Player Name'] = pn
            new_data['DateTime'] = datetime.date.today().strftime("%Y-%m-%d")
            updated_df = pd.concat([db_df, new_data], ignore_index=True)
            
            # スプレッドシートへ書き込み
            conn.update(spreadsheet=SPREADSHEET_URL, data=updated_df)
            st.success("スプレッドシートの更新が完了しました！")
            st.balloons()
