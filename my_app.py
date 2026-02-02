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

def save_to_github(new_df):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    csv_content = new_df.to_csv(index=False)
    b64_content = base64.b64encode(csv_content.encode()).decode()
    data = {"message": "Update batting data", "content": b64_content}
    if sha: data["sha"] = sha
    put_res = requests.put(url, headers=headers, json=data)
    return put_res.status_code in [200, 201]

# --- UI設定 ---
st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")

# CSSでプロ仕様のダークモードを強制
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #00FFCC !important; font-family: 'Segoe UI', sans-serif; font-weight: 800; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; color: #888; border: none; }
    .stTabs [aria-selected="true"] { color: #00FFCC !important; border-bottom: 2px solid #00FFCC !important; }
    </style>
    """, unsafe_allow_html=True)

if "ok" not in st.session_state: st.session_state["ok"] = False

if not st.session_state["ok"]:
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("PASSWORD", type="password")
    if st.button("LOGIN"):
        if val == PW: st.session_state["ok"] = True; st.rerun()
else:
    db_df = load_data_from_github()
    tab1, tab2 = st.tabs(["📊 データ分析", "📝 データ登録"])

    with tab1:
        st.title("🔵 BATTING ANALYTICS")
        if not db_df.empty:
            c1, c2, c3 = st.columns([2, 2, 3])
            with c1: target_player = st.selectbox("PLAYER", PLAYERS)
            hand = PLAYER_HANDS[target_player]
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            
            if not pdf.empty:
                pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
                with c2: target_date = st.selectbox("DATE", sorted(pdf['Date_Only'].unique(), reverse=True))
                vdf = pdf[pdf['Date_Only'] == target_date].copy()
                
                # 数値列の抽出（エラー回避：Zone, StrikeZoneという文字列列を完全に除外）
                metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
                with c3: target_metric = st.selectbox("METRIC", metrics)

                # --- 1. コース別平均（ヒートマップ） ---
                st.subheader(f"📊 {target_metric} : HEATMAP")
                
                zones = []
                # 実際のCSV列名が 'StrikeZone' であることを確認して処理
                target_col = 'StrikeZone'
                
                for y in range(3, 0, -1):
                    row_data = []
                    for x in range(1, 4):
                        logic_x = x if hand == "右" else (4 - x)
                        # データの平均値を計算（データがない場合は0に置き換え）
                        val = vdf[vdf[target_col] == f"Zone{logic_x}_{y}"][target_metric].mean()
                        row_data.append(float(val) if pd.notnull(val) else 0.0)
                    zones.append(row_data)

                # デザイン重視のヒートマップ描画
                fig_heat = go.Figure(data=go.Heatmap(
                    z=zones,
                    x=['INSIDE', 'MIDDLE', 'OUTSIDE'] if hand == "右" else ['OUTSIDE', 'MIDDLE', 'INSIDE'],
                    y=['HIGH', 'CENTER', 'LOW'],
                    colorscale=[[0, '#121212'], [0.5, '#0055ff'], [1, '#00ffcc']], # 寒色系のテックカラー
                    text=[[f"{v:.1f}" if v != 0 else "" for v in row] for row in zones],
                    texttemplate="%{text}",
                    textfont={"size": 24, "family": "Arial Black", "color": "white"},
                    showscale=True,
                    xgap=3, ygap=3 # グリッドの隙間でプロ感を演出
                ))
                
                fig_heat.update_layout(
                    width=600, height=450,
                    xaxis=dict(side="top", tickfont=dict(color="#00FFCC")),
                    yaxis=dict(autorange="reversed", tickfont=dict(color="#00FFCC")),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=40, r=40, t=80, b=40)
                )
                st.plotly_chart(fig_heat, use_container_width=True)

                # --- 2. インパクトポイント（シルエット版） ---
                st.subheader(f"📍 {target_metric} : IMPACT LOCATIONS")
                fig_point = go.Figure()
                
                # グラウンド
                fig_point.add_shape(type="rect", x0=-150, x1=150, y0=-50, y1=200, fillcolor="#0a0a0a", line_width=0, layer="below")
                # ホームベース
                fig_point.add_shape(type="path", path="M -25 10 L 25 10 L 25 5 L 0 0 L -25 5 Z", fillcolor="white", line=dict(color="#444", width=1))
                
                m = 1 if hand == "左" else -1
                offset = 80 * m
                
                # 抽象的なシルエット（よりシンプルにして「ダサさ」を排除）
                fig_point.add_shape(type="rect", x0=offset-10, x1=offset+10, y0=20, y1=140, fillcolor="rgba(255,255,255,0.15)", line_width=0) # 体
                fig_point.add_shape(type="circle", x0=offset-10, x1=offset+10, y0=145, y1=175, fillcolor="rgba(255,255,255,0.15)", line_width=0) # 頭
                
                # ストライクゾーン（ネオン枠）
                fig_point.add_shape(type="rect", x0=-35, x1=35, y0=40, y1=120, line=dict(color="#00FFCC", width=3))
                
                # プロット点
                valid_data = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                fig_point.add_trace(go.Scatter(
                    x=valid_data['StrikeZoneX'] * 1.2, 
                    y=valid_data['StrikeZoneY'] + 40, 
                    mode='markers', 
                    marker=dict(size=14, color=valid_data[target_metric], colorscale="Viridis", 
                                line=dict(width=1.5, color="white"), showscale=False),
                    text=valid_data[target_metric], hoverinfo='text'
                ))
                
                fig_point.update_layout(width=800, height=500, xaxis=dict(range=[-150, 150], visible=False), 
                                        yaxis=dict(range=[-20, 220], visible=False), 
                                        margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_point, use_container_width=True)
        else:
            st.warning("No data available.")

    with tab2:
        st.title("📝 DATA ENTRY")
        with st.form("input_form"):
            c1, c2, c3 = st.columns(3)
            with c1: f_player = st.selectbox("PLAYER", PLAYERS)
            with c2: f_date = st.date_input("DATE")
            with c3: f_time = st.time_input("TIME")
            
            f_speed = st.number_input("SWING SPEED (km/h)", value=110.0)
            f_zone = st.selectbox("STRIKE ZONE", [f"Zone{x}_{y}" for y in range(3, 0, -1) for x in range(1, 4)])
            
            if st.form_submit_button("SUBMIT"):
                # 登録処理（略）
                pass
