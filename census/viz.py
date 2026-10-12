import plotly.express as px
import math

def build_map(df):
    plot_df = df.dropna(subset=["rent_burden_pct", "INTPTLAT", "INTPTLONG"]).copy()
    plot_df["B01003_001E"] = plot_df["B01003_001E"].fillna(0)   # missing sizes can hide markers

    fig = px.scatter_geo(
        plot_df,
        lat="INTPTLAT", lon="INTPTLONG",
        color="rent_burden_pct",
        size="B01003_001E",
        size_max=14,
        color_continuous_scale="Viridis",
        hover_name="NAME",
        hover_data={"rent_burden_pct": ":.1f", "B19013_001E": ":$,.0f",
                    "INTPTLAT": False, "INTPTLONG": False, "B01003_001E": ":,"},
        labels={"rent_burden_pct": "% renters cost-burdened",
                "B19013_001E": "Median income",
                "B01003_001E": "Population"},
    )
    fig.update_geos(
        fitbounds="locations",          # auto-zoom to whatever city is loaded
        showland=True, landcolor="#f2f2f2",
        showsubunits=True, subunitcolor="#bbbbbb",   # state lines for context
    )
    fig.update_layout(height=600, margin={"l": 0, "r": 0, "t": 30, "b": 0})
    return fig

#centers the map view to the city selected
def map_view(df, lat="INTPTLAT", lon="INTPTLONG", width_px=1200, height_px=950, padding=1.1):

    lat_min, lat_max = df[lat].min(), df[lat].max()
    lon_min, lon_max = df[lon].min(), df[lon].max()
    center = {"lat": (lat_min + lat_max) / 2, "lon": (lon_min + lon_max) / 2}

    lon_span = max((lon_max - lon_min) * padding, 1e-6)
    lat_span = max((lat_max - lat_min) * padding, 1e-6)

    zoom_lon = math.log2(width_px * 360 / (256 * lon_span))
    zoom_lat = math.log2(height_px * 360 * math.cos(math.radians(center["lat"])) / (256 * lat_span))

    return center, min(zoom_lon, zoom_lat)