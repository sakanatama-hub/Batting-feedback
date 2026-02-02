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

# --- UI ---
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

    with tab1:
        st.title("🔵 選手別打撃分析")
        if not db_df.empty:
            c1, c2, c3 = st.columns([2, 2, 3])
            with c1: target_player = st.selectbox("選手を選択", PLAYERS)
            hand = PLAYER_HANDS[target_player]
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            
            if not pdf.empty:
                pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
                with c2: target_date = st.selectbox("日付を選択", sorted(pdf['Date_Only'].unique(), reverse=True))
                vdf = pdf[pdf['Date_Only'] == target_date].copy()
                metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
                with c3: target_metric = st.selectbox("分析指標", metrics)

                # --- 1. コース別平均（ヒートマップ）---
                st.subheader(f"📊 {target_metric}：コース別平均")
                
                zones = []
                for y in range(3, 0, -1):
                    row_data = []
                    for x in range(1, 4):
                        logic_x = x if hand == "右" else (4 - x)
                        # 列名を 'StrikeZone' に修正
                        val = vdf[vdf['StrikeZone'] == f"Zone{logic_x}_{y}"][target_metric].mean()
                        row_data.append(val if pd.notnull(val) else 0)
                    zones.append(row_data)

                fig_heat = go.Figure(data=go.Heatmap(
                    z=zones,
                    x=['内角', '中', '外角'] if hand == "右" else ['外角', '中', '内角'],
                    y=['高め', '真ん中', '低め'],
                    colorscale='Viridis',
                    text=[[f"{v:.1f}" if v != 0 else "" for v in row] for row in zones],
                    texttemplate="%{text}",
                    showscale=True
                ))
                fig_heat.update_layout(width=500, height=450, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_heat)

                # --- 2. インパクトポイント（シンプル版） ---
                st.subheader(f"📍 {target_metric}：インパクトポイント")
                fig_point = go.Figure()
                
                # ホームベースと枠
                fig_point.add_shape(type="rect", x0=-35, x1=35, y0=40, y1=120, line=dict(color="black", width=2))
                
                valid_data = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                fig_point.add_trace(go.Scatter(
                    x=valid_data['StrikeZoneX'], 
                    y=valid_data['StrikeZoneY'], 
                    mode='markers', 
                    marker=dict(size=12, color=valid_data[target_metric], colorscale='Viridis', showscale=True),
                    text=valid_data[target_metric], hoverinfo='text'
                ))
                
                fig_point.update_layout(width=600, height=500, xaxis=dict(range=[-100, 100]), yaxis=dict(range=[-20, 200]))
                st.plotly_chart(fig_point)

    with tab2:
        st.title("📝 データ登録")
        with st.form("input_form"):
            c1, c2, c3 = st.columns(3)
            with c1: f_player = st.selectbox("選手", PLAYERS)
            with c2: f_date = st.date_input("日付")
            with c3: f_time = st.time_input("時間")
            f_speed = st.number_input("スイング速度", value=110.0)
            f_zone = st.selectbox("ゾーン", [f"Zone{x}_{y}" for y in range(3, 0, -1) for x in range(1, 4)])
            
            if st.form_submit_button("保存"):
                new_entry = {
                    "Player Name": f_player, "DateTime": f"{f_date} {f_time}",
                    "Swing Speed": f_speed, "StrikeZone": f_zone,
                    "StrikeZoneX": 0, "StrikeZoneY": 75 
                }
                new_df = pd.concat([db_df, pd.DataFrame([new_entry])], ignore_index=True)
                if save_to_github(new_df):
                    st.success("完了"); st.rerun()
