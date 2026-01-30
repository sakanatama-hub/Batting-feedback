import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import base64
import requests
import json
import os

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

# --- データ処理関数 ---
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

# --- グラフィック描画関数 ---
def draw_stadium_background(fig):
    """イラストのような奥行きのあるスタジアム背景をコードで描画"""
    # 1. 芝生のグラデーション
    fig.add_shape(type="rect", x0=-150, x1=150, y0=0, y1=200, fillcolor="#1a4d1a", line_width=0, layer="below")
    # 2. 芝生のストライプ
    for i in range(0, 200, 20):
        fig.add_shape(type="rect", x0=-150, x1=150, y0=i, y1=i+10, fillcolor="#1e5c1e", line_width=0, layer="below")
    # 3. 奥行きのある「土」のエリア（パース付き）
    fig.add_shape(type="path", path="M -110 180 L 110 180 L 160 0 L -160 0 Z", fillcolor="#a0522d", line_width=0, layer="below")
    # 4. バッターボックス（パース付き）
    fig.add_shape(type="path", path="M -45 10 L -25 10 L -20 50 L -40 50 Z", line=dict(color="rgba(255,255,255,0.7)", width=3), layer="below")
    fig.add_shape(type="path", path="M 25 10 L 45 10 L 40 50 L 20 50 Z", line=dict(color="rgba(255,255,255,0.7)", width=3), layer="below")
    # 5. 立体的なホームベース
    fig.add_shape(type="path", path="M -12 20 L 12 20 L 12 35 L 0 50 L -12 35 Z", fillcolor="white", line=dict(color="gray", width=1), layer="below")

# --- 認証機能 ---
def check_auth():
    if "ok" not in st.session_state: st.session_state["ok"] = False
    if st.session_state["ok"]: return True
    st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
        else: st.error("パスワードが正しくありません")
    return False

# --- メインロジック ---
if check_auth():
    db_df = load_data_from_github()
    mode = st.sidebar.radio("機能メニュー", ["📊 選手分析", "📥 練習データ登録"])

    if mode == "📊 選手分析":
        st.header("📊 スタジアム・パフォーマンス分析")
        if db_df.empty:
            st.warning("データが見つかりません。")
        else:
            target_player = st.sidebar.selectbox("選手を選択", PLAYERS)
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            
            if not pdf.empty:
                pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
                target_date = st.sidebar.selectbox("日付を選択", sorted(pdf['Date_Only'].unique(), reverse=True))
                vdf = pdf[pdf['Date_Only'] == target_date].copy()
                
                metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
                target_metric = st.selectbox("分析する数値指標", metrics if metrics else ["データなし"])

                # --- チャート作成 ---
                fig = go.Figure()
                draw_stadium_background(fig)

                if target_metric != "データなし":
                    # ヒートマップ用グリッド計算
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

                    # 前面に浮かぶヒートマップ
                    fig.add_trace(go.Heatmap(
                        z=np.flipud(display_grid),
                        x=[-40, -20, 0, 20, 40],
                        y=[90, 105, 120, 135, 150],
                        colorscale='YlOrRd', opacity=0.8,
                        text=np.flipud(np.round(display_grid, 1)), texttemplate="<b>%{text}</b>",
                        showscale=False
                    ))

                    # 太いストライクゾーン枠
                    fig.add_shape(type="rect", x0=-25, x1=25, y0=100, y1=140, line=dict(color="Red", width=6), layer="above")
                    
                    # 打点プロット（光るダイヤモンド）
                    fig.add_trace(go.Scatter(
                        x=vdf['StrikeZoneX'] * 0.45,
                        y=vdf['StrikeZoneY'] + 50,
                        mode='markers',
                        marker=dict(size=14, color='cyan', symbol='diamond', line=dict(width=2, color='white'), opacity=0.9),
                        name="打球"
                    ))

                fig.update_layout(
                    width=900, height=800,
                    xaxis=dict(range=[-120, 120], visible=False),
                    yaxis=dict(range=[0, 200], visible=False),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(vdf)

    elif mode == "📥 練習データ登録":
        st.header("📥 新規データ登録")
        target_player = st.selectbox("登録選手", PLAYERS)
        target_date = st.date_input("練習日", datetime.date.today())
        uploaded_file = st.file_uploader("ファイルをアップロード (Excel/CSV)", type=["csv", "xlsx"])
        
        if st.button("GitHubへデータを送信"):
            if uploaded_file:
                try:
                    df_up = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                    df_up['Player Name'] = target_player
                    df_up['DateTime'] = datetime.datetime.combine(target_date, datetime.datetime.now().time())
                    new_db = pd.concat([db_df, df_up], ignore_index=True).replace({np.nan: ""})
                    if save_to_github(new_db) in [200, 201]:
                        st.success("GitHubへの保存が完了しました！")
                        st.cache_data.clear()
                    else: st.error("保存に失敗しました。トークンを確認してください。")
                except Exception as e: st.error(f"エラーが発生しました: {e}")
