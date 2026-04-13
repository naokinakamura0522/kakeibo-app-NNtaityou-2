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
# 残高
# =========================
if not df.empty:
    income_total = df[df["タイプ"] == "収入"]["金額"].sum()
    expense_total = df[df["タイプ"] == "支出"]["金額"].sum()
else:
    income_total = 0
    expense_total = 0

st.metric("残高", f"{income_total - expense_total:,.0f} 円")
st.write(f"収入：{income_total:,.0f} 円")
st.write(f"支出：{expense_total:,.0f} 円")

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

exp = df[df["タイプ"] == "支出"].copy()

if not exp.empty:
    exp["年月"] = exp["日付"].dt.to_period("M").astype(str)
    months = sorted(exp["年月"].unique(), reverse=True)
    m = st.selectbox("月選択", months)

    mdf = exp[exp["年月"] == m]
    pie = mdf.groupby("カテゴリ")["金額"].sum().reindex(EXPENSE_CATEGORIES).fillna(0)

    colors = [CATEGORY_COLORS[c] for c in pie.index]

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
# データ削除
# =========================
st.header("🗂 データ管理")

if not df.empty:
    for _, row in df.sort_values("日付").iterrows():

        with st.container():
            st.markdown(f"### {row['項目']}")
            st.write(f"📅 {row['日付'].strftime('%m月%d日')}")
            st.write(f"💰 ¥{row['金額']:,}")
            st.write(f"📂 {row['カテゴリ']} / {row['タイプ']}")

            if st.button("削除", key=f"del_{row['id']}"):
                supabase.table("kakeibo").delete().eq("id", row["id"]).execute()
                st.cache_data.clear()
                st.rerun()

        st.divider()
