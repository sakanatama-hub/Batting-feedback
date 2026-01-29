import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import datetime
import base64

# --- 基本設定 ---
PW = "TOYOTABASEBALLCLUB"
DB = "toyota_baseball_db.csv"
PLAYERS = [
    "#1 熊田 任洋", "#2 逢澤 崚介", "#3 三塚 武蔵", "#4 北村 祥治", "#5 前田 健伸",
    "#6 佐藤 勇基", "#7 西村 友哉", "#8 和田 佳大", "#9 今泉 颯太", "#10 福井 章吾",
    "#22 高祖 健輔", "#23 箱山 遥人", "#24 坂巻 尚哉", "#26 西村 彰浩", "#27 小畑 尋規",
    "#28 宮崎 仁斗", "#29 徳本 健太朗", "#39 柳 元珍", "#99 尾瀬 雄大"
]

LOCAL_IMAGE_PATH = r"捕手目線.png" 

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
    val = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
        else:
            st.error("パスワード不一致")
    return False

if check_auth():
    db_df = pd.DataFrame()
    if os.path.exists(DB):
        try:
            db_df = pd.read_csv(DB)
            db_df['DateTime'] = pd.to_datetime(db_df['DateTime'], errors='coerce')
        except:
            pass

    mode = st.sidebar.radio("機能", ["分析・表示", "データ登録"])

    if mode == "分析・表示":
        st.header("📊 打撃データ分析")
        bg_img = get_encoded_bg(LOCAL_IMAGE_PATH)
        
        if not db_df.empty:
            sp = st.sidebar.selectbox("選手", PLAYERS)
            pdf = db_df[db_df['Player Name'] == sp].copy()
            
            if not pdf.empty:
                # --- 日付範囲選択への変更 ---
                pdf['D_Only'] = pdf['DateTime'].dt.date
                min_date = pdf['D_Only'].min()
                max_date = pdf['D_Only'].max()
                
                st.sidebar.write("---")
                date_range = st.sidebar.date_input(
                    "分析期間を選択",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                
                # 範囲が正しく選択されているか確認（開始と終了の両方が選ばれた時のみフィルタリング）
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_date, end_date = date_range
                    vdf = pdf[(pdf['D_Only'] >= start_date) & (pdf['D_Only'] <= end_date)].copy()
                    
                    numeric_cols = vdf.select_dtypes(include=[np.number]).columns.tolist()
                    avail_m = [c for c in numeric_cols if "Zone" not in c]
                    cx, cy = 'StrikeZoneX', 'StrikeZoneY'
                    
                    if avail_m and cx in vdf.columns:
                        tm = st.sidebar.selectbox("表示指標", avail_m)
                        is_lefty = "左" in str(vdf[vdf['利き腕'].notna()]['利き腕'].iloc[0]) if '利き腕' in vdf.columns and not vdf[vdf['利き腕'].notna()].empty else False
                        
                        for col in [tm, cx, cy]:
                            vdf[col] = pd.to_numeric(vdf[col], errors='coerce')
                        c_df = vdf.dropna(subset=[tm, cx, cy])

                        def get_full_zone(x, y):
                            if y > 110: row = 0
                            elif 88.2 < y <= 110: row = 1
                            elif 66.6 < y <= 88.2: row = 2
                            elif 45 <= y <= 66.6: row = 3
                            else: row = 4
                            if x < -28.8: col_idx = 0
                            elif -28.8 <= x < -9.6: col_idx = 1
                            elif -9.6 <= x <= 9.6: col_idx = 2
                            elif 9.6 < x <= 28.8: col_idx = 3
                            else: col_idx = 4
                            if is_lefty: col_idx = 4 - col_idx
                            return row, col_idx

                        grid_data = np.zeros((5, 5))
                        counts = np.zeros((5, 5))
                        for _, row_data in c_df.iterrows():
                            r, c = get_full_zone(row_data[cx], row_data[cy])
                            grid_data[r, c] += row_data[tm]
                            counts[r, c] += 1
                        final_grid = np.where(counts > 0, grid_data / counts, 0)

                        # カラースケール設定（既存ロジック）
                        mid_val, c_scale, txt_fmt = None, 'YlOrRd', "%{z:.1f}"
                        if "手の最大スピード" in tm or "HandSpeed" in tm:
                            mid_val, c_scale = 25, [[0, "blue"], [0.5, "white"], [1, "red"]]
                        elif "ExitDirection" in tm:
                            mid_val = 0
                            c_scale = [[0, "blue"], [0.5, "white"], [1, "red"]] if is_lefty else [[0, "red"], [0.5, "white"], [1, "blue"]]
                        elif "スイング時間" in tm or "Time" in tm:
                            mid_val, c_scale, txt_fmt = 0.15, [[0, "red"], [0.5, "white"], [1, "blue"]], "%{z:.3f}"
                        elif tm == 'バットスピード (km/h)':
                            mid_val, c_scale = 100, [[0, "blue"], [0.5, "white"], [1, "red"]]
                        elif tm in ['ExitVelocity', '打球スピード (km/h)']:
                            mid_val, c_scale = 140, [[0, "blue"], [0.5, "white"], [1, "red"]]
                        elif tm == 'LaunchAngle':
                            mid_val, c_scale = 7, [[0, "blue"], [0.5, "white"], [1, "red"]]

                        # --- 1. コース別分析図 ---
                        st.subheader(f"🔢 {tm}：{start_date} ～ {end_date} の分析")
                        x_labels = ['極外','外','中','内','極内'] if is_lefty else ['極内','内','中','外','極外']
                        y_labels = ['極高','高','中','低','極低']

                        fig_hm = go.Figure()
                        fig_hm.add_trace(go.Heatmap(
                            z=np.flipud(final_grid), x=x_labels, y=y_labels,
                            colorscale=c_scale, 
                            texttemplate=None if "ExitDirection" in tm else txt_fmt,
                            textfont={"size": 16, "color": "black", "family": "Arial Black"},
                            showscale=True, zmid=mid_val,
                            xgap=2, ygap=2, opacity=0.9
                        ))

                        if bg_img:
                            fig_hm.add_layout_image(
                                dict(
                                    source=bg_img, xref="x", yref="y",
                                    x=-2.2, y=6.2, sizex=9.5, sizey=9.5,
                                    sizing="stretch", opacity=1.0, layer="below"
                                )
                            )

                        if "ExitDirection" in tm:
                            for r in range(5):
                                for c in range(5):
                                    if counts[r, c] > 0:
                                        fig_hm.add_annotation(
                                            x=x_labels[c], y=y_labels[4-r], text="↑", showarrow=False,
                                            font=dict(size=40, color="black"), textangle=final_grid[r, c]
                                        )

                        fig_hm.add_shape(type="rect", x0=0.5, y0=0.5, x1=3.5, y1=3.5, line=dict(color="Cyan", width=5))
                        fig_hm.update_xaxes(showgrid=False, range=[-1.5, 5.5])
                        fig_hm.update_yaxes(showgrid=False, range=[-1.5, 5.5], scaleanchor="x", scaleratio=1)
                        fig_hm.update_layout(width=800, height=800, plot_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_hm)

                        # --- 2. 打球分布図 ---
                        st.subheader(f"📍 {tm}：詳細分布")
                        fig_sc = px.scatter(c_df, x=cx, y=cy, color=tm, color_continuous_scale=c_scale, range_x=[-80, 80], range_y=[0, 160])
                        if mid_val: fig_sc.update_layout(coloraxis_cmid=mid_val)
                        fig_sc.add_shape(type="rect", x0=-28.8, y0=45, x1=28.8, y1=110, line=dict(color="Black", width=3))
                        fig_sc.update_layout(width=700, height=700, plot_bgcolor='white')
                        st.plotly_chart(fig_sc)
                else:
                    st.info("カレンダーで開始日と終了日の両方を選択してください。")

    elif mode == "データ登録":
        st.header("📥 データ登録")
        pn = st.selectbox("選手", PLAYERS)
        f = st.file_uploader("CSVアップロード", type=["csv"])
        if st.button("保存") and f:
            new = pd.read_csv(f)
            new['Player Name'], new['DateTime'] = pn, pd.to_datetime(datetime.date.today())
            pd.concat([db_df, new], ignore_index=True).drop_duplicates().to_csv(DB, index=False)
            st.success("完了")
