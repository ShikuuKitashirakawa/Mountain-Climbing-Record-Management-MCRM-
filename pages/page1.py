import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.features import DivIcon # ラベル表示に必要

st.set_page_config(layout="wide", page_title="エリア分析 - Page1")

st.title("📍 エリア分析ツール (Page 1)")
st.markdown("地図上をクリックして中心地点を変更し、半径ごとの面積を確認できます。")

# --- セッション状態の初期化 ---
if 'clicked_lat' not in st.session_state:
    st.session_state.clicked_lat = 35.6812
if 'clicked_lon' not in st.session_state:
    st.session_state.clicked_lon = 139.7671

# --- サイドバー設定 ---
with st.sidebar:
    st.header("📍 座標と半径の設定")
    lat = st.number_input("緯度", value=st.session_state.clicked_lat, format="%.6f")
    lon = st.number_input("経度", value=st.session_state.clicked_lon, format="%.6f")
    st.markdown("---")
    r1 = st.number_input("半径1 (km) - 赤太実線", min_value=0.0, value=1.0, step=0.1)
    r2 = st.number_input("半径2 (km) - 青細実線", min_value=0.0, value=2.0, step=0.1)
    r3 = st.number_input("半径3 (km) - 緑細点線", min_value=0.0, value=3.0, step=0.1)
    st.markdown("---")
    
    map_style = st.radio("地図スタイル", ["標準地図", "淡色地図", "シームレス空中写真"])
    
    st.page_link("20260102_App.py", label="Home: 詳細な施設分析へ", icon="🏠")

# --- メインレイアウト ---
col_map, col_info = st.columns([3, 1])

with col_map:
    map_tiles = {
        "標準地図": "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png",
        "淡色地図": "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png",
        "シームレス空中写真": "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"
    }
    m = folium.Map(
        location=[lat, lon], 
        zoom_start=13, 
        tiles=map_tiles[map_style], 
        attr="国土地理院"
    )
    
    folium.Marker([lat, lon], icon=folium.Icon(color="black", icon="info-sign")).add_to(m)

    # 同心円の設定: (半径, 色, 太さ, 点線)
    configs = [
        (r1, "red", 5, None),
        (r2, "blue", 2, None),
        (r3, "green", 2, "10, 10")
    ]

    for r, color, weight, dash in configs:
        if r > 0:
            # 1. 円の描画
            folium.Circle(
                location=[lat, lon], radius=r*1000, 
                color=color, weight=weight, dash_array=dash,
                fill=True, fill_opacity=0.05
            ).add_to(m)

            # 2. ラベル（半径〇km）の描画
            # 簡易計算で真北の座標を算出（1度 = 約111km）
            label_lat = lat + (r / 111.0) 
            
            folium.Marker(
                location=[label_lat, lon],
                icon=DivIcon(
                    icon_size=(150, 36),
                    icon_anchor=(75, 18), # テキストの中央が座標に来るように調整
                    html=f'<div style="font-size: 10pt; color: {color}; font-weight: bold; '
                         f'text-align: center; background-color: rgba(255,255,255,0.7); '
                         f'border-radius: 5px; padding: 2px;">半径 {r} km</div>',
                )
            ).add_to(m)

    map_data = st_folium(m, width=None, height=600, use_container_width=True)

with col_info:
    st.subheader("📏 面積計算結果")
    st.write(f"中心座標: `{lat:.5f}, {lon:.5f}`")
    st.markdown("---")
    for r, label in zip([r1, r2, r3], ["🔴 半径1", "🔵 半径2", "🟢 半径3"]):
        if r > 0:
            area = 3.14159 * (r**2)
            st.write(f"{label}: **{r} km** / **{area:.2f} km²**")
            st.markdown("---")

# --- クリック処理 ---
if map_data and map_data["last_clicked"]:
    nl, ng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    if abs(nl - st.session_state.clicked_lat) > 0.0001:
        st.session_state.clicked_lat, st.session_state.clicked_lon = nl, ng
        st.rerun()