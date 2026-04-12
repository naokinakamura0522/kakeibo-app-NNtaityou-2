import streamlit as st
import pandas as pd
from datetime import date
import os
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.font_manager as fm

# =========================
# 日本語フォント
# =========================
font_path = "NotoSansJP-Regular.ttf"

font_prop = None
if os.path.exists(font_path):
    font_prop = fm.FontProperties(fname=font_path)
    matplotlib.rcParams["font.family"] = font_prop.get_name()
    plt.rcParams["font.family"] = font_prop.get_name()
else:
    st.warning("⚠ 日本語フォントが見つかりません")

# =========================
# ページ設定
# =========================
st.set_page_config(page_title="家計簿アプリ", layout="centered")

# =========================
# ファイル設定
# =========================
DATA_FILE = "kakeibo.csv"
COLS = ["id", "日付", "項目", "金額", "カテゴリ", "タイプ"]

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
# CSV初期化
# =========================
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=COLS).to_csv(DATA_FILE, index=False)

# =========================
# データ読み込み（安全版）
# =========================
def load_data():
    df = pd.read_csv(DATA_FILE)

    if df.empty:
        return df

    # idを安全に整数化
    if "id" not in df.columns:
        df["id"] = range(len(df))
    else:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)

    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    df = df.dropna(subset=["日付"])
    df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0)

    return df

df = load_data()

# =========================
# タイトル
# =========================
st.title("💰 家計簿アプリ")

# =========================
# 残高
# =========================
income_total = df[df["タイプ"] == "収入"]["金額"].sum()
expense_total = df[df["タイプ"] == "支出"]["金額"].sum()

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

        # 🔥 最新CSVを再読み込み
        latest_df = load_data()

        if latest_df.empty:
            new_id = 0
        else:
            new_id = latest_df["id"].max() + 1

        new_row = pd.DataFrame(
            [[new_id, d, item, amount, category, st.session_state.type_radio]],
            columns=COLS
        )

        latest_df = pd.concat([latest_df, new_row], ignore_index=True)
        latest_df.to_csv(DATA_FILE, index=False)

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
# データ管理
# =========================
st.header("🗂 データ管理")

if not df.empty:

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

                        with st.container():
                            st.markdown(f"### {row['項目']}")
                            st.write(f"📅 {row['日付'].strftime('%m月%d日')}")
                            st.write(f"💰 ¥{row['金額']:,}")
                            st.write(f"📂 {row['カテゴリ']} / {row['タイプ']}")

                            c1, c2 = st.columns(2)

                            if c2.button("削除", key=f"del_{row['id']}"):
                                new_df = df[df["id"] != row["id"]]
                                new_df.to_csv(DATA_FILE, index=False)
                                st.rerun()

                        st.divider()
