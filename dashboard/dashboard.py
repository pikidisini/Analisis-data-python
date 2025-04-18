import pandas as pd
import streamlit as st
import plotly.express as px
import folium
from folium.plugins import MarkerCluster
from streamlit.components.v1 import html

# Load data
orders_df_clean = pd.read_csv('dashboard/orders_df_clean.csv')  
order_items_df = pd.read_csv('dashboard/order_items_df.csv')    
customers_df = pd.read_csv('dashboard/customers_df.csv')        
products_df = pd.read_csv('dashboard/products_df.csv') 
geolocation_df = pd.read_csv('dashboard/geolocation_df.csv')           
product_cat_translation_df = pd.read_csv('.data/product_category_name_translation.csv')      
rfm = pd.read_csv('dashboard/rfm.csv') 

# Ubah tipe data order_purchase_timestamp menjadi datetime
orders_df_clean['order_purchase_timestamp'] = pd.to_datetime(orders_df_clean['order_purchase_timestamp'])

# Gabungkan beberapa dataframe yang dibutuhkan
orders_items_products_df = pd.merge(order_items_df, products_df, on='product_id')
orders_full_df = pd.merge(orders_df_clean, customers_df, on='customer_id')
orders_full_df = pd.merge(orders_full_df, orders_items_products_df, on='order_id')
orders_full_df = pd.merge(orders_full_df, product_cat_translation_df, on='product_category_name', how='left')
orders_full_df = pd.merge(orders_full_df, rfm, on='customer_id', how='left')

st.sidebar.header("Filter")

# Filter berdasarkan rentang waktu
min_date = orders_full_df['order_purchase_timestamp'].min().date()
max_date = orders_full_df['order_purchase_timestamp'].max().date()

start_date = st.sidebar.date_input("Tanggal Mulai", min_date)
end_date = st.sidebar.date_input("Tanggal Akhir", max_date)

# Konversi tanggal yang dipilih menjadi datetime untuk filtering
start_datetime = pd.to_datetime(start_date)
end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1) # Include end date fully

filtered_df_time = orders_full_df[(orders_full_df['order_purchase_timestamp'] >= start_datetime) &
                                   (orders_full_df['order_purchase_timestamp'] <= end_datetime)]

# Filter berdasarkan kategori produk
product_categories = filtered_df_time['product_category_name_english'].dropna().unique()
all_categories_option = "Pilih Semua Kategori"
categories_with_all = [all_categories_option] + list(product_categories)

# Jika ada kategori spesifik yang dipilih, kita tidak menyertakan "Pilih Semua" sebagai default
default_categories = [all_categories_option] if not st.session_state.get('specific_category_selected', False) else []
selected_categories = st.sidebar.multiselect("Pilih Kategori Produk", categories_with_all, default=default_categories)

if all_categories_option in selected_categories and len(selected_categories) > 1:
    selected_categories.remove(all_categories_option)
    filtered_categories = selected_categories
elif not selected_categories:
    filtered_categories = list(product_categories)
elif all_categories_option in selected_categories and len(selected_categories) == 1:
    filtered_categories = product_categories
else:
    filtered_categories = selected_categories



filtered_df = filtered_df_time[filtered_df_time['product_category_name_english'].isin(filtered_categories)]

# Gunakan dataframe asli jika tidak ada filter rentang waktu DAN kategori yang diterapkan
first_date = orders_full_df['order_purchase_timestamp'].min().date()
last_date = orders_full_df['order_purchase_timestamp'].max().date()

time_filter_default = (start_date == first_date and end_date == last_date)
category_filter_default = (all_categories_option in selected_categories or not selected_categories)

if time_filter_default and category_filter_default:
    df_to_visualize = orders_full_df.copy()
else:
    df_to_visualize = filtered_df.copy()

# ==============================================================================
# VISUALISASI
# ==============================================================================

st.subheader("1. Performa Penjualan dari Waktu ke Waktu")

# Pilihan granularitas waktu
time_granularity = st.radio(
    "Pilih Granularitas Waktu:",
    ('Harian', 'Mingguan', 'Bulanan', 'Tahunan'),
    horizontal=True
)

# Agregasi data berdasarkan granularitas waktu yang dipilih
if time_granularity == 'Harian':
    daily_sales = df_to_visualize.resample('D', on='order_purchase_timestamp').agg(
        total_order=('order_id', 'nunique'),
        total_revenue=('price', 'sum')
    ).reset_index()
    fig_orders = px.line(daily_sales, x='order_purchase_timestamp', y='total_order', title='Total Order Harian')
    fig_revenue = px.line(daily_sales, x='order_purchase_timestamp', y='total_revenue', title='Total Revenue Harian')
elif time_granularity == 'Mingguan':
    weekly_sales = df_to_visualize.resample('W', on='order_purchase_timestamp').agg(
        total_order=('order_id', 'nunique'),
        total_revenue=('price', 'sum')
    ).reset_index()
    fig_orders = px.line(weekly_sales, x='order_purchase_timestamp', y='total_order', title='Total Order Mingguan')
    fig_revenue = px.line(weekly_sales, x='order_purchase_timestamp', y='total_revenue', title='Total Revenue Mingguan')
elif time_granularity == 'Bulanan':
    monthly_sales = df_to_visualize.resample('M', on='order_purchase_timestamp').agg(
        total_order=('order_id', 'nunique'),
        total_revenue=('price', 'sum')
    ).reset_index()
    fig_orders = px.line(monthly_sales, x='order_purchase_timestamp', y='total_order', title='Total Order Bulanan')
    fig_revenue = px.line(monthly_sales, x='order_purchase_timestamp', y='total_revenue', title='Total Revenue Bulanan')
elif time_granularity == 'Tahunan':
    yearly_sales = df_to_visualize.resample('Y', on='order_purchase_timestamp').agg(
        total_order=('order_id', 'nunique'),
        total_revenue=('price', 'sum')
    ).reset_index()
    fig_orders = px.line(yearly_sales, x='order_purchase_timestamp', y='total_order', title='Total Order Tahunan')
    fig_revenue = px.line(yearly_sales, x='order_purchase_timestamp', y='total_revenue', title='Total Revenue Tahunan')

st.plotly_chart(fig_orders, use_container_width=True)
st.plotly_chart(fig_revenue, use_container_width=True)

st.subheader("2. Performa Penjualan Berdasarkan Lokasi Geografis")

# Ambil koordinat unik tiap kota
city_coords = geolocation_df.groupby('geolocation_city').agg({
    'geolocation_lat': 'mean',
    'geolocation_lng': 'mean'
}).reset_index()
city_coords.rename(columns={'geolocation_city': 'customer_city'}, inplace=True)

# Agregasi performa penjualan per kota (pastikan 'df_to_visualize' sudah didefinisikan)
city_performance = df_to_visualize.groupby('customer_city').agg(
    total_orders=('order_id', 'nunique'),
    total_revenue=('price', 'sum')
).reset_index()

# Gabungkan koordinat dengan performa kota
city_geo_performance = pd.merge(city_performance, city_coords, on='customer_city', how='left')
city_geo_performance.dropna(subset=['geolocation_lat', 'geolocation_lng'], inplace=True) # Handle kota tanpa koordinat

# Inisialisasi peta Brazil
m = folium.Map(location=[-14.2350, -51.9253], zoom_start=4)

# Tambahkan marker cluster
marker_cluster = MarkerCluster().add_to(m)

# Looping kota dan buat marker
for _, row in city_geo_performance.iterrows():
    folium.CircleMarker(
        location=[row['geolocation_lat'], row['geolocation_lng']],
        radius=5 + (row['total_revenue'] / city_geo_performance['total_revenue'].max()) * 10 if city_geo_performance['total_revenue'].max() > 0 else 5,
        popup=(f"Kota: {row['customer_city']}<br>"
               f"Total Order: {row['total_orders']}<br>"
               f"Pendapatan: {row['total_revenue']:.2f}"),
        color='blue',
        fill=True,
        fill_opacity=0.6
    ).add_to(marker_cluster)

# Simpan peta ke HTML string
map_html = m._repr_html_()

# Tampilkan peta di Streamlit
html(map_html, height=500)


# Agregasi data per kota pelanggan
city_sales = df_to_visualize.groupby('customer_city').agg(
    total_order=('order_id', 'nunique'),
    total_revenue=('price', 'sum')
).sort_values(by='total_order', ascending=False).head(10).reset_index()

# Bar chart untuk total order per kota
fig_city_orders = px.bar(city_sales, x='customer_city', y='total_order',
                             title='Top 10 Kota Berdasarkan Total Order')
st.plotly_chart(fig_city_orders, use_container_width=True)

# Bar chart untuk total revenue per kota
city_revenue = df_to_visualize.groupby('customer_city').agg(
    total_revenue=('price', 'sum')
).sort_values(by='total_revenue', ascending=False).head(10).reset_index()
fig_city_revenue = px.bar(city_revenue, x='customer_city', y='total_revenue',
                              title='Top 10 Kota Berdasarkan Total Revenue')
st.plotly_chart(fig_city_revenue, use_container_width=True)

st.subheader("3. Kategori Produk Terlaris dan Penghasil Revenue Terbesar")
# Agregasi data per kategori produk
category_sales = df_to_visualize.groupby('product_category_name_english').agg(
    total_order=('order_id', 'nunique'),
    total_revenue=('price', 'sum')
).sort_values(by='total_order', ascending=False).reset_index()

# Bar chart untuk total order per kategori
fig_category_orders = px.bar(category_sales.head(10), x='product_category_name_english', y='total_order',
                             title='10 Kategori Produk Terlaris')
st.plotly_chart(fig_category_orders, use_container_width=True)

# Bar chart untuk total revenue per kategori
category_revenue = category_sales.sort_values(by='total_revenue', ascending=False)
fig_category_revenue = px.bar(category_revenue.head(10), x='product_category_name_english', y='total_revenue',
                              title='10 Kategori Produk dengan Revenue Terbesar')
st.plotly_chart(fig_category_revenue, use_container_width=True)

st.subheader("4. Distribusi Segmen Pelanggan RFM per Kategori Produk dan Regional")

# Pastikan RFM_Label dan customer_city serta product_category_name_english tidak NaN
rfm_category_city_df = df_to_visualize.dropna(subset=['RFM_Label', 'product_category_name_english', 'customer_city'])

# Grouped bar chart untuk distribusi RFM Label per kategori produk
rfm_category_counts = rfm_category_city_df.groupby(['product_category_name_english', 'RFM_Label']).size().reset_index(name='count')
fig_rfm_category = px.bar(rfm_category_counts, x='product_category_name_english', y='count', color='RFM_Label',
                          title='Distribusi RFM Label per Kategori Produk',
                          labels={'count': 'Jumlah Pelanggan', 'product_category_name_english': 'Kategori Produk'})
st.plotly_chart(fig_rfm_category, use_container_width=True)

# Grouped bar chart untuk distribusi RFM Label per kota pelanggan (Top 10)
top_cities = rfm_category_city_df['customer_city'].value_counts().nlargest(10).index
rfm_top_city_df = rfm_category_city_df[rfm_category_city_df['customer_city'].isin(top_cities)]
rfm_city_counts = rfm_top_city_df.groupby(['customer_city', 'RFM_Label']).size().reset_index(name='count')
fig_rfm_city = px.bar(rfm_city_counts, x='customer_city', y='count', color='RFM_Label',
                       title='Distribusi RFM Label per 10 Kota Teratas',
                       labels={'count': 'Jumlah Pelanggan', 'customer_city': 'Kota Pelanggan'})
st.plotly_chart(fig_rfm_city, use_container_width=True)