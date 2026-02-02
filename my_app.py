import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import requests
import base64

# --- 基本設定 ---
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

def get_color(val, metric_name):
    if val == 0 or pd.isna(val): return "rgba(255, 255, 255, 0.1)", "white"
    if "スイング時間" in metric_name:
        base, sensitivity = 0.15, 0.05
    elif "アッパースイング度" in metric_name:
        base, sensitivity = 10.5, 15
    else:
        base, sensitivity = 105, 30
    diff = val - base
    intensity = min(abs(diff) / sensitivity, 1.0)
    if "スイング時間" in metric_name:
        color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff < 0 else f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
    else:
        color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff > 0 else f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
    return color, ("black" if intensity < 0.4 else "white")

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
    # タブ名を変更し、比較分析を追加
    tab1, tab2, tab3 = st.tabs(["👤 個人分析", "⚔️ 比較分析", "📝 データ登録"])

    with tab1:
        st.title("🔵 個人別打撃分析")
        if not db_df.empty:
            c1, c2, c3 = st.columns([2, 3, 3])
            with c1: target_player = st.selectbox("選手を選択", PLAYERS, key="p_tab1")
            hand = PLAYER_HANDS[target_player]
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            if not pdf.empty:
                pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
                with c2:
                    date_range = st.date_input("分析期間を選択", value=(pdf['Date_Only'].min(), pdf['Date_Only'].max()), key="range_tab1")
                
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_date, end_date = date_range
                    vdf = pdf[(pdf['Date_Only'] >= start_date) & (pdf['Date_Only'] <= end_date)].copy()
                else:
                    vdf = pd.DataFrame()

                metrics = [c for c in pdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
                with c3: target_metric = st.selectbox("分析指標", metrics if metrics else ["データなし"], key="m_tab1")

                if not vdf.empty:
                    # コース別平均（野球場デザイン）
                    st.subheader(f"📊 {target_metric}：期間内平均")
                    fig_heat = go.Figure()
                    fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
                    L_x, L_y, R_x, R_y = 125, 140, -125, 140
                    fig_heat.add_shape(type="path", path=f"M {R_x} {R_y} L -450 600 L 450 600 L {L_x} {L_y} Z", fillcolor="#8B4513", line_width=0, layer="below")
                    fig_heat.add_shape(type="circle", x0=-120, x1=120, y0=-50, y1=160, fillcolor="#8B4513", line_width=0, layer="below")
                    fig_heat.add_shape(type="path", path="M -25 70 L 25 70 L 25 45 L 0 5 L -25 45 Z", fillcolor="white", line=dict(color="#444", width=3), layer="below")
                    box_style = dict(fillcolor="rgba(255, 255, 255, 0.1)", line=dict(color="rgba(255,255,255,0.8)", width=4), layer="below")
                    fig_heat.add_shape(type="path", path="M 130 20 L 65 20 L 60 140 L 125 140 Z", **box_style)
                    fig_heat.add_shape(type="path", path="M -130 20 L -65 20 L -60 140 L -125 140 Z", **box_style)
                    
                    grid_side = 55
                    z_x_start, z_y_start = -(grid_side * 2.5), 180 
                    def get_grid_pos(x, y):
                        r = 0 if y > 110 else 1 if y > 88.2 else 2 if y > 66.6 else 3 if y > 45 else 4
                        c = 0 if x < -28.8 else 1 if x < -9.6 else 2 if x <= 9.6 else 3 if x <= 28.8 else 4
                        return r, c
                    grid_val = np.zeros((5, 5)); grid_count = np.zeros((5, 5))
                    for _, row in vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric]).iterrows():
                        r, c = get_grid_pos(row['StrikeZoneX'], row['StrikeZoneY'])
                        grid_val[r, c] += row[target_metric]; grid_count[r, c] += 1
                    display_grid = np.where(grid_count > 0, grid_val / grid_count, 0)
                    for r in range(5):
                        for c in range(5):
                            logic_c = c if hand == "右" else (4 - c)
                            x0, x1 = z_x_start + c * grid_side, z_x_start + (c+1) * grid_side
                            y0, y1 = z_y_start + (4-r) * grid_side, z_y_start + (5-r) * grid_side
                            val = display_grid[r, logic_c]
                            color, f_color = get_color(val, target_metric)
                            fig_heat.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color, line=dict(color="#222", width=1.5))
                            if val > 0:
                                txt = f"{val:.3f}" if "時間" in target_metric else f"{val:.1f}"
                                fig_heat.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=txt, showarrow=False, font=dict(size=18, color=f_color, weight="bold"))
                    
                    fig_heat.add_shape(type="rect", x0=z_x_start+grid_side, x1=z_x_start+4*grid_side, y0=z_y_start+grid_side, y1=z_y_start+4*grid_side, line=dict(color="#ff2222", width=6))
                    fig_heat.update_layout(width=900, height=650, xaxis=dict(range=[-320, 320], visible=False), yaxis=dict(range=[-40, 520], visible=False), margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_heat, use_container_width=True)

    with tab2:
        st.title("⚔️ 選手間比較分析")
        if not db_df.empty:
            all_metrics = [c for c in db_df.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            comp_metric = st.selectbox("比較する指標を選択", all_metrics, key="m_tab2")
            
            # 選手ごとの平均値を計算
            comp_df = db_df.groupby('Player Name')[comp_metric].agg(['mean', 'count']).reset_index()
            comp_df.columns = ['選手名', '平均値', 'スイング数']
            comp_df = comp_df.sort_values(by='平均値', ascending=("スイング時間" not in comp_metric))

            # 横棒グラフでランキング表示
            fig_comp = go.Figure(go.Bar(
                x=comp_df['平均値'],
                y=comp_df['選手名'],
                orientation='h',
                marker=dict(color='royalblue'),
                text=comp_df['平均値'].round(3),
                textposition='auto'
            ))
            fig_comp.update_layout(title=f"{comp_metric} チームランキング", height=600, xaxis_title=comp_metric, yaxis_title="選手名")
            st.plotly_chart(fig_comp, use_container_width=True)
            
            st.subheader("📋 詳細データ一覧")
            st.dataframe(comp_df, use_container_width=True)

    with tab3:
        # (登録タブの内容を維持)
        st.title("📝 Excelデータ一括登録")
        with st.expander("登録設定", expanded=True):
            col1, col2 = st.columns(2)
            with col1: reg_player = st.selectbox("登録する選手を選択", PLAYERS, key="reg_p_tab3")
            with col2: reg_date = st.date_input("登録する日付を選択", datetime.date.today(), key="reg_d_tab3")
        uploaded_file = st.file_uploader("Excelファイルをアップロード (.xlsx)", type=["xlsx"])
        if uploaded_file is not None:
            try:
                input_df = pd.read_excel(uploaded_file)
                if st.button("GitHubへ保存"):
                    input_df['Player Name'] = reg_player
                    input_df['DateTime'] = reg_date.strftime('%Y-%m-%d')
                    updated_db = pd.concat([db_df, input_df], ignore_index=True)
                    # (save_to_github関数を呼び出し)
                    st.success("登録完了！")
            except Exception as e:
                st.error(f"エラー: {e}")
