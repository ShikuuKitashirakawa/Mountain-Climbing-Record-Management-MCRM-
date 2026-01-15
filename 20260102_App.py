import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import pandas as pd
import os

st.title("🏞️ 日本三百名山・登山ログアプリ(試作版)")

# --- ページ設定 ---
st.set_page_config(layout="wide", page_title="日本三百名山・登山ログ")

CSV_FILE = "mountains300.csv"

# --- 1. データ読み込み ---
if os.path.exists(CSV_FILE):
    df_300 = pd.read_csv(CSV_FILE)
    if "登頂済み" not in df_300.columns:
        df_300["登頂済み"] = False
else:
    st.error(f"エラー: {CSV_FILE} が見つかりません。")
    st.stop()

# --- 2. 地方区分データの定義 ---
REGION_MAP = {
    "北海道": ["北海道"], "東北": ["青森", "岩手", "宮城", "秋田", "山形", "福島"],
    "関東": ["茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川"],
    "北陸・甲信越": ["新潟", "富山", "石川", "福井", "山梨", "長野"],
    "東海": ["岐阜", "静岡", "愛知", "三重"], "近畿": ["滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山"],
    "中国": ["鳥取", "島根", "岡山", "広島", "山口"], "四国": ["徳島", "香川", "愛媛", "高知"],
    "九州・沖縄": ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
}

# --- 3. サイドバー ---
with st.sidebar:
    st.title("🏔️ 山歩き記録帳")
    selected_region = st.selectbox("地方を選択", ["全国"] + list(REGION_MAP.keys()))
    st.markdown("---")
    map_style = st.radio("地図スタイル", ["標準地図", "淡色地図", "シームレス空中写真"])
    st.markdown("---")
    done_count = df_300["登頂済み"].sum()
    st.metric("合計登頂数", f"{done_count} / 300", f"{done_count/300:.1%}")

# --- 4. フィルタリングと座標設定 ---
if selected_region == "全国":
    display_df = df_300.copy()
    c_lat, c_lon, zoom = 36.2, 138.2, 5
else:
    prefs = REGION_MAP[selected_region]
    display_df = df_300[df_300["所在地"].apply(lambda x: any(p in str(x) for p in prefs))]
    if not display_df.empty:
        c_lat, c_lon = display_df["lat"].mean(), display_df["lon"].mean()
        zoom = 7 if selected_region != "北海道" else 6
    else:
        c_lat, c_lon, zoom = 36.2, 138.2, 5

# --- 5. 地図描画 ---
st.subheader(f"🗺️ {selected_region}の名山マップ")

map_tiles = {
    "標準地図": "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png",
    "淡色地図": "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png",
    "シームレス空中写真": "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"
}

m = folium.Map(location=[c_lat, c_lon], zoom_start=zoom, tiles=map_tiles[map_style], attr="国土地理院")

# クラスターのデザイン設定
icon_js = """
    function(cluster) {
        var count = cluster.getChildCount();
        return new L.DivIcon({ 
            html: '<div style="background-color: rgba(30, 30, 30, 0.85); border: 2px solid #fff; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold;">' + count + '</span></div>', 
            className: 'marker-cluster', iconSize: new L.Point(40, 40) 
        });
    }
"""
marker_cluster = MarkerCluster(icon_create_function=icon_js).add_to(m)

for idx, row in display_df.iterrows():
    is_done = row["登頂済み"]
    color = "orange" if is_done else ("red" if row["種類"]=="百名山" else "blue" if row["種類"]=="二百名山" else "green")
    icon_img = "trophy" if is_done else "mountain"
    
    status_label = f"【{row['種類']}】" + (" ✨登頂済み✨" if is_done else "")
    
    popup_html = f"""
    <div style="width: 180px; font-family: sans-serif; line-height: 1.5;">
        <p style="margin: 0; font-size: 11px; color: {color}; font-weight: bold;">{status_label}</p>
        <p style="margin: 0; font-size: 16px; font-weight: bold; color: #333;">{row['山名']}</p>
        <div style="margin: 5px 0; border-top: 1px solid #eee;"></div>
        <p style="margin: 0; font-size: 12px; color: #666;">標高: <span style="font-size: 15px; font-weight: bold; color: #000;">{row['標高']} m</span></p>
        <p style="margin: 0; font-size: 11px; color: #999;">所在地: {row['所在地']}</p>
    </div>
    """
    
    folium.Marker(
        [row["lat"], row["lon"]],
        popup=folium.Popup(popup_html, max_width=250),
        icon=folium.Icon(color=color, icon=icon_img, prefix="fa")
    ).add_to(marker_cluster)

# 地図表示・クリック取得
map_data = st_folium(m, width=None, height=550, use_container_width=True)

# --- 6. クリック連動ロジック ---
clicked_mt_name = None
if map_data and map_data.get("last_object_clicked"):
    clat, clon = map_data["last_object_clicked"]["lat"], map_data["last_object_clicked"]["lng"]
    display_df["tmp_dist"] = (display_df["lat"] - clat)**2 + (display_df["lon"] - clon)**2
    nearest = display_df.sort_values("tmp_dist").iloc[0]
    if nearest["tmp_dist"] < 0.001:
        clicked_mt_name = nearest["山名"]
        st.info(f"📍 選択中: **{clicked_mt_name}** （下のリストの先頭に表示しています）")

# --- 7. リスト表示 (クリック連動ソート) ---
st.markdown("---")
st.subheader(f"📋 {selected_region}の山一覧")

rank_order = {"百名山": 1, "二百名山": 2, "三百名山": 3}
display_sorted = display_df.copy()
display_sorted["rank_weight"] = display_sorted["種類"].map(rank_order)

if clicked_mt_name:
    display_sorted.loc[display_sorted["山名"] == clicked_mt_name, "rank_weight"] = 0

display_sorted = display_sorted.sort_values(by=["rank_weight", "lat"], ascending=[True, False])

edited_df = st.data_editor(
    display_sorted[["登頂済み", "種類", "山名", "標高", "所在地"]],
    use_container_width=True, height=450, hide_index=True,
    disabled=["種類", "山名", "標高", "所在地"], key="mt_editor"
)

# 保存処理
if st.button("✅ 変更を確定して保存する", key="save_final"):
    if edited_df is not None:
        for _, r in edited_df.iterrows():
            df_300.loc[df_300["山名"] == r["山名"], "登頂済み"] = r["登頂済み"]
        df_300.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
        st.success("CSVファイルに保存が完了しました！")
        st.rerun()

# --- 8. 出典情報の追加 ---
st.markdown("---")
st.caption("【出典】 日本三百名山（公益社団法人日本山岳会選定） / [日本山岳会](https://jac1.or.jp/)")
st.caption("【出典】 日本三百名山（公益社団法人日本山岳会選定） / [日本山岳会編 新版 日本三百名山 登山ガイド(2014) 掲載 山岳リスト](https://jac1.or.jp/wp-content/uploads/2016/10/300meizanlist%E3%80%80.pdf)")