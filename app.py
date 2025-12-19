import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from sklearn.linear_model import LinearRegression
import numpy as np
import os

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="Dashboard Pangan Indonesia", layout="wide")
st.title("📊 Dashboard Produksi & Gap Supply–Demand Beras Indonesia")

# =============================
# LOAD HEATMAP DATA
# =============================
@st.cache_data
def load_gap_data():
    try:
        df = pd.read_csv("gap_per_provinsi.csv")
        gdf = gpd.read_file("indonesia.geojson")
        return df, gdf
    except FileNotFoundError as e:
        st.error(f"File not found: {e.filename}")
        st.stop()

gap_df, gdf = load_gap_data()

# =============================
# HEATMAP
# =============================
st.subheader("🗺️ Heatmap Gap Supply–Demand Beras")

year_gap = st.slider(
    "Pilih Tahun untuk Heatmap",
    min_value=int(gap_df["Tahun"].min()),
    max_value=int(gap_df["Tahun"].max()),
    value=int(gap_df["Tahun"].min()),
    step=1
)

df_year = gap_df[gap_df["Tahun"]==year_gap].drop(columns="Tahun").T.reset_index()
df_year.columns = ["state","Gap_ton"]
df_year["state"] = df_year["state"].str.upper().str.strip()
gdf["state"] = gdf["state"].str.upper().str.strip()
gdf_merge = gdf.merge(df_year, on="state", how="left")

m = folium.Map(location=[-2.5, 118], zoom_start=5, tiles="cartodbpositron")
folium.Choropleth(
    geo_data=gdf_merge,
    data=gdf_merge,
    columns=["state","Gap_ton"],
    key_on="feature.properties.state",
    fill_color="YlOrRd",
    fill_opacity=0.8,
    line_opacity=0.2,
    nan_fill_color="lightgrey",
    legend_name="Gap Supply–Demand (ton)"
).add_to(m)
folium.GeoJson(
    gdf_merge,
    tooltip=folium.GeoJsonTooltip(
        fields=["state","Gap_ton"],
        aliases=["Provinsi","Gap (ton)"],
        localize=True
    )
).add_to(m)
st_folium(m, width=1400, height=700)

# =============================
# LOAD PRODUKSI DATA (WIDE → LONG)
# =============================
@st.cache_data
def load_produksi(csv_file="Produksi.csv"):
    BASE_DIR = os.path.dirname(__file__)
    csv_path = os.path.join(BASE_DIR, csv_file)
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        st.error(f"File not found: {csv_path}")
        st.stop()

    # Normalisasi kolom
    df.columns = (
        df.columns.str.strip()
                  .str.replace(" ", "_")
                  .str.replace(r"[^\w]", "", regex=True)
                  .str.lower()
    )
    st.write("Kolom setelah normalisasi:", df.columns.tolist())

    if "provinsi" not in df.columns:
        st.error("Kolom 'provinsi' tidak ditemukan")
        st.stop()

    # Melt wide → long
    df_long = pd.wide_to_long(
        df,
        stubnames=["luas_panen_ha","produktivitaskuha","produksi_ton"],
        i="provinsi",
        j="tahun",
        sep="",
        suffix=r"\d+"
    ).reset_index()

    # Pastikan numeric
    df_long["luas_panen_ha"] = pd.to_numeric(df_long["luas_panen_ha"], errors="coerce")
    df_long["produktivitaskuha"] = pd.to_numeric(df_long["produktivitaskuha"], errors="coerce")
    df_long["produksi_ton"] = pd.to_numeric(df_long["produksi_ton"], errors="coerce")
    df_long["tahun"] = pd.to_numeric(df_long["tahun"], errors="coerce") + 2017  # suffix 1 = 2018

    return df_long

df_long = load_produksi()

# =============================
# LINEAR REGRESSION
# =============================
X = df_long[["luas_panen_ha","produktivitaskuha"]]
y = df_long["produksi_ton"]
model = LinearRegression()
model.fit(X, y)

df_long["produksi_prediksi"] = model.predict(X)
df_long["selisih"] = df_long["produksi_ton"] - df_long["produksi_prediksi"]
df_long["status"] = np.where(df_long["selisih"]<0,"Rendah dari Prediksi","Sesuai/Diatas Prediksi")

# =============================
# SIDEBAR: Tahun & Provinsi
# =============================
st.sidebar.subheader("Filter Data Produksi")
tahun_sel = st.sidebar.slider(
    "Pilih Tahun",
    min_value=int(df_long["tahun"].min()),
    max_value=int(df_long["tahun"].max()),
    value=int(df_long["tahun"].min())
)

provinsi_list = df_long["provinsi"].unique().tolist()
selected_provinsi = st.sidebar.multiselect(
    "Pilih Provinsi",
    options=provinsi_list,
    default=provinsi_list
)

df_plot = df_long[(df_long["tahun"]==tahun_sel) & (df_long["provinsi"].isin(selected_provinsi))]

# =============================
# SCATTER PLOT
# =============================
st.subheader(f"📈 Produksi vs Luas Lahan & Produktivitas ({tahun_sel})")
fig = px.scatter(
    df_plot,
    x="luas_panen_ha",
    y="produksi_ton",
    size="produktivitaskuha",
    color="status",
    hover_data=["provinsi","produksi_prediksi","selisih","produktivitaskuha","luas_panen_ha"],
    size_max=35,
    color_discrete_map={"Rendah dari Prediksi":"red","Sesuai/Diatas Prediksi":"green"}
)
fig.update_layout(
    xaxis_title="Luas Panen (ha)",
    yaxis_title="Produksi (ton)",
    legend_title="Status Produksi",
    width=1200,
    height=800
)
st.plotly_chart(fig, use_container_width=True)

# =============================
# TABEL PRODUKSI RENDAH
# =============================
st.subheader("Provinsi Produksi Rendah Dibanding Prediksi")
st.dataframe(
    df_plot[df_plot["status"]=="Rendah dari Prediksi"]
    .sort_values("selisih")
    .reset_index(drop=True)
)
