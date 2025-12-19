import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from sklearn.linear_model import LinearRegression
import numpy as np

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(
    page_title="Dashboard Pangan Indonesia",
    layout="wide"
)
st.title("📊 Dashboard Produksi & Gap Supply–Demand Beras Indonesia")

# =============================
# LOAD GAP DATA (HEATMAP)
# =============================
@st.cache_data
def load_gap_data():
    df = pd.read_csv("gap_per_provinsi.csv")
    gdf = gpd.read_file("indonesia.geojson")

    # Normalisasi nama provinsi
    gdf["state"] = gdf["state"].str.upper().str.strip()

    return df, gdf

gap_df, gdf = load_gap_data()

# =============================
# LOAD PRODUKSI DATA (wide → long)
# =============================
@st.cache_data
def load_produksi():
    df = pd.read_csv("produksi_rice.csv")

    # Ambil list tahun dari header (asumsi ada di header)
    tahun = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
    dfs = []
    for t in tahun:
        cols = [f"Luas Panen (ha)_{t}", f"Produktivitas (ku/ha)_{t}", f"Produksi (ton)_{t}"]
        # Jika header CSV tanpa _tahun, sesuaikan saja
        if all(c in df.columns for c in cols):
            temp = df[["Provinsi"] + cols].copy()
            temp.columns = ["provinsi", "luas_panen_ha", "produktivitaskuha", "produksi_ton"]
            temp["tahun"] = t
            dfs.append(temp)
    df_long = pd.concat(dfs, ignore_index=True)

    # Normalisasi provinsi
    df_long["provinsi"] = df_long["provinsi"].str.upper().str.strip()

    # Pastikan numeric
    df_long["luas_panen_ha"] = pd.to_numeric(df_long["luas_panen_ha"], errors="coerce")
    df_long["produktivitaskuha"] = pd.to_numeric(df_long["produktivitaskuha"], errors="coerce")
    df_long["produksi_ton"] = pd.to_numeric(df_long["produksi_ton"], errors="coerce")

    return df_long.dropna(subset=["luas_panen_ha", "produktivitaskuha", "produksi_ton"])

df_long = load_produksi()

# =============================
# HEATMAP PETA INDONESIA
# =============================
st.subheader("🗺️ Heatmap Gap Supply–Demand Beras")

year_gap = st.slider(
    "Pilih Tahun",
    min_value=int(gap_df["Tahun"].min()),
    max_value=int(gap_df["Tahun"].max()),
    value=int(gap_df["Tahun"].min()),
    step=1
)

# Wide → Long untuk tahun terpilih
df_year = (
    gap_df[gap_df["Tahun"] == year_gap]
    .drop(columns="Tahun")
    .T
    .reset_index()
)
df_year.columns = ["state", "Gap_ton"]
df_year["state"] = df_year["state"].str.upper().str.strip()

# Merge ke peta
gdf_merge = gdf.merge(df_year, on="state", how="left")

# Folium Map
m = folium.Map(
    location=[-2.5, 118],
    zoom_start=5,
    tiles="cartodbpositron"
)

folium.Choropleth(
    geo_data=gdf_merge,
    data=gdf_merge,
    columns=["state", "Gap_ton"],
    key_on="feature.properties.state",
    fill_color="YlOrRd",
    fill_opacity=0.85,
    line_opacity=0.3,
    nan_fill_color="lightgrey",
    legend_name="Gap Supply–Demand (ton)"
).add_to(m)

folium.GeoJson(
    gdf_merge,
    tooltip=folium.GeoJsonTooltip(
        fields=["state", "Gap_ton"],
        aliases=["Provinsi", "Gap (ton)"],
        localize=True
    )
).add_to(m)

st_folium(m, width=1400, height=700)

# =============================
# REGRESI LINIER
# =============================
X = df_long[["luas_panen_ha", "produktivitaskuha"]]
y = df_long["produksi_ton"]

model = LinearRegression()
model.fit(X, y)

df_long["produksi_prediksi"] = model.predict(X)
df_long["selisih"] = df_long["produksi_ton"] - df_long["produksi_prediksi"]
df_long["status"] = np.where(
    df_long["selisih"] < 0,
    "Rendah dari Prediksi",
    "Sesuai / Di atas Prediksi"
)

# =============================
# SIDEBAR FILTER
# =============================
st.sidebar.subheader("Filter Data Produksi")

tahun_sel = st.sidebar.slider(
    "Pilih Tahun",
    min_value=int(df_long["tahun"].min()),
    max_value=int(df_long["tahun"].max()),
    value=int(df_long["tahun"].min())
)

provinsi_list = sorted(df_long["provinsi"].unique())
selected_provinsi = st.sidebar.multiselect(
    "Pilih Provinsi",
    options=provinsi_list,
    default=provinsi_list
)

df_plot = df_long[
    (df_long["tahun"] == tahun_sel) &
    (df_long["provinsi"].isin(selected_provinsi))
]

# =============================
# SCATTER PLOT
# =============================
st.subheader(f"📈 Produksi vs Luas Panen & Produktivitas ({tahun_sel})")

fig = px.scatter(
    df_plot,
    x="luas_panen_ha",
    y="produksi_ton",
    size="produktivitaskuha",
    color="status",
    hover_data=[
        "provinsi",
        "produksi_prediksi",
        "selisih",
        "produktivitaskuha",
        "luas_panen_ha"
    ],
    size_max=35,
    color_discrete_map={
        "Rendah dari Prediksi": "red",
        "Sesuai / Di atas Prediksi": "green"
    }
)

fig.update_layout(
    xaxis_title="Luas Panen (ha)",
    yaxis_title="Produksi (ton)",
    legend_title="Status Produksi",
    height=750
)

st.plotly_chart(fig, use_container_width=True)

# =============================
# TABEL PROVINSI PRODUKSI RENDAH
# =============================
st.subheader("📉 Provinsi dengan Produksi di Bawah Prediksi")

st.dataframe(
    df_plot[df_plot["status"] == "Rendah dari Prediksi"]
    .sort_values("selisih")
    .reset_index(drop=True)
)
