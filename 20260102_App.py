import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import requests
import re
import os

# ページ基本設定
st.set_page_config(layout="wide", page_title="日本三百名山探索ツール")

st.title("🏔️ 日本三百名山探索ツール（完成版プロトタイプ）")
st.markdown("自作の三百名山データベースと国土地理院地図を連携させた探索ツールです。")

# --- 1. CSVデータの読み込み ---
CSV_FILE = "mountains300.csv"
if os.path.exists(CSV_FILE):
    df_300 = pd.read_csv(CSV_FILE)
else:
    st.error(f"エラー: {CSV_FILE} が見つかりません。")
    st.stop()

# --- 2. データ取得・検索関数 ---

@st.cache_data(ttl=3600)
def get_nearby_mountains(lat_val, lon_val, radius_km):
    """Overpass APIを使用して周囲の山頂ノードを取得"""
    overpass_url = "https://overpass-api.de/api/interpreter"
    dist = radius_km * 1000
    
    # エラー回避のため f-string をやめ、.format() を使用
    query_template = '[out:json][timeout:30];node["natural"="peak"](around:{0},{1},{2});out body;'
    query = query_template.format(dist, lat_val, lon_val)
    
    try:
        res = requests.get(overpass_url, params={'data': query}, timeout=15)
        return res.json().get('elements', [])
    except Exception as e:
        return []

def search_location(query_text, pref_name):
    """Nominatim APIを使用してキーワードから座標を取得"""
    url = "https://nominatim.openstreetmap.org/search"
    full_query = "{0} {1}".format(pref_name, query_text) if pref_name != "指定なし" else query_text
    params = {"q": full_query, "format": "json", "limit": 1, "countrycodes": "jp"}
    headers = {"User-Agent": "MyMountainApp/Prototype"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        data = res.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"]), data[0]["display_name"]
    except:
        return None
    return None

# --- 3. CSVベースの判定ロジック ---

def get_mountain_info_from_csv(p_lat, p_lon):
    """CSVの座標と照らし合わせて、三百名山かどうかを判定"""
    nearby = df_300[
        (abs(df_300['lat'] - p_lat) < 0.01) & 
        (abs(df_300['lon'] - p_lon) < 0.01)
    ]
    if not nearby.empty:
        row = nearby.iloc[0]
        rank = row['分類']
        color = "red" if rank == "百名山" else "blue" if rank == "二百名山" else "green"
        return "【{0}】".format(rank), row['山名'], row['標高'], color, True
    return "", "", "", "orange", False

# --- 4. セッション状態の初期化 ---
if 'clicked_lat' not in st.session_state:
    st.session_state.clicked_lat = 35.3606 
if 'clicked_lon' not in st.session_state:
    st.session_state.clicked_lon = 138.7274

# --- 5. サイドバー ---
with st.sidebar:
    st.header("🔍 ピンポイント山名検索")
    prefectures = ["指定なし", "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
    selected_pref = st.selectbox("都道府県で絞り込む", prefectures)
    search_query = st.text_input("山の名前（例：槍ヶ岳）")
    
    if st.button("検索してジャンプ"):
        result = search_location(search_query, selected_pref)
        if result:
            st.session_state.clicked_lat, st.session_state.clicked_lon = result[0], result[1]
            st.rerun()

    st.markdown("---")
    st.header("📍 地図設定")
    lat_in = st.number_input("中心緯度", value=st.session_state.clicked_lat, format="%.6f")
    lon_in = st.number_input("中心経度", value=st.session_state.clicked_lon, format="%.6f")
    map_style = st.radio("地図スタイル", ["標準地図", "淡色地図", "シームレス空中写真"])
    r_mountain = st.slider("探索半径 (km)", 5, 100, 30)
    
    st.markdown("---")
    st.page_link("pages/page1.py", label="同心円描画ツールへ", icon="⭕")
    st.page_link("pages/low_mountains.py", label="一般山岳・低山探索へ", icon="🌿")

# --- 6. メインレイアウト ---
peaks = get_nearby_mountains(lat_in, lon_in, r_mountain)
col_map, col_info = st.columns([3, 1])

with col_map:
    map_tiles = {
        "標準地図": "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png",
        "淡色地図": "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png",
        "シームレス空中写真": "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"
    }
    
    m = folium.Map(location=[lat_in, lon_in], zoom_start=10, tiles=map_tiles[map_style], attr="国土地理院")
    folium.Marker([lat_in, lon_in], icon=folium.Icon(color="black", icon="crosshairs", prefix="fa")).add_to(m)
    
    for p in peaks:
        tag, name, ele, color, is_300 = get_mountain_info_from_csv(p['lat'], p['lon'])
        d_name = name if is_300 else p.get('tags', {}).get('name', '無名峰')
        d_ele = ele if is_300 else p.get('tags', {}).get('ele', '不明')
        
        popup_html = """
        <div style="width: 150px; font-family: sans-serif; line-height: 1.1;">
            <p style="margin: 0; font-size: 10px; color: gray;">{0}</p>
            <p style="margin: 0; font-size: 14px; color: {1}; font-weight: bold;">{2}</p>
            <div style="margin: 1px 0; border-top: 1px dashed #ddd;"></div>
            <p style="margin: 0; font-size: 12px;">標高: <b>{3} m</b></p>
        </div>
        """.format(tag, color, d_name, d_ele)
        
        folium.Marker(
            [p['lat'], p['lon']], 
            popup=folium.Popup(popup_html, max_width=200),
            icon=folium.Icon(color=color, icon="mountain", prefix="fa")
        ).add_to(m)

    map_data = st_folium(m, width=None, height=700, use_container_width=True)

with col_info:
    st.subheader("📊 エリア内の名山")
    found_peaks = []
    for p in peaks:
        tag, name, ele, color, is_300 = get_mountain_info_from_csv(p['lat'], p['lon'])
        if is_300:
            found_peaks.append((tag, name, ele))
    
    if found_peaks:
        for t, n, e in found_peaks:
            st.write("- {0} **{1}** ({2}m)".format(t, n, e))
    else:
        st.write("名山は見つかりませんでした。")

# --- 7. クリック連動処理 ---
if map_data and map_data["last_clicked"]:
    nl, ng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    if abs(nl - st.session_state.clicked_lat) + abs(ng - st.session_state.clicked_lon) > 0.01:
        st.session_state.clicked_lat, st.session_state.clicked_lon = nl, ng
        st.rerun()


"""
import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import re

st.set_page_config(layout="wide", page_title="名山探索ツール")

st.title("🏔️ 全国名山探索ツール（試作品）")

# --- 定数・リスト ---
PREFECTURES = ["指定なし", "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
FAMOUS_100_KEYWORDS = ["富士山", "槍ヶ岳", "穂高岳", "剱岳", "北岳", "大雪山", "岩手山", "開聞岳", "阿蘇山", "筑波山"]

# --- 関数定義 ---
@st.cache_data(ttl=3600)
def get_nearby_mountains(lat, lon, radius_km):
    overpass_url = "https://overpass-api.de/api/interpreter"
    dist = radius_km * 1000
#    query = f"""[out:json][timeout:30];node["natural"="peak"](around:{dist},{lat},{lon});out body;"""
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

# --- ★引数に lat, lon を追加 ---
def analyze_mountain_type(tags, p_lat, p_lon):
    raw_name = tags.get('name', '無名峰')
    text = str(tags).lower()
    
    # 富士山頂エリアの座標判定 (剣ヶ峰などをカバー)
    is_fuji_area = (35.355 <= p_lat <= 35.375) and (138.720 <= p_lon <= 138.740)
    
    is_100 = any(k in text for k in ["日本百名山", "100 famous japanese mountains"]) or \
             any(fn in raw_name for fn in FAMOUS_100_KEYWORDS) or \
             is_fuji_area
    
    if is_100:
        display_name = f"富士山 ({raw_name})" if is_fuji_area else raw_name
        return "【日本百名山】", display_name, "red", True
    if "新日本百名山" in text:
        return "【新日本百名山】", raw_name, "purple", True
    return "", raw_name, "orange", False

# --- セッション管理 ---
if 'clicked_lat' not in st.session_state: st.session_state.clicked_lat = 35.3606 
if 'clicked_lon' not in st.session_state: st.session_state.clicked_lon = 138.7274

# --- サイドバー ---
with st.sidebar:
    st.header("🔍 山名検索")
    selected_pref = st.selectbox("都道府県で絞り込む", PREFECTURES)
    search_query = st.text_input("山の名前")
    if st.button("検索してジャンプ"):
        result = search_location(search_query, selected_pref)
        if result:
            st.session_state.clicked_lat, st.session_state.clicked_lon = result[0], result[1]
            st.rerun()
    st.markdown("---")
    lat_in = st.number_input("緯度", value=st.session_state.clicked_lat, format="%.6f")
    lon_in = st.number_input("経度", value=st.session_state.clicked_lon, format="%.6f")
    map_style = st.radio("地図スタイル", ["標準地図", "淡色地図", "シームレス空中写真"])
    r_mountain = st.slider("探索半径 (km)", 5, 100, 30)
    st.markdown("---")
    st.page_link("pages/page1.py", label="同心円描画ツールへ", icon="⭕")
    st.page_link("pages/low_mountains.py", label="低山探索ツールへ", icon="🌿")

# --- メイン描画 ---
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

    for p in peaks:
        # ★ここでの呼び出しを修正
        tag_label, name, color, is_major = analyze_mountain_type(p.get('tags', {}), p['lat'], p['lon'])
        ele = p.get('tags', {}).get('ele', '不明')
        
        popup_content = f"""
        <div style="width: 150px; font-family: sans-serif; line-height: 1.1;">
            <p style="margin: 0; font-size: 10px; color: gray;">{tag_label}</p>
            <p style="margin: 0; font-size: 14px; color: {color}; font-weight: bold;">{name}</p>
            <div style="margin: 1px 0; border-top: 1px dashed #ddd;"></div>
            <p style="margin: 0; font-size: 12px;">標高: <b>{ele} m</b></p>
        </div>
        """
        folium.Marker(
            [p['lat'], p['lon']], 
            popup=folium.Popup(popup_content, max_width=200),
            icon=folium.Icon(color=color, icon="mountain", prefix="fa")
        ).add_to(m)

    map_data = st_folium(m, width=None, height=700, use_container_width=True)

with col2:
    st.subheader("📊 周辺の名山")
    major_found = False
    for p in peaks:
        # ★右側のリスト表示部分の呼び出しも修正
        tag_label, name, color, is_major = analyze_mountain_type(p.get('tags', {}), p['lat'], p['lon'])
        if is_major:
            st.write(f"- {tag_label}{name}")
            major_found = True
    if not major_found: st.write("名山は見つかりませんでした")

# クリック連動 (0.01度以上の移動)
if map_data and map_data["last_clicked"]:
    nl, ng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    if abs(nl - st.session_state.clicked_lat) + abs(ng - st.session_state.clicked_lon) > 0.01:
        st.session_state.clicked_lat, st.session_state.clicked_lon = nl, ng
        st.rerun()
"""