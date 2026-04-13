import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib

# =========================
# Supabase接続
# =========================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# =========================
# 日本語フォント
# =========================
font_path = "NotoSansJP-Regular.ttf"
font_prop = None

try:
    font_prop = fm.FontProperties(fname=font_path)
    matplotlib.rcParams["font.family"] = font_prop.get_name()
except:
    pass

# =========================
# ページ設定
# =========================
st.set_page_config(page_title="家計簿アプリ", layout="centered")

# =========================
# カテゴリ
# =========================
EXPENSE_CATEGORIES = ["外食費", "食材費", "交通費", "娯楽", "日用品", "その他支出"]
INCOME_CATEGORIES = ["給料", "ボーナス", "副業", "お小遣い", "その他収入"]

CATEGORY_COLORS = {
    "外食費": "#FF9999",
    "食材費": "#FF9900",
    "交通費": "#66B3FF",
    "娯楽": "#99FF99",
    "日用品": "#FFCC99",
    "その他支出": "#D3D3D3",
    "給料": "#FFD700",
    "ボーナス": "#C71585",
    "副業": "#20B2AA",
    "お小遣い": "#9370DB",
    "その他収入": "#A9A9A9"
}

# =========================
# データ取得
# =========================
@st.cache_data(ttl=5)
def load_data():
    res = supabase.table("kakeibo").select("*").execute()
    df = pd.DataFrame(res.data)

    if df.empty:
        df = pd.DataFrame(columns=["id", "日付", "項目", "金額", "カテゴリ", "タイプ"])

    if not df.empty:
        df["日付"] = pd.to_datetime(df["日付"])
        df["金額"] = pd.to_numeric(df["金額"])

    return df

df = load_data()

# =========================
# タイトル
# =========================
st.title("💰 家計簿アプリ")

# =========================
# 残高（タブ化）
# =========================
st.header("💰 残高")

if df.empty:
    st.info("データがまだありません")
else:
    df["年"] = df["日付"].dt.year
    df["月"] = df["日付"].dt.month

    tabs = st.tabs(["合計", "年別", "月別"])

    # =========================
    # 合計
    # =========================
    with tabs[0]:
        income_total = df[df["タイプ"] == "収入"]["金額"].sum()
        expense_total = df[df["タイプ"] == "支出"]["金額"].sum()

        st.metric("残高", f"{income_total - expense_total:,.0f} 円")
        st.write(f"収入：{income_total:,.0f} 円")
        st.write(f"支出：{expense_total:,.0f} 円")

    # =========================
    # 年別
    # =========================
    with tabs[1]:
        years = sorted(df["年"].unique(), reverse=True)

        for y in years:
            ydf = df[df["年"] == y]

            income = ydf[ydf["タイプ"] == "収入"]["金額"].sum()
            expense = ydf[ydf["タイプ"] == "支出"]["金額"].sum()

            st.subheader(f"{y}年")
            st.metric("残高", f"{income - expense:,.0f} 円")
            st.write(f"収入：{income:,.0f} 円 / 支出：{expense:,.0f} 円")
            st.divider()

    # =========================
    # 月別
    # =========================
    with tabs[2]:
        df["年月"] = df["日付"].dt.to_period("M").astype(str)
        months = sorted(df["年月"].unique(), reverse=True)
    
        month_tabs = st.tabs(months)
    
        for mtab, m in zip(month_tabs, months):
            with mtab:
                mdf = df[df["年月"] == m]
    
                income = mdf[mdf["タイプ"] == "収入"]["金額"].sum()
                expense = mdf[mdf["タイプ"] == "支出"]["金額"].sum()
    
                st.metric("残高", f"{income - expense:,.0f} 円")
                st.write(f"収入：{income:,.0f} 円")
                st.write(f"支出：{expense:,.0f} 円")

st.divider()

# =========================
# データ追加
# =========================
st.header("➕ データ追加")

if "type_radio" not in st.session_state:
    st.session_state.type_radio = "支出"

st.radio("タイプ", ["支出", "収入"], key="type_radio")

category_list = EXPENSE_CATEGORIES if st.session_state.type_radio == "支出" else INCOME_CATEGORIES

with st.form("form"):
    d = st.date_input("日付", value=date.today())
    item = st.text_input("項目")
    amount = st.number_input("金額", min_value=0)
    category = st.selectbox("カテゴリ", category_list)

    if st.form_submit_button("追加"):

        supabase.table("kakeibo").insert({
            "日付": str(d),
            "項目": item,
            "金額": int(amount),
            "カテゴリ": category,
            "タイプ": st.session_state.type_radio
        }).execute()

        st.success("追加しました！")
        st.cache_data.clear()
        st.rerun()

st.divider()

# =========================
# 月別集計
# =========================
st.header("📊 月別集計")

if not df.empty:
    df["年"] = df["日付"].dt.year
    df["月"] = df["日付"].dt.month

    years = sorted(df["年"].unique(), reverse=True)
    tabs = st.tabs([f"{y}年" for y in years])

    for tab, y in zip(tabs, years):
        with tab:
            ydf = df[df["年"] == y]

            summary = ydf.pivot_table(
                index="月",
                columns="タイプ",
                values="金額",
                aggfunc="sum",
                fill_value=0
            )

            st.dataframe(summary)

            if "収入" in summary:
                st.bar_chart(summary["収入"])

            if "支出" in summary:
                st.bar_chart(summary["支出"])

st.divider()

# =========================
# 円グラフ
# =========================
st.header("🥧 支出内訳")

if df.empty or "タイプ" not in df.columns:
    st.info("データがまだありません")
    exp = pd.DataFrame()
else:
    exp = df[df["タイプ"] == "支出"].copy()

if not exp.empty:
    exp["年月"] = exp["日付"].dt.to_period("M").astype(str)
    months = sorted(exp["年月"].unique(), reverse=True)
    m = st.selectbox("月選択", months)

    mdf = exp[exp["年月"] == m]
    pie = mdf.groupby("カテゴリ")["金額"].sum().reindex(EXPENSE_CATEGORIES).fillna(0)

    colors = [CATEGORY_COLORS[c] for c in pie.index]

    # 👇 追加（これが重要）
    if pie.sum() == 0:
        st.info("この月の支出データがありません")
    else:
        fig, ax = plt.subplots()
    
        ax.pie(
            pie,
            labels=pie.index,
            autopct="%1.1f%%",
            colors=colors,
            textprops={"fontproperties": font_prop} if font_prop else {}
        )
    
        ax.axis("equal")
        st.pyplot(fig)

st.divider()

# =========================
# データ管理（年・月タブ＋編集）
# =========================
st.header("🗂 データ管理")

# フィルタ
selected_type = st.selectbox("タイプで絞る", ["すべて", "支出", "収入"])
if selected_type != "すべて":
    ydf = ydf[ydf["タイプ"] == selected_type]

if not df.empty and "edit_id" not in st.session_state:

    df["年"] = df["日付"].dt.year
    df["月"] = df["日付"].dt.month

    years = sorted(df["年"].unique(), reverse=True)
    year_tabs = st.tabs([f"{y}年" for y in years])

    for ytab, y in zip(year_tabs, years):
        with ytab:

            ydf = df[df["年"] == y]
            months = sorted(ydf["月"].unique())
            mtabs = st.tabs([f"{m}月" for m in months])

            for mtab, m in zip(mtabs, months):
                with mtab:

                    mdf = ydf[ydf["月"] == m].sort_values("日付")

                    for _, row in mdf.iterrows():

                        with st.container(border=True):
                        
                            st.markdown(f"### {row['項目']}")
                        
                            col1, col2 = st.columns([2,1])
                        
                            with col1:
                                st.write(f"📅 {row['日付'].strftime('%m/%d')}")
                                st.write(f"📂 {row['カテゴリ']}")
                        
                            with col2:
                                color = "red" if row["タイプ"] == "支出" else "green"
                                st.markdown(f"<h4 style='color:{color};'>¥{row['金額']:,}</h4>", unsafe_allow_html=True)
                        
                            col1, col2 = st.columns(2)
                        
                            if col1.button("削除", key=f"del_{row['id']}"):
                                supabase.table("kakeibo").delete().eq("id", row["id"]).execute()
                                st.cache_data.clear()
                                st.rerun()
                        
                            if col2.button("編集", key=f"edit_{row['id']}"):
                                st.session_state["edit_id"] = row["id"]

                        col1, col2 = st.columns(2)

                        # 削除
                        if col1.button("削除", key=f"del_{row['id']}"):
                            supabase.table("kakeibo").delete().eq("id", row["id"]).execute()
                            st.cache_data.clear()
                            st.rerun()

                        # 編集ボタン
                        if col2.button("編集", key=f"edit_{row['id']}"):
                            st.session_state["edit_id"] = row["id"]

                        st.divider()

# =========================
# 編集モード切り替え
# =========================
if "edit_id" in st.session_state:
    st.header("✏️ 編集モード")

    if st.button("← 一覧に戻る"):
        del st.session_state["edit_id"]
        st.rerun()

# =========================
# 編集フォーム
# =========================
if "edit_id" in st.session_state:

    edit_id = st.session_state["edit_id"]
    edit_row = df[df["id"] == edit_id].iloc[0]

    st.subheader("✏️ データ編集")

    new_date = st.date_input("日付", edit_row["日付"])
    new_item = st.text_input("項目", edit_row["項目"])
    new_amount = st.number_input("金額", value=int(edit_row["金額"]))

    # カテゴリはタイプに応じて切り替え
    if edit_row["タイプ"] == "支出":
        category_list = EXPENSE_CATEGORIES
    else:
        category_list = INCOME_CATEGORIES

    new_category = st.selectbox("カテゴリ", category_list, index=category_list.index(edit_row["カテゴリ"]))
    new_type = st.selectbox("タイプ", ["支出", "収入"], index=0 if edit_row["タイプ"]=="支出" else 1)

    col1, col2 = st.columns(2)

    if col1.button("更新"):
        supabase.table("kakeibo").update({
            "日付": str(new_date),
            "項目": new_item,
            "金額": int(new_amount),
            "カテゴリ": new_category,
            "タイプ": new_type
        }).eq("id", edit_id).execute()

        st.success("更新しました！")
        del st.session_state["edit_id"]
        st.cache_data.clear()
        st.rerun()

    if col2.button("キャンセル"):
        del st.session_state["edit_id"]
        st.rerun()
