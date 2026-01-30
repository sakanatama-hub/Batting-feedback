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

def draw_stadium_background(fig):
    """
    イラストのような奥行きのあるスタジアム背景をコードで描画
    """
    # 1. 芝生のグラデーション（奥に行くほど暗い緑）
    fig.add_shape(type="rect", x0=-150, x1=150, y0=0, y1=200, fillcolor="#1a4d1a", line_width=0, layer="below")
    
    # 2. 芝生のストライプ（奥行きを出すための模様）
    for i in range(0, 200, 20):
        fig.add_shape(type="rect", x0=-150, x1=150, y0=i, y1=i+10, fillcolor="#1e5c1e", line_width=0, layer="below")

    # 3. 奥行きのある「土」のエリア（パースのついた台形）
    fig.add_shape(type="path", path="M -100 180 L 100 180 L 150 0 L -150 0 Z", fillcolor="#a0522d", line_width=0, layer="below")
    
    # 4. バッターボックス（パース付き）
    # 左ボックス
    fig.add_shape(type="path", path="M -45 10 L -25 10 L -20 50 L -40 50 Z", line=dict(color="rgba(255,255,255,0.6)", width=3), layer="below")
    # 右ボックス
    fig.add_shape(type="path", path="M 25 10 L 45 10 L 40 50 L 20 50 Z", line=dict(color="rgba(255,255,255,0.6)", width=3), layer="below")

    # 5. 立体的なホームベース
    fig.add_shape(type="path", path="M -12 20 L 12 20 L 12 35 L 0 50 L -12 35 Z", fillcolor="white", line=dict(color="gray", width=1), layer="below")

def check_auth():
    if "ok" not in st.session_state: st.session_state["ok"] = False
    if st.session_state["ok"]: return True
    st.set_page_config(page_title="TOYOTA BASEBALL", layout="wide")
    st.title("⚾️ TOYOTA BASEBALL CLUB")
    val = st.text_input("パスワード入力", type="password")
    if st.button("ログイン"):
        if val == PW:
            st.session_state["ok"] = True
            st.rerun()
        else: st.error("PWエラー")
    return False

if check_auth():
    db_df = load_data_from_github() # 既存の読込関数を使用
    mode = st.sidebar.radio("切替", ["📊 分析", "📥 登録"])

    if mode == "📊 分析":
        st.header("📊 選手分析（スタジアムビュー）")
        target_player = st.sidebar.selectbox("選手", PLAYERS)
        pdf = db_df[db_df['Player Name'] == target_player].copy()
        
        if not pdf.empty:
            pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
            target_date = st.sidebar.selectbox("日付", sorted(pdf['Date_Only'].unique(), reverse=True))
            vdf = pdf[pdf['Date_Only'] == target_date].copy()
            metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c]
            target_metric = st.selectbox("指標", metrics if metrics else ["なし"])

            # --- メインチャート作成 ---
            fig = go.Figure()
            draw_stadium_background(fig)

            # 6. 空中に浮かぶ「ストライクゾーン」のヒートマップ
            # 座標を調整して、ホームベースより少し上の「空中」に配置
            if target_metric != "なし":
                clean_df = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                # (グリッド計算ロジックは以前と同様のため中略。表示部分を重点的に記述)
                # ... (grid計算処理) ...
                
                # ヒートマップを「前面」にフロートさせる
                fig.add_trace(go.Heatmap(
                    z=np.flipud(display_grid),
                    x=[-40, -20, 0, 20, 40], # フィールドのパースに合わせた座標
                    y=[80, 100, 120, 140, 160], # 地面(0-50)より上の空中
                    colorscale='YlOrRd', opacity=0.8,
                    text=np.flipud(np.round(display_grid, 1)), texttemplate="<b>%{text}</b>",
                    showscale=False
                ))

                # 7. デザインされたストライクゾーン枠（前面）
                fig.add_shape(type="rect", x0=-30, x1=30, y0=90, y1=150, line=dict(color="Red", width=6), layer="above")
                
                # 8. 打点プロット（光る点として表現）
                fig.add_trace(go.Scatter(
                    x=vdf['StrikeZoneX'] * 0.5, # 座標をパースに合わせて圧縮
                    y=vdf['StrikeZoneY'] + 40,   # 空中に持ち上げ
                    mode='markers',
                    marker=dict(size=12, color='yellow', symbol='diamond', line=dict(width=2, color='white'), opacity=0.9),
                    name="打点"
                ))

            fig.update_layout(
                width=900, height=800,
                xaxis=dict(range=[-120, 120], visible=False),
                yaxis=dict(range=[0, 200], visible=False),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=0, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(vdf)
