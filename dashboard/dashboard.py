
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="E-Commerce Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 E-Commerce Analytics Dashboard")
st.caption("Analisis transaksi, kategori produk, pembayaran, dan ulasan pelanggan")

# Lokasi dataset relatif terhadap folder dashboard
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@st.cache_data
def load_data():
    files = {
        "orders": "orders_dataset.csv",
        "payments": "order_payments_dataset.csv",
        "items": "order_items_dataset.csv",
        "products": "products_dataset.csv",
        "categories": "product_category_name_translation.csv",
        "reviews": "order_reviews_dataset.csv",
    }

    data = {}
    for key, filename in files.items():
        path = DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {path}")
        data[key] = pd.read_csv(path)

    return data


try:
    data = load_data()
except Exception as e:
    st.error(f"Gagal memuat dataset: {e}")
    st.info("Periksa nama file CSV di folder data.")
    st.stop()

orders = data["orders"]
payments = data["payments"]
items = data["items"]
products = data["products"]
categories = data["categories"]
reviews = data["reviews"]

# Siapkan data pesanan dan pembayaran
orders["order_purchase_timestamp"] = pd.to_datetime(
    orders["order_purchase_timestamp"], errors="coerce"
)
orders["purchase_month"] = (
    orders["order_purchase_timestamp"].dt.to_period("M").astype(str)
)

monthly_orders = (
    orders.dropna(subset=["order_purchase_timestamp"])
    .groupby("purchase_month")["order_id"]
    .nunique()
    .reset_index(name="jumlah_pesanan")
)

order_month = orders[["order_id", "purchase_month"]].dropna()
order_payments = order_month.merge(payments, on="order_id", how="inner")

monthly_revenue = (
    order_payments.groupby("purchase_month")["payment_value"]
    .sum()
    .reset_index(name="total_pembayaran")
)

monthly = monthly_orders.merge(
    monthly_revenue, on="purchase_month", how="outer"
).fillna(0)

# Siapkan kategori produk
category_sales = (
    items.merge(
        products[["product_id", "product_category_name"]],
        on="product_id", how="left"
    )
    .merge(categories, on="product_category_name", how="left")
)

category_column = "product_category_name_english"
category_sales[category_column] = (
    category_sales[category_column].fillna("unknown")
)

# Filter periode
st.sidebar.header("Filter Dashboard")
months = sorted(monthly["purchase_month"].unique())
selected_months = st.sidebar.multiselect(
    "Pilih bulan",
    months,
    default=months
)

filtered_monthly = monthly[
    monthly["purchase_month"].isin(selected_months)
]

# Ringkasan utama
col1, col2, col3 = st.columns(3)

col1.metric(
    "Total pesanan",
    f"{int(filtered_monthly['jumlah_pesanan'].sum()):,}"
)
col2.metric(
    "Total nilai pembayaran",
    f"BRL {filtered_monthly['total_pembayaran'].sum():,.2f}"
)
col3.metric(
    "Total item terjual",
    f"{len(items):,}"
)

st.divider()

# Visualisasi 1
st.subheader("1. Tren Pesanan dan Pembayaran")

fig_orders = px.line(
    filtered_monthly,
    x="purchase_month",
    y="jumlah_pesanan",
    markers=True,
    title="Jumlah Pesanan per Bulan"
)
st.plotly_chart(fig_orders, use_container_width=True)

fig_revenue = px.line(
    filtered_monthly,
    x="purchase_month",
    y="total_pembayaran",
    markers=True,
    title="Total Nilai Pembayaran per Bulan"
)
st.plotly_chart(fig_revenue, use_container_width=True)

# Visualisasi 2
st.subheader("2. Performa Kategori Produk")

quantity = (
    category_sales.groupby(category_column)["order_item_id"]
    .count()
    .sort_values(ascending=False)
    .head(10)
    .reset_index(name="jumlah_item")
)

revenue = (
    category_sales.groupby(category_column)["price"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index(name="nilai_penjualan")
)

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(
        quantity.sort_values("jumlah_item"),
        x="jumlah_item",
        y=category_column,
        orientation="h",
        title="10 Kategori dengan Item Terjual Terbanyak"
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(
        revenue.sort_values("nilai_penjualan"),
        x="nilai_penjualan",
        y=category_column,
        orientation="h",
        title="10 Kategori dengan Nilai Penjualan Tertinggi"
    )
    st.plotly_chart(fig, use_container_width=True)

# Visualisasi 3
st.subheader("3. Metode Pembayaran dan Skor Ulasan")

col1, col2 = st.columns(2)

with col1:
    payment_counts = (
        payments.groupby("payment_type")
        .size()
        .reset_index(name="jumlah")
    )
    fig = px.pie(
        payment_counts,
        names="payment_type",
        values="jumlah",
        title="Distribusi Metode Pembayaran"
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    review_counts = (
        reviews.groupby("review_score")
        .size()
        .reset_index(name="jumlah")
        .sort_values("review_score")
    )
    fig = px.bar(
        review_counts,
        x="review_score",
        y="jumlah",
        title="Distribusi Skor Ulasan",
        labels={
            "review_score": "Skor Ulasan",
            "jumlah": "Jumlah Ulasan"
        }
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Catatan: nilai pembayaran merupakan total payment_value, "
    "bukan keuntungan bersih. Data pada periode yang belum lengkap "
    "perlu ditafsirkan secara hati-hati."
)
