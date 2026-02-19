import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import datetime

# --- ページ設定 ---
st.set_page_config(layout="wide", page_title="日本三百名山・登山ログ")

st.title("🏞️ 日本三百名山・登山ログ（完全統合版）")

# --- 定数設定 ---
CSV_FILE = "mountains300.csv"

# --- 1. データ読み込み（修正版） ---
def load_mountain_data():
    df = None
    
    # A. ローカルのCSVファイルを最優先で確認
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
            # 読み込めた直後に「None」じゃないかチェック
            if df is not None:
                st.sidebar.success(f"📂 CSV読み込み成功 ({len(df)}件)")
            else:
                st.sidebar.error("❌ ファイルはあるが、読み込み結果が None です")
        except Exception as e:
            st.sidebar.error(f"⚠️ CSV読み込み失敗: {e}")

    # --- ここで df が None の場合のセーフティガード ---
    if df is None:
        # (ここで本来は Google Sheets を見に行くが、今は一旦止めて原因を探る)
        st.error(f"❌ '{CSV_FILE}' が見つからないか、正しく読み込めませんでした。")
        st.info("ファイルが Python スクリプトと同じフォルダにあるか確認してください。")
        st.stop() # ここで止めれば、下の df["lat"] でのエラーは防げます

    # --- 以降、df が存在する場合のみ実行される ---
    if "lat" not in df.columns:
        st.error(f"❌ CSVに 'lat' 列がありません。現在の列名: {list(df.columns)}")
        st.stop()
        

    # データ型の整理
    df["lat"] = pd.to_numeric(df["lat"], errors='coerce')
    df["lon"] = pd.to_numeric(df["lon"], errors='coerce')
    
    # 欠損値（NaN）になった行を除去（地図描画エラー防止）
    df = df.dropna(subset=["lat", "lon"])
    
    # 登頂済み列の正規化
    if "登頂済み" not in df.columns:
        df["登頂済み"] = False
    else:
        df["登頂済み"] = df["登頂済み"].astype(str).str.upper().map({'TRUE': True, 'FALSE': False}).fillna(False)
    
    # 登頂日列の正規化
    if "登頂日" not in df.columns:
        df["登頂日"] = ""
    else:
        df["登頂日"] = df["登頂日"].fillna("").astype(str).replace("nan", "")
    
    return df

# --- データの初期化 ---
if "df_master" not in st.session_state:
    st.session_state.df_master = load_mountain_data()

df_300 = load_mountain_data()

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
    st.header("🏔️ 山歩き記録帳")
    selected_region = st.selectbox("表示エリアを選択", ["全国"] + list(REGION_MAP.keys()))
    
    st.markdown("---")
    map_style = st.radio("地図スタイル", ["標準地図", "淡色地図", "シームレス空中写真"])
    
    st.markdown("---")
    done_count = st.session_state.df_master["登頂済み"].sum()
    total_mountains = len(df_300)
    st.metric("合計登頂数", f"{done_count} / {total_mountains}", f"{done_count/total_mountains:.1%}")
    
    with st.expander("📝 開発・操作メモ"):
        st.caption("地図上のピンをクリックすると、下のリストが連動してソートされます。")

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
    
    # --- 1. まず popup_html を定義する (これが先！) ---
    date_info = f"<br>登頂日: {row['登頂日']}" if row['登頂日'] else ""
    done_label = " 🏆 【登頂達成！】" if is_done else ""
    
    popup_html = f"""
    <div style="width: 180px; font-family: sans-serif; line-height: 1.5;">
        <p style="margin: 0; font-size: 11px; color: {'orange' if is_done else 'blue'}; font-weight: bold;">【{row['種類']}】{done_label}</p>
        <p style="margin: 0; font-size: 16px; font-weight: bold; color: #333;">{row['山名']}</p>
        <div style="margin: 5px 0; border-top: 1px solid #eee;"></div>
        <p style="margin: 0; font-size: 12px; color: #666;">標高: <span style="font-size: 14px; font-weight: bold; color: #000;">{row['標高']} m</span></p>
        <p style="margin: 0; font-size: 11px; color: #999;">所在地: {row['所在地']}{date_info}</p>
    </div>
    """

    # --- 2. 次にマーカーのアイコンを決める ---
    if is_done:
        # 豪華なゴールドマーカー (サイズを30px → 50pxに大型化)
        icon_html = """
        <div style="position: relative; width: 50px; height: 50px;">
            <div style="
                position: absolute; width: 100%; height: 100%;
                background: radial-gradient(circle, rgba(255,215,0,0.9) 0%, rgba(255,165,0,0.4) 50%, rgba(255,215,0,0) 80%);
                border-radius: 50%;
                animation: flare 2s infinite alternate;
                filter: blur(2px);">
            </div>
            <div style="
                position: absolute; width: 100%; height: 100%;
                display: flex; align-items: center; justify-content: center;
                font-size: 35px; /* アイコンを大きく */
                filter: drop-shadow(0 0 10px rgba(255, 69, 0, 0.8));">
                👑
            </div>
        </div>
        <style>
        @keyframes flare {
            0% { transform: scale(0.7); opacity: 0.4; }
            100% { transform: scale(1.4); opacity: 0.8; }
        }
        </style>
        """
        # icon_size と icon_anchor を大きくしたサイズに合わせて調整
        icon = folium.DivIcon(
            html=icon_html, 
            icon_size=(50, 50), 
            icon_anchor=(25, 25) # 中心を合わせるためにサイズ(50)の半分に設定
        )
    else:
        # 通常の山マーカー
        color = "red" if row["種類"]=="百名山" else "blue" if row["種類"]=="二百名山" else "green"
        icon = folium.Icon(color=color, icon="mountain", prefix="fa")

    # --- 3. 最後にマーカーを地図に追加する (ここで popup_html を使う) ---
    folium.Marker(
        [row["lat"], row["lon"]],
        popup=folium.Popup(popup_html, max_width=250), # ここでエラーが出ていた
        icon=icon
    ).add_to(marker_cluster)
    
# 地図表示・クリックオブジェクト取得
map_data = st_folium(m, width=None, height=550, use_container_width=True, key="mt_hybrid_map")

# --- 6. クリック連動ロジック（復活機能） ---
clicked_mt_name = None
if map_data and map_data.get("last_object_clicked"):
    clat, clon = map_data["last_object_clicked"]["lat"], map_data["last_object_clicked"]["lng"]
    # 距離が最も近い山を特定して選択
    display_df["tmp_dist"] = (display_df["lat"] - clat)**2 + (display_df["lon"] - clon)**2
    nearest = display_df.sort_values("tmp_dist").iloc[0]
    if nearest["tmp_dist"] < 0.001:
        clicked_mt_name = nearest["山名"]
        st.info(f"📍 **{clicked_mt_name}** を選択中（下のリストの先頭に表示しています）")

# --- 7. リスト表示と自動保存ロジック ---
st.markdown("---")
st.subheader("📋 登頂記録（チェックを入れると即座に保存されます）")

# 以前の状態を保持
df_current = st.session_state.df_master.copy()

# 種類順の重み付け（百 > 二百 > 三百）
rank_order = {"百名山": 1, "二百名山": 2, "三百名山": 3}
display_sorted = display_df.copy() # ここで display_sorted を作成！
display_sorted["rank_weight"] = display_sorted["種類"].map(rank_order).fillna(4)

# 地図でクリックされた山があれば、それをリストの最優先（一番上）にする
if clicked_mt_name:
    display_sorted.loc[display_sorted["山名"] == clicked_mt_name, "rank_weight"] = 0

# 重みと山名でソート
display_sorted = display_sorted.sort_values(by=["rank_weight", "山名"])

# データエディタを表示
edited_df = st.data_editor(
    display_sorted[["登頂済み", "登頂日", "種類", "山名", "標高", "所在地"]],
    use_container_width=True, height=500, hide_index=True,
    disabled=["種類", "山名", "標高", "所在地"], key="mt_editor"
)

# --- 変更検知ロジック ---
# エディタで変更があった場合、edited_df の中身が更新される
for idx, row in edited_df.iterrows():
    mt_name = row["山名"]
    new_status = row["登頂済み"]
    
    # 元のデータ(df_master)の状態を取得
    old_status = st.session_state.df_master.loc[st.session_state.df_master["山名"] == mt_name, "登頂済み"].values[0]

    # 【重要】今回新しくチェックがついた場合
    if new_status == True and old_status == False:
        # 1. マスターデータを更新
        st.session_state.df_master.loc[st.session_state.df_master["山名"] == mt_name, ["登頂済み", "登頂日"]] = [True, row["登頂日"]]
        
        # 2. 保存処理を実行
        if os.path.exists(CSV_FILE):
            st.session_state.df_master.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
        else:
            conn = st.connection("gsheets", type=GSheetsConnection)
            conn.update(data=st.session_state.df_master)

        # 3. お祝い演出！
        st.balloons()
        st.snow()
        st.toast(f"🏆 {mt_name} 登頂おめでとうございます！", icon="⛰️")
        
        # 4. 画面を再描画して地図に反映（少し待ってから）
        import time
        time.sleep(2)
        st.rerun()

    # チェックが外された場合の保存処理（演出なし）
    elif new_status == False and old_status == True:
        st.session_state.df_master.loc[st.session_state.df_master["山名"] == mt_name, ["登頂済み", "登頂日"]] = [False, ""]
        if os.path.exists(CSV_FILE):
            st.session_state.df_master.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
        st.rerun()
        
# --- 8. 免責事項・ライセンス・出典 ---
st.markdown("---")
with st.expander("ℹ️ アプリ情報・出典・ライセンス"):
    st.markdown("""
    ### **【出典情報】**
    - **日本三百名山リスト**: 公益社団法人日本山岳会選定 / [日本山岳会編 新版 日本三百名山 登山ガイド(2014)](https://jac1.or.jp/wp-content/uploads/2016/10/300meizanlist%E3%80%80.pdf)
    - **地図データ**: [国土地理院タイル](https://maps.gsi.go.jp/development/ichiran.html)
    
    ### **【ライセンス】**
    - **MIT License** / © 2026 Shikuu Kitashirakawa
    
    ### **【免責事項】**
    - 本アプリの情報の正確性は保証されません。実際の登山には必ず専用の装備と地図を携行してください。
    - アプリ利用による事故や損害について、開発者は一切の責任を負いません。
    """)