import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")
st.title("🖱️ 地図クリックで座標を取得")

# セッション状態（クリック座標を保存するため）の初期化
if 'clicked_lat' not in st.session_state:
    st.session_state.clicked_lat = 35.6895
if 'clicked_lon' not in st.session_state:
    st.session_state.clicked_lon = 139.6917

# --- サイドバーの設定 ---
st.sidebar.header("座標と半径の設定")

# サイドバーの入力（セッション状態を初期値に設定）
lat = st.sidebar.number_input("緯度", value=st.session_state.clicked_lat, format="%.6f")
lon = st.sidebar.number_input("経度", value=st.session_state.clicked_lon, format="%.6f")
radius = st.sidebar.number_input("半径 (m)", value=1000, step=100)

# --- 地図の作成 ---
m = folium.Map(location=[lat, lon], zoom_start=14)

# クリック地点にマーカーを表示
folium.Marker([lat, lon], tooltip="選択中の地点").add_to(m)
folium.Circle([lat, lon], radius=radius, color="red", fill=True).add_to(m)

# 地図を描画し、クリックイベントを取得
# returned_objects に "last_clicked" を指定することで情報を取得可能
map_data = st_folium(m, width=800, height=500)

# --- クリック時の処理 ---
if map_data and map_data["last_clicked"]:
    new_lat = map_data["last_clicked"]["lat"]
    new_lon = map_data["last_clicked"]["lng"]
    
    # クリックされた座標が現在のセッションと異なる場合、更新してリラン
    if new_lat != st.session_state.clicked_lat or new_lon != st.session_state.clicked_lon:
        st.session_state.clicked_lat = new_lat
        st.session_state.clicked_lon = new_lon
        st.rerun()

st.write(f"現在の中心座標: {lat}, {lon}")
st.info("地図上をクリックすると、その地点に円が移動します。")

with st.sidebar:
    st.markdown("---")
    st.caption("### Disclaimer / 免責事項")
    st.caption("This app is for educational purposes. Use at your own risk.")
    st.caption("本アプリは学習用です。利用による責任は負いかねます。")

#複数ページ実装
st.page_link("20260102_App.py", label="Home", icon="🏠")
st.page_link("pages/page1.py", label="Page1")

