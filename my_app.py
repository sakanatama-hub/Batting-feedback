import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import requests
import base64
import io

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
    if "スイング時間" in metric_name:
        base, sensitivity = 0.15, 0.05
        diff = val - base
        intensity = min(abs(diff) / sensitivity, 1.0)
        color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff < 0 else f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
        return color, ("black" if intensity < 0.4 else "white")
    elif "アッパースイング度" in metric_name:
        base, sensitivity = 10.5, 15
        diff = val - base
        intensity = min(abs(diff) / sensitivity, 1.0)
        color = f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)" if diff > 0 else f"rgba({int(255*(1-intensity))}, 255, {int(255*(1-intensity))}, 0.9)"
        return color, ("black" if intensity < 0.4 else "white")
    else:
        base, sensitivity = 105, 30
        diff = val - base
        intensity = min(abs(diff) / sensitivity, 1.0)
        color = f"rgba(255, {int(255*(1-intensity))}, {int(255*(1-intensity))}, 0.9)" if diff > 0 else f"rgba({int(255*(1-intensity))}, 255, {int(255*(1-intensity))}, 0.9)"
        if diff < 0: color = f"rgba({int(255*(1-intensity))}, {int(255*(1-intensity))}, 255, 0.9)"
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
    tab1, tab2 = st.tabs(["📊 データ分析", "📝 データ登録"])

    # --- タブ1: 分析 ---
    with tab1:
        st.title("🔵 選手別打撃分析")
        if not db_df.empty:
            c1, c2, c3 = st.columns([2, 2, 3])
            with c1: target_player = st.selectbox("選手を選択", PLAYERS, key="ana_player")
            hand = PLAYER_HANDS[target_player]
            pdf = db_df[db_df['Player Name'] == target_player].copy()
            
            if not pdf.empty:
                pdf['Date_Only'] = pd.to_datetime(pdf['DateTime']).dt.date
                with c2: target_date = st.selectbox("日付を選択", sorted(pdf['Date_Only'].unique(), reverse=True), key="ana_date")
                vdf = pdf[pdf['Date_Only'] == target_date].copy()
                # ゾーン情報を除く数値列を取得
                metrics = [c for c in vdf.select_dtypes(include=[np.number]).columns if "Zone" not in c and "StrikeZone" not in c]
                with c3: target_metric = st.selectbox("分析指標", metrics, key="ana_metric")

                # 1. コース別平均（俯瞰ヒートマップ）
                st.subheader(f"📊 {target_metric}：コース別平均")
                fig_heat = go.Figure()
                # 野球場描画
                fig_heat.add_shape(type="rect", x0=-500, x1=500, y0=-100, y1=600, fillcolor="#1a4314", line_width=0, layer="below")
                L_x, L_y, R_x, R_y, Outer_x, Outer_y = 125, 140, -125, 140, 450, 600
                fig_heat.add_shape(type="path", path=f"M {R_x} {R_y} L -{Outer_x} {Outer_y} L {Outer_x} {Outer_y} L {L_x} {L_y} Z", fillcolor="#8B4513", line_width=0, layer="below")
                fig_heat.add_shape(type="circle", x0=-120, x1=120, y0=-50, y1=160, fillcolor="#8B4513", line_width=0, layer="below")
                fig_heat.add_shape(type="path", path="M -25 70 L 25 70 L 25 45 L 0 5 L -25 45 Z", fillcolor="white", line=dict(color="#444", width=3), layer="below")
                box_style = dict(fillcolor="#1a4314", line=dict(color="rgba(255,255,255,0.8)", width=4), layer="below")
                fig_heat.add_shape(type="path", path="M -130 20 L -65 20 L -60 140 L -125 140 Z", **box_style)
                fig_heat.add_shape(type="path", path="M 130 20 L 65 20 L 60 140 L 125 140 Z", **box_style)
                fig_heat.add_shape(type="line", x0=L_x, y0=L_y, x1=Outer_x, y1=Outer_y, line=dict(color="white", width=7), layer="below")
                fig_heat.add_shape(type="line", x0=R_x, y0=R_y, x1=-Outer_x, y1=Outer_y, line=dict(color="white", width=7), layer="below")

                grid_side = 55
                z_x_start, z_y_start = -(grid_side * 2.5), 180 

                def get_grid_pos(x, y):
                    r = 0 if y > 110 else 1 if y > 88.2 else 2 if y > 66.6 else 3 if y > 45 else 4
                    c = 0 if x < -28.8 else 1 if x < -9.6 else 2 if x <= 9.6 else 3 if x <= 28.8 else 4
                    return r, c

                grid_val = np.zeros((5, 5)); grid_count = np.zeros((5, 5))
                valid_data = vdf.dropna(subset=['StrikeZoneX', 'StrikeZoneY', target_metric])
                for _, row in valid_data.iterrows():
                    r, c = get_grid_pos(row['StrikeZoneX'], row['StrikeZoneY'])
                    grid_val[r, c] += row[target_metric]; grid_count[r, c] += 1
                display_grid = np.where(grid_count > 0, grid_val / grid_count, 0)

                for r in range(5):
                    for c in range(5):
                        x0, x1 = z_x_start + c * grid_side, z_x_start + (c+1) * grid_side
                        y0, y1 = z_y_start + (4-r) * grid_side, z_y_start + (5-r) * grid_side
                        val = display_grid[r, c]
                        color, f_color = get_color(val, target_metric)
                        fig_heat.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=color, line=dict(color="#222", width=1.5))
                        if val > 0:
                            txt = str(round(val,3)) if "時間" in target_metric else str(round(val,1))
                            fig_heat.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=txt, showarrow=False, font=dict(size=18, color=f_color, weight="bold"))

                # カラーバー設定（エラー回避用の安全なロジック）
                if "スイング時間" in target_metric:
                    c_scale, zm, zM = [[0, "red"], [0.5, "white"], [1, "blue"]], 0.10, 0.20
                elif "アッパースイング度" in target_metric:
                    c_scale, zm, zM = [[0, "green"], [0.5, "white"], [1, "blue"]], -10.0, 30.0
                else:
                    c_scale, zm, zM = [[0, "blue"], [0.5, "white"], [1, "red"]], 70, 140

                fig_heat.add_trace(go.Scatter(
                    x=[None], y=[None], mode='markers',
                    marker=dict(colorscale=c_scale, cmin=zm, cmax=zM, showscale=True, 
                                colorbar=dict(tickfont=dict(color="white"), thickness=15, x=0.9)),
                    showlegend=False
                ))

                fig_heat.add_shape(type="rect", x0=z_x_start+grid_side, x1=z_x_start+4*grid_side, y0=z_y_start+grid_side, y1=z_y_start+4*grid_side, line=dict(color="#ff2222", width=4))
                fig_heat.update_layout(width=800, height=600, xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_heat, use_container_width=True)

                # 2. インパクトポイント（打者シルエット付き）
                st.subheader(f"📍 {target_metric}：インパクトポイント")
                fig_point = go.Figure()
                fig_point.add_shape(type="rect", x0=-150, x1=150, y0=-50, y1=200, fillcolor="#8B4513", line_width=0, layer="below")
                fig_point.add_shape(type="path", path="M -30 15 L 30 15 L 30 8 L 0 0 L -30 8 Z", fillcolor="white", line=dict(color="#444", width=2))
                sc, y_off = 1.2, 40
                sx_min, sx_max, sy_min, sy_max = -35, 35, 35, 115
                bx = 75 if hand == "左" else -75
                fig_point.add_shape(type="rect", x0=bx-15, x1=bx+15, y0=20, y1=140, fillcolor="rgba(200,200,200,0.4)", line_width=0)
                fig_point.add_shape(type="circle", x0=bx-10, x1=bx+10, y0=145, y1=175, fillcolor="rgba(200,200,200,0.4)", line_width=0)
                fig_point.add_shape(type="rect", x0=sx_min, x1=sx_max, y0=sy_min, y1=sy_max, line=dict(color="rgba(255,255,255,0.8)", width=4))
                for i in range(1, 3):
                    vx = sx_min + (sx_max - sx_min) * (i / 3)
                    fig_point.add_shape(type="line", x0=vx, x1=vx, y0=sy_min, y1=sy_max, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"))
                    vy = sy_min + (sy_max - sy_min) * (i / 3)
                    fig_point.add_shape(type="line", x0=sx_min, x1=sx_max, y0=vy, y1=vy, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"))
                
                for _, row in valid_data.iterrows():
                    val = row[target_metric]
                    dot_color, _ = get_color(val, target_metric)
                    fig_point.add_trace(go.Scatter(x=[row['StrikeZoneX'] * sc], y=[row['StrikeZoneY'] + y_off], mode='markers', marker=dict(size=12, color=dot_color, line=dict(width=1, color="white")), text=f"{val}", hoverinfo='text', showlegend=False))
                fig_point.update_layout(width=800, height=500, xaxis=dict(range=[-150, 150], visible=False), yaxis=dict(range=[-20, 200], visible=False), margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_point, use_container_width=True)
                st.dataframe(vdf)
            else:
                st.warning("選択した選手のデータが見つかりません。登録タブからデータを追加してください。")

    # --- タブ2: 登録 ---
    with tab2:
        st.title("📝 データ一括登録")
        with st.expander("📂 ファイルから登録 (Excel/CSV)", expanded=True):
            c1, c2 = st.columns(2)
            with c1: up_player = st.selectbox("選手を選択", PLAYERS, key="reg_player")
            with c2: up_date = st.date_input("練習日を選択", datetime.date.today(), key="reg_date")
            up_file = st.file_uploader("ファイルを選択", type=['xlsx', 'csv'], key="reg_file")
            if up_file:
                try:
                    df_new = pd.read_excel(up_file) if up_file.name.endswith('.xlsx') else pd.read_csv(up_file)
                    df_new['Player Name'] = up_player
                    df_new['DateTime'] = up_date.strftime("%Y-%m-%d") + " 00:00:00"
                    st.write("### プレビュー")
                    st.dataframe(df_new.head())
                    if st.button("GitHubへ追加保存"):
                        if save_to_github(pd.concat([db_df, df_new], ignore_index=True)):
                            st.success("保存完了！")
                            st.rerun()
                        else: st.error("保存失敗")
                except Exception as e: st.error(f"読み込みエラー: {e}")
