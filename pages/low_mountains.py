import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import re

st.set_page_config(layout="wide", page_title="低山・一般山岳探索")

st.title("🌿 全国・一般山岳探索ツール（試作品）")
st.markdown("百名山・新日本百名山以外の、地域に親しまれている山々を探索できます。")

# --- 1. 定数・リスト ---
PREFECTURES = ["指定なし", "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]

# --- 2. 関数定義 ---
@st.cache_data(ttl=3600)
def get_nearby_mountains(lat, lon, radius_km):
    overpass_url = "https://overpass-api.de/api/interpreter"
    dist = radius_km * 1000
    query = f"""[out:json][timeout:30];node["natural"="peak"](around:{dist},{lat},{lon});out body;"""
    try:
        res = requests.get(overpass_url, params={'data': query}, timeout=15)
        return res.json().get('elements', [])
    except: return []

def search_location(query, pref):
    url = "https://nominatim.openstreetmap.org/search"
    full_query = f"{pref} {query}" if pref != "指定なし" else query
    params = {"q": full_query, "format": "json", "limit": 1, "countrycodes": "jp"}
    headers = {"User-Agent": "MyMountainApp/Prototype"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        data = res.json()
        if data: return float(data[0]["lat"]), float(data[0]["lon"]), data[0]["display_name"]
    except: return None
    return None

def is_major_mountain(tags):
    """百名山・新日本百名山かどうかを判定"""
    text = str(tags).lower()
    return any(k in text for k in ["日本百名山", "100 famous japanese mountains", "新日本百名山"])

# --- 3. セッション管理 ---
if 'clicked_lat' not in st.session_state: st.session_state.clicked_lat = 35.3606 
if 'clicked_lon' not in st.session_state: st.session_state.clicked_lon = 138.7274

lat_in = st.session_state.clicked_lat
lon_in = st.session_state.clicked_lon

# --- 4. サイドバー ---
with st.sidebar:
    st.header("🔍 一般山岳検索")
    selected_pref = st.selectbox("都道府県で絞り込む", PREFECTURES, key="low_pref")
    search_query = st.text_input("山の名前", key="low_search")
    
    if st.button("検索してジャンプ", key="low_btn"):
        result = search_location(search_query, selected_pref)
        if result:
            st.session_state.clicked_lat, st.session_state.clicked_lon = result[0], result[1]
            st.rerun()

    st.markdown("---")
    map_style = st.radio("地図スタイル", ["標準地図", "淡色地図", "シームレス空中写真"], key="low_map_style")
    # ★keyを追加してエラーを回避
    r_mountain = st.slider("探索半径 (km)", 5, 50, 15, key="low_mt_slider")
    
    st.markdown("---")
    st.page_link("20260102_App.py", label="名山探索（メイン）へ戻る", icon="🏔️")

# --- 5. メイン描画 ---
peaks = get_nearby_mountains(lat_in, lon_in, r_mountain)
col1, col2 = st.columns([3, 1])

with col1:
    map_tiles = {
        "標準地図": "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png",
        "淡色地図": "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png",
        "シームレス空中写真": "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"
    }
    m = folium.Map(location=[lat_in, lon_in], zoom_start=11, tiles=map_tiles[map_style], attr="国土地理院")
    folium.Marker([lat_in, lon_in], icon=folium.Icon(color="black", icon="crosshairs", prefix="fa")).add_to(m)
    
    plot_count = 0
    for p in peaks:
        tags = p.get('tags', {})
        # 名山（百名山・新日本）でなければプロット
        if not is_major_mountain(tags):
            name = tags.get('name', '無名峰')
            ele = tags.get('ele', '不明')
            
            popup_content = f"""
            <div style="width: 140px; font-family: sans-serif; line-height: 1.1;">
                <p style="margin: 0; font-size: 10px; color: green;">🌿 一般山岳</p>
                <p style="margin: 0; font-size: 14px; font-weight: bold;">{name}</p>
                <div style="margin: 1px 0; border-top: 1px dashed #ddd;"></div>
                <p style="margin: 0; font-size: 12px;">標高: <b>{ele} m</b></p>
            </div>
            """
            folium.Marker(
                [p['lat'], p['lon']], 
                popup=folium.Popup(popup_content, max_width=200),
                icon=folium.Icon(color="green", icon="leaf", prefix="fa")
            ).add_to(m)
            plot_count += 1
    
    map_data = st_folium(m, width=None, height=700, use_container_width=True)

with col2:
    st.subheader("🌿 周辺の山一覧")
    st.write(f"半径 {r_mountain}km 内の一般山岳: {plot_count}件")
    # 標高順に上位20件を表示
    sorted_peaks = sorted(
        [p for p in peaks if not is_major_mountain(p.get('tags', {}))],
        key=lambda x: float(re.findall(r"\d+", x['tags'].get('ele', '0'))[0]) if re.findall(r"\d+", x['tags'].get('ele', '0')) else 0,
        reverse=True
    )
    for p in sorted_peaks[:20]:
        st.write(f"- {p['tags'].get('name','無名')} ({p['tags'].get('ele','?')}m)")

# クリック連動 (0.01度以上の移動)
if map_data and map_data["last_clicked"]:
    nl, ng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    if abs(nl - st.session_state.clicked_lat) + abs(ng - st.session_state.clicked_lon) > 0.01:
        st.session_state.clicked_lat, st.session_state.clicked_lon = nl, ng
        st.rerun()