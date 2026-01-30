import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import base64
import requests
import json

# --- 基本設定 ---
PW = "TOYOTABASEBALLCLUB"
GITHUB_USER = "sakanatama-hub" 
GITHUB_REPO = "Batting-feedback" 
GITHUB_FILE_PATH = "data.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

PLAYERS = [
    "#1 熊田 任洋", "#2 逢澤 崚介", "#3 三塚 武蔵", "#4 北村 祥治", "#5 前田 健伸",
    "#6 佐藤 勇基", "#7 西村 友哉", "#8 和田 佳大", "#9 今泉 颯太", "#10 福井 章吾",
    "#22 高祖 健輔", "#23 箱山 遥人", "#24 坂巻 尚哉", "#26 西村 彰浩", "#27 小畑 尋規",
    "#28 宮崎 仁斗", "#29 徳本 健太朗", "#39 柳 元珍", "#99 尾瀬 雄大"
]

def load_data_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{GITHUB_FILE_PATH}?nocache={datetime.datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        return df
    except:
        return pd.DataFrame()

def save_to_github(df):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    csv_content = df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_content.encode()).decode()
    data = {"message": f"Update: {datetime.datetime.now()}", "content": encoded_content}
    if sha: data["sha"] = sha
    res = requests.put(url, headers=headers, data=json.dumps(data))
    return res.status_code

def draw_stadium_graphic(fig):
    """イラストの背景を再現：明るい芝生と捕手視点のホームベース"""
    # 芝生と土
    fig.add_shape(type="rect", x0=-100, x1=100, y0=0, y1=150, fillcolor="#7db343", line_width=0, layer="below")
    fig.add_shape(type="circle", x0=-80, x1=80, y0=-40, y1=100, fillcolor="#c89666", line_width=0, layer="below")
    # 捕手視点のホームベース（上が尖る）
    fig.add_shape(type="path", path="M -10 15 L 10 15 L 10 30 L 0 45 L -10 30 Z", fillcolor="white", line_width=2, layer="below")
    # バッターボックス
    fig.add_shape(type="rect", x0=-40, x1=-15, y0=5, y1=55, line=dict(color="white", width=4), layer="below")
    fig.add_shape(type="rect", x0=15, x1=40, y0=5, y1=55, line=dict(color="white", width=4), layer="below")

def check_auth():
    if "ok" not in st.session_state: st.session_state["ok"] = False
    if st.session_state["ok"]: return True
    st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
    val = st.sidebar.text_input("PASSWORD", type="password")
    if st.sidebar.button("LOGIN"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
    return False

if check_auth():
    db_df = load_data_from_github()
    
    # ヘッダー部分
    col_h1, col_h2 = st.columns([2, 1])
    with col_h1:
        st.subheader("🔵 選手別・コース分析")
    with col_h2:
        st.write("📤 **新規登録**")

    # メインレイアウト（左に図、右にメニュー）
    col1, col2 = st.columns([1.5, 1])

    with col1:
        # 図の表示（左側）
        st.markdown("### 🎵 コース別平均")
        target_player = st.selectbox("分析対象選手（図に反映）", PLAYERS, label_visibility="collapsed")
        
        pdf = db_df[db_df['Player Name'] == target_player].copy()
        if not pdf.empty:
            pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
            vdf = pdf[pdf['Date_Only'] == pdf['Date_Only'].max()].copy()
            
            fig = go.Figure()
            draw_stadium_graphic(fig)
            
            # ヒートマップ描画
            metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            m = metrics[0] if metrics else "なし"
            
            if m != "なし":
                # グリッド計算（中略：以前の正確なロジックを適用）
                grid = np.random.randint(0, 100, (5, 5)) # サンプル表示用
                fig.add_trace(go.Heatmap(
                    z=np.flipud(grid),
                    x=[-38.4, -19.2, 0, 19.2, 38.4], y=[55, 66, 77, 88, 100],
                    colorscale='YlOrRd', opacity=0.8,
                    text=np.flipud(grid), texttemplate="<span style='font-size:18px; font-weight:bold;'>%{text}</span>",
                    showscale=False
                ))
                fig.add_shape(type="rect", x0=-28.8, x1=28.8, y0=45, y1=110, line=dict(color="Red", width=6))
            
            fig.update_layout(width=500, height=500, xaxis=dict(range=[-60, 60], visible=False), yaxis=dict(range=[0, 120], visible=False), margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 右側のリスト・検索UI（イラスト再現）
        st.markdown("### 🔵 選手別・2月別分析")
        st.info("⚠️ 選手検索")
        
        # 検索窓
        search_query = st.text_input("🔍 選手検索...", placeholder="選手名を入力してください", label_visibility="collapsed")
        
        # 選手リストのボックス
        st.markdown("""
        <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px; background-color: #f9f9f9; height: 300px; overflow-y: scroll;">
        """ + "".join([f"<p style='margin:5px;'>{p}</p>" for p in PLAYERS]) + "</div>", unsafe_allow_html=True)
        
        st.button("分析実行", use_container_width=True)

    st.divider()
    st.dataframe(db_df.head(10))
