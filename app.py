import streamlit as st
import folium
import branca.colormap as cm
from streamlit_folium import st_folium
import pandas as pd
import geopandas as gpd

# --- Load your data ---
try:
    data = pd.read_csv("data_nasional.csv")
except FileNotFoundError:
    st.error("File not found. Make sure 'data_nasional.csv' is in the same folder as app.py.")
    st.stop()

# --- Debug DataFrame columns ---
st.write("Columns in your dataset:", list(data.columns))

# --- Optional: Wrap session_state access ---
def safe_get(key, default=None):
    if key not in st.session_state:
        st.warning(f"'{key}' not found in session_state, using default={default}")
        st.session_state[key] = default
    return st.session_state[key]

# Example usage:
tahun = safe_get('tahun', 2025)

# --- Rest of your Streamlit code ---
try:
    # Access your columns safely
    total_produksi = data['produksi_ton'].sum()
except KeyError as e:
    st.error(f"Column {e} not found in your DataFrame. Check spelling!")
    st.stop()


st.set_page_config(layout="wide")
st.title("Peta Gap Supply–Demand per Provinsi")

# ===============================
# LOAD DATA
# ===============================
@st.cache_data
def load_data():
    df = pd.read_csv("gap_per_provinsi.csv")        # state | Tahun | Gap_ton
    gdf = gpd.read_file("indonesia.geojson") # state | geometry
    return df, gdf

df_long, gdf_map = load_data()

# ===============================
# NORMALISASI KOLOM (AMAN)
# ===============================
df_long.columns = df_long.columns.str.strip()
gdf_map.columns = gdf_map.columns.str.strip()

# ===============================
# SLIDER TAHUN
# ===============================
year = st.slider(
    "Pilih Tahun",
    int(df_long["Tahun"].min()),
    int(df_long["Tahun"].max()),
    int(df_long["Tahun"].min())
)

# ===============================
# FILTER & MERGE (PAKAI state)
# ===============================
df_year = df_long[df_long["Tahun"] == year]

gdf_year = gdf_map.merge(
    df_year,
    on="state",
    how="left"
)

# ===============================
# COLORMAP
# ===============================
colormap = cm.linear.YlOrRd_09.scale(
    gdf_year["Gap_ton"].min(),
    gdf_year["Gap_ton"].max()
)
colormap.caption = f"Gap Supply–Demand (ton) — {year}"

# ===============================
# MAP
# ===============================
m = folium.Map(
    location=[-2.5, 118],
    zoom_start=5,
    tiles="cartodbpositron"
)

folium.GeoJson(
    gdf_year,
    style_function=lambda feature: {
        "fillColor": colormap(
            feature["properties"]["Gap_ton"]
        ) if feature["properties"]["Gap_ton"] is not None else "#cccccc",
        "color": "black",
        "weight": 0.5,
        "fillOpacity": 0.8,
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["state", "Gap_ton"],
        aliases=["Provinsi", "Gap (ton)"],
        localize=True
    ),
    highlight_function=lambda x: {
        "weight": 2,
        "color": "blue"
    }
).add_to(m)

colormap.add_to(m)

# ===============================
# MAP + CLICK
# ===============================
map_data = st_folium(
    m,
    width=1100,
    height=550,
    returned_objects=["last_active_drawing"]
)

# ===============================
# BREAKDOWN OTOMATIS
# ===============================
st.subheader("Breakdown Provinsi")

prov_clicked = None
if map_data and map_data.get("last_active_drawing"):
    prov_clicked = map_data["last_active_drawing"]["properties"].get("state")

if prov_clicked:
    st.success(f"Provinsi dipilih: **{prov_clicked}**")

    df_prov = df_long[df_long["state"] == prov_clicked]

    col1, col2 = st.columns([1, 2])

    with col1:
        gap_year = df_prov[df_prov["Tahun"] == year]["Gap_ton"]
        st.metric(
            f"Gap Tahun {year}",
            f"{gap_year.values[0]:,.0f} ton" if not gap_year.empty else "Tidak ada data"
        )

    with col2:
        st.line_chart(
            df_prov.set_index("Tahun")["Gap_ton"]
        )
else:
    st.info("👆 Klik provinsi pada peta untuk melihat breakdown.")

    st.subheader("DEBUG KOLOM")
st.write("Kolom gdf_map:", list(gdf_map.columns))
st.write("Kolom df_long:", list(df_long.columns))
st.stop()

