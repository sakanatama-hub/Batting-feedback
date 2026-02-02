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

def get_color(val, metric_name):
    if val == 0: return "rgba(255, 255, 255, 0.1)", "white"
    base, sensitivity = 105, 30
    diff = val - base
    intensity = min(abs(diff) / sensitivity, 1.0)
    if diff > 0:
        color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)"
    else:
        color = f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
    return color, "white"

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
                
                # 数値列だけを抽出（StrikeZoneX/Yは除外して指標のみにする）
                metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "StrikeZone" not in c]
                with c3: target_metric = st.selectbox("分析指標", metrics)

                # --- 1. コース別平均（ヒートマップ） ---
                st.subheader(f"📊 {target_metric}：コース別平均")
                
                # 座標から計算して集計
                vdf['zx'] = vdf['StrikeZoneX'].apply(lambda x: 1 if x < -11.6 else (2 if x < 11.6 else 3))
                vdf['zy'] = vdf['StrikeZoneY'].apply(lambda y: 3 if y > 93.3 else (2 if y > 66.6 else 1))
                
                zones = []
                for y_idx in [3, 2, 1]:
                    row_data = []
                    for x_idx in [1, 2, 3]:
                        logic_x = x_idx if hand == "右" else (4 - x_idx)
                        avg_val = vdf[(vdf['zx'] == logic_x) & (vdf['zy'] == y_idx)][target_metric].mean()
                        row_data.append(avg_val if pd.notnull(avg_val) else 0)
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
                st.plotly_chart(fig_heat, use_container_width=True)

                # --- 2. インパクトポイント（シルエット版） ---
                st.subheader(f"📍 {target_metric}：インパクトポイント")
                fig_point = go.Figure()
                fig_point.add_shape(type="rect", x0=-150, x1=150, y0=-50, y1=200, fillcolor="#8B4513", line_width=0, layer="below")
                fig_point.add_shape(type="path", path="M -30 15 L 30 15 L 30 8 L 0 0 L -30 8 Z", fillcolor="white", line=dict(color="#444", width=2))
                
                sc, y_off = 1.1, 40
                sx_min, sx_max, sy_min, sy_max = -35, 35, 35, 115
                b_col = "rgba(220, 220, 220, 0.4)"; m = 1 if hand == "左" else -1; offset = 85 * m

                # シルエット
                fig_point.add_shape(type="path", path=f"M {offset-15*m} 20 L {offset-5*m} 70 L {offset+15*m} 70 L {offset+25*m} 20", line=dict(color=b_col, width=15))
                fig_point.add_shape(type="path", path=f"M {offset-10*m} 70 Q {offset} 100, {offset-5*m} 140 L {offset+20*m} 140 Q {offset+25*m} 100, {offset+15*m} 70 Z", fillcolor=b_col, line_width=0)
                fig_point.add_shape(type="circle", x0=offset-12*m if hand=="右" else offset+2*m, x1=offset+8*m if hand=="右" else offset-18*m, y0=145, y1=175, fillcolor=b_col, line_width=0)
                fig_point.add_shape(type="path", path=f"M {offset-5*m} 135 L {offset-30*m} 150 L {offset-25*m} 180", line=dict(color=b_col, width=8))
                fig_point.add_shape(type="line", x0=offset-25*m, y0=180, x1=offset-10*m, y1=230, line=dict(color="rgba(180, 180, 180, 0.5)", width=5))
                
                # ストライクゾーン枠
                fig_point.add_shape(type="rect", x0=sx_min, x1=sx_max, y0=sy_min, y1=sy_max, line=dict(color="rgba(255,255,255,0.8)", width=4))
                
                # プロット点
                valid_data = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY'])
                for _, row in valid_data.iterrows():
                    val = row[target_metric]
                    dot_color, _ = get_color(val, target_metric)
                    fig_point.add_trace(go.Scatter(x=[row['StrikeZoneX'] * sc], y=[row['StrikeZoneY'] + y_off], mode='markers', marker=dict(size=12, color=dot_color, line=dict(width=1, color="white")), text=f"{val}", hoverinfo='text', showlegend=False))
                
                fig_point.update_layout(width=800, height=550, xaxis=dict(range=[-150, 150], visible=False), yaxis=dict(range=[-20, 240], visible=False), margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_point, use_container_width=True)
        else:
            st.warning("データがありません。")

    with tab2:
        st.title("📝 データ登録")
        with st.form("input_form"):
            c1, c2, c3 = st.columns(3)
            with c1: f_player = st.selectbox("選手", PLAYERS)
            with c2: f_date = st.date_input("日付")
            with c3: f_time = st.time_input("時間")
            f_speed = st.number_input("スイング速度", value=110.0)
            f_x = st.number_input("コースX (-35〜35)", value=0.0)
            f_y = st.number_input("コースY (35〜115)", value=75.0)
            
            if st.form_submit_button("保存"):
                new_entry = {
                    "Player Name": f_player, "DateTime": f"{f_date} {f_time}",
                    "Swing Speed": f_speed, "StrikeZoneX": f_x, "StrikeZoneY": f_y 
                }
                new_df = pd.concat([db_df, pd.DataFrame([new_entry])], ignore_index=True)
                if save_to_github(new_df):
                    st.success("保存完了"); st.rerun()
