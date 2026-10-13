import math

import pandas as pd
import plotly.express as px

MAP_WIDTH_PX = 1100
MAP_HEIGHT_PX = 650

def map_view(df, lat="INTPTLAT", lon="INTPTLONG",
             width_px=MAP_WIDTH_PX, height_px=MAP_HEIGHT_PX, padding=1.1):
    lat_min, lat_max = df[lat].min(), df[lat].max()
    lon_min, lon_max = df[lon].min(), df[lon].max()
    center = {"lat": (lat_min + lat_max) / 2, "lon": (lon_min + lon_max) / 2}

    lon_span = max((lon_max - lon_min) * padding, 1e-6)
    lat_span = max((lat_max - lat_min) * padding, 1e-6)

    zoom_lon = math.log2(width_px * 360 / (256 * lon_span))
    zoom_lat = math.log2(height_px * 360 * math.cos(math.radians(center["lat"])) / (256 * lat_span))

    return center, min(zoom_lon, zoom_lat)


def build_map(df: pd.DataFrame, metric: str, label: str = "", height_px: int = MAP_HEIGHT_PX):
    plot_df = df.dropna(subset=[metric])
    center, zoom = map_view(plot_df, height_px=height_px)

    fig = px.scatter_map(
        plot_df,
        lat="INTPTLAT", lon="INTPTLONG",
        color=metric,
        size="B01003_001E",
        color_continuous_scale="Viridis",
        hover_name="NAME",
        center=center, zoom=zoom,
        height=height_px,
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        coloraxis_colorbar_title=label or metric,
    )
    return fig


def build_map_simple(df: pd.DataFrame, metric: str, label: str = ""):
    plot_df = df.dropna(subset=[metric, "INTPTLAT", "INTPTLONG"]).copy()
    plot_df["B01003_001E"] = plot_df["B01003_001E"].fillna(0)

    fig = px.scatter_geo(
        plot_df,
        lat="INTPTLAT", lon="INTPTLONG",
        color=metric,
        size="B01003_001E",
        size_max=14,
        color_continuous_scale="Viridis",
        hover_name="NAME",
    )
    fig.update_geos(fitbounds="locations", showland=True, landcolor="#f2f2f2",
                    showsubunits=True, subunitcolor="#bbbbbb")
    fig.update_layout(height=MAP_HEIGHT_PX, margin={"l": 0, "r": 0, "t": 0, "b": 0},
                      coloraxis_colorbar_title=label or metric)
    return fig