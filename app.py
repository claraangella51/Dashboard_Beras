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

# =====================================================
# LOAD GAP DATA (HEATMAP)
# =====================================================
@st.cache_data
def load_gap_data():
    df = pd.read_csv("gap_per_provinsi.csv")
    gdf = gpd.read_file("indonesia.geojson")

    # Normalisasi nama provinsi
    gdf["state"] = gdf["state"].str.upper().str.strip()

    return df, gdf

gap_df, gdf = load_gap_data()

# =====================================================
# LOAD PRODUKSI DATA
# =====================================================
@st.cache_data
def load_produksi():
    df = pd.read_csv("Produksi.csv")  # sesuaikan path CSV kamu
    df.columns = df.columns.str.strip()
    return df

df_long = load_produksi()  # Load dulu sebelum pakai

# Standardisasi nama kolom utama
rename_map = {}
for col in df_long.columns:
    col_lower = col.lower()
    if "luas" in col_lower and "panen" in col_lower:
        rename_map[col] = "luas_panen_ha"
    elif "produksi" in col_lower:
        rename_map[col] = "produksi_ton"
    elif "produktif" in col_lower:
        rename_map[col] = "produktivitaskuha"

df_long = df_long.rename(columns=rename_map)

# Cek kolom yang dibutuhkan
required_cols = ["luas_panen_ha", "produktivitaskuha", "produksi_ton", "tahun", "provinsi"]
missing_cols = [c for c in required_cols if c not in df_long.columns]
if missing_cols:
    st.error(f"Kolom berikut tidak ditemukan: {missing_cols}")
    st.stop()

df_long = df_long.dropna(subset=required_cols)

# =====================================================
# HEATMAP PETA INDONESIA
# =====================================================
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

# =====================================================
# REGRESI LINIER
# =====================================================
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

# =====================================================
# SIDEBAR FILTER
# =====================================================
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

# =====================================================
# SCATTER PLOT
# =====================================================
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

# =====================================================
# TABEL PROVINSI PRODUKSI RENDAH
# =====================================================
st.subheader("📉 Provinsi dengan Produksi di Bawah Prediksi")

st.dataframe(
    df_plot[df_plot["status"] == "Rendah dari Prediksi"]
    .sort_values("selisih")
    .reset_index(drop=True)
)
