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
font_candidates = [
    "C:/Windows/Fonts/msgothic.ttc",
    "C:/Windows/Fonts/meiryo.ttc",
    "/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
]

for font in font_candidates:
    if os.path.exists(font):
        matplotlib.rcParams["font.family"] = fm.FontProperties(fname=font).get_name()
        break

matplotlib.rcParams["axes.unicode_minus"] = False

# =========================
# ファイル設定
# =========================
DATA_FILE = "kakeibo.csv"
COLS = ["id", "日付", "項目", "金額", "カテゴリ", "タイプ"]

# =========================
# カテゴリ定義
# =========================
EXPENSE_CATEGORIES = [
    "外食費", "食材費", "交通費", "娯楽", "日用品", "その他支出"
]

INCOME_CATEGORIES = [
    "給料", "ボーナス", "副業", "お小遣い", "その他収入"
]

ALL_CATEGORY_ORDER = list(dict.fromkeys(
    EXPENSE_CATEGORIES + INCOME_CATEGORIES
))

# =========================
# カラー固定
# =========================
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
# 読み込み
# =========================
df = pd.read_csv(DATA_FILE)
df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

for c in COLS:
    if c not in df.columns:
        df[c] = None

# ID再生成（重複防止）
df = df.reset_index(drop=True)
df["id"] = df.index

# 型整形
df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
df = df.dropna(subset=["日付"])
df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0)

df["カテゴリ"] = df["カテゴリ"].astype(str).str.strip()
df.loc[~df["カテゴリ"].isin(ALL_CATEGORY_ORDER), "カテゴリ"] = "その他支出"

df["カテゴリ"] = pd.Categorical(
    df["カテゴリ"],
    categories=ALL_CATEGORY_ORDER,
    ordered=True
)

df.to_csv(DATA_FILE, index=False)

# =========================
# タイトル
# =========================
st.title("💰 家計簿アプリ")

# =========================
# 残高表示
# =========================
income_total = df[df["タイプ"] == "収入"]["金額"].sum()
expense_total = df[df["タイプ"] == "支出"]["金額"].sum()
balance = income_total - expense_total

st.metric("現在の残高", f"{balance:,.0f} 円")
st.write(f"収入合計：{income_total:,.0f} 円")
st.write(f"支出合計：{expense_total:,.0f} 円")

st.divider()

# =========================
# データ追加
# =========================
st.header("データ追加")

if "ttype" not in st.session_state:
    st.session_state.ttype = "支出"

def change_type():
    st.session_state.ttype = st.session_state.type_radio

st.radio("タイプ", ["支出", "収入"], key="type_radio", on_change=change_type)

category_list = EXPENSE_CATEGORIES if st.session_state.ttype == "支出" else INCOME_CATEGORIES

with st.form("add_form"):
    d = st.date_input("日付", value=date.today())
    item = st.text_input("項目")
    amount = st.number_input("金額", min_value=0)
    category = st.selectbox("カテゴリ", category_list)
    submitted = st.form_submit_button("追加")

    if submitted:
        new_id = df["id"].max() + 1 if not df.empty else 0
        new_row = pd.DataFrame(
            [[new_id, pd.to_datetime(d), item, amount, category, st.session_state.ttype]],
            columns=COLS
        )
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.rerun()

# =========================
# 月別集計（年タブ）
# =========================
st.header("📊 月別集計")

if not df.empty:

    df["年"] = df["日付"].dt.year
    df["月"] = df["日付"].dt.month

    years = sorted(df["年"].unique(), reverse=True)
    tabs = st.tabs([f"{y}年" for y in years])

    for tab, year in zip(tabs, years):
        with tab:
            year_df = df[df["年"] == year]

            month_summary = (
                year_df
                .pivot_table(
                    index="月",
                    columns="タイプ",
                    values="金額",
                    aggfunc="sum",
                    fill_value=0
                )
                .sort_index()
            )

            st.dataframe(month_summary)

            if "収入" in month_summary.columns:
                st.subheader("収入（月別）")
                st.bar_chart(month_summary["収入"])

            if "支出" in month_summary.columns:
                st.subheader("支出（月別）")
                st.bar_chart(month_summary["支出"])

st.divider()

# =========================
# 月別支出円グラフ
# =========================
st.header("🥧 支出カテゴリ内訳（月別）")

expense_df = df[df["タイプ"] == "支出"].copy()

if not expense_df.empty:
    expense_df["年月"] = expense_df["日付"].dt.to_period("M").astype(str)
    month_list = sorted(expense_df["年月"].unique(), reverse=True)
    selected_month = st.selectbox("表示する月", month_list)

    month_data = expense_df[expense_df["年月"] == selected_month]

    pie_data = (
        month_data.groupby("カテゴリ", observed=False)["金額"]
        .sum()
        .reindex(EXPENSE_CATEGORIES)
        .fillna(0)
    )

    colors = [CATEGORY_COLORS.get(cat, "#D3D3D3") for cat in pie_data.index]

    fig, ax = plt.subplots()
    ax.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%", startangle=90, colors=colors)
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

    for ytab, year in zip(year_tabs, years):
        with ytab:

            year_df = df[df["年"] == year]
            months = sorted(year_df["月"].unique())
            month_tabs = st.tabs([f"{m}月" for m in months])

            for mtab, month in zip(month_tabs, months):
                with mtab:

                    month_df = year_df[year_df["月"] == month].sort_values("日付")

                    for i, row in month_df.iterrows():
                        cols = st.columns([2,2,2,2,2,1])
                        cols[0].write(row["日付"].strftime("%m月%d日"))
                        cols[1].write(row["項目"])
                        cols[2].write(f"¥{row['金額']:,}")
                        cols[3].write(row["タイプ"])
                        cols[4].write(row["カテゴリ"])

                        if cols[5].button("削除", key=f"del_{year}_{month}_{i}"):
                            df = df[df["id"] != row["id"]]
                            df.to_csv(DATA_FILE, index=False)
                            st.rerun()
