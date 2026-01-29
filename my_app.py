import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import datetime
import base64

# --- 基本設定 ---
PW = "TOYOTABASEBALLCLUB"
SPREADSHEET_ID = "1uXTl0qap2MWW2b1Y-dTUl5UZ7ierJvWv9znmLzCDnBk"
# 直接CSVとして読み込む最強のURL
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv"

# 選手リスト
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
    @st.cache_data(ttl=30)
    def load_data():
        df = pd.read_csv(CSV_URL)
        # 日付と選手名の列を使いやすいように調整
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        return df

    db_df = load_data()

    # サイドバーメニュー
    mode = st.sidebar.radio("機能を選択", ["📊 データ分析", "📥 新規登録"])

    if mode == "📊 データ分析":
        st.header("📊 打撃データ分析 (9分割ヒートマップ)")
        
        if db_df.empty or len(db_df) < 1:
            st.warning("まだデータがありません。先に「新規登録」からアップロードしてください。")
        else:
            # 選手選択
            target_player = st.sidebar.selectbox("選手を選択", PLAYERS)
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            
            if pdf.empty:
                st.info(f"{target_player} 選手のデータはまだありません。")
            else:
                # 日付フィルタ
                pdf['Date_Only'] = pdf['DateTime'].dt.date
                min_d, max_d = pdf['Date_Only'].min(), pdf['Date_Only'].max()
                d_range = st.sidebar.date_input("分析期間", value=(min_d, max_d))
                
                if isinstance(d_range, tuple) and len(d_range) == 2:
                    vdf = pdf[(pdf['Date_Only'] >= d_range[0]) & (pdf['Date_Only'] <= d_range[1])].copy()
                    
                    # 分析する項目の選択（バットスピード、打球速度など）
                    numeric_cols = vdf.select_dtypes(include=[np.number]).columns.tolist()
                    exclude = ["StrikeZoneX", "StrikeZoneY", "Unique ID"]
                    metrics = [c for c in numeric_cols if c not in exclude]
                    target_metric = st.sidebar.selectbox("表示する数値", metrics if metrics else ["データなし"])

                    if not vdf.empty and target_metric != "データなし":
                        # 数値に変換して欠損値を消す
                        vdf['StrikeZoneX'] = pd.to_numeric(vdf['StrikeZoneX'], errors='coerce')
                        vdf['StrikeZoneY'] = pd.to_numeric(vdf['StrikeZoneY'], errors='coerce')
                        vdf[target_metric] = pd.to_numeric(vdf[target_metric], errors='coerce')
                        clean_df = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])

                        # 5x5グリッド計算
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

                        grid = np.zeros((5, 5))
                        counts = np.zeros((5, 5))
                        for _, row in clean_df.iterrows():
                            r, c = get_grid_pos(row['StrikeZoneX'], row['StrikeZoneY'])
                            grid[r, c] += row[target_metric]
                            counts[r, c] += 1
                        
                        display_grid = np.where(counts > 0, grid / counts, 0)

                        # Plotlyで描画
                        fig = go.Figure(data=go.Heatmap(
                            z=np.flipud(display_grid),
                            x=['極内','内','中','外','極外'],
                            y=['極高','高','中','低','極低'],
                            colorscale='YlOrRd',
                            text=np.flipud(np.round(display_grid, 1)),
                            texttemplate="%{text}",
                            showscale=True
                        ))

                        bg_img = get_encoded_bg(LOCAL_IMAGE_PATH)
                        if bg_img:
                            fig.add_layout_image(dict(
                                source=bg_img, xref="x", yref="y",
                                x=-0.5, y=4.5, sizex=5, sizey=5,
                                sizing="stretch", opacity=0.4, layer="below"
                            ))
                        
                        fig.update_layout(width=700, height=700, title=f"{target_player}: {target_metric} 分布")
                        st.plotly_chart(fig)

    elif mode == "📥 新規登録":
        st.header("📥 データ登録")
        # 以前のCSVアップロード＆スプレッドシート保存ロジック（省略せずに以前のものを活用可能）
        st.info("ここにCSVをドラッグ＆ドロップしてスプレッドシートを更新する機能を配置します。")
