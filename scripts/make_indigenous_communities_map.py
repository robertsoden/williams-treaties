"""Render a static PDF map of Indigenous communities within the Williams Treaty territory."""

from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
from adjustText import adjust_text
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "new"
OUT_PDF = OUT_DIR / "indigenous_communities_williams_treaty.pdf"

WEB_MERC = 3857

# Williams Treaties First Nations community locations.
# Coordinates resolved from each Nation's official band-office address (sourced
# from the Nation's own website) via Nominatim geocoding, with manual overrides
# for the two ferry-only island communities. See scripts/geocode_band_offices.py.
# Format: (first_nation, lon, lat).
COMMUNITIES = [
    ("Alderville First Nation",                     -78.07621, 44.17757),
    ("Curve Lake First Nation",                     -78.36233, 44.48227),
    ("Hiawatha First Nation",                       -78.20882, 44.19154),
    ("Mississaugas of Scugog Island First Nation",  -78.92008, 44.12535),
    ("Chippewas of Beausoleil First Nation",        -80.12320, 44.84200),
    ("Chippewas of Georgina Island First Nation",   -79.29670, 44.37330),
    ("Chippewas of Rama First Nation",              -79.34943, 44.65525),
]

# Reference cities (lon, lat).
CITIES = [
    ("Toronto", -79.3832, 43.6532),
]

# Major water bodies in the frame: (label, lon, lat, rotation_deg, fontsize).
WATER_LABELS = [
    ("Lake Ontario",     -78.45, 43.75,   0, 14),
    ("Lake Simcoe",      -79.35, 44.42,   0, 11),
    ("Georgian Bay",     -80.30, 44.78,  -8, 13),
    ("Lake Scugog",      -78.78, 44.18,   0,  8),
    ("Rice Lake",        -78.22, 44.15,   0,  9),
    ("Kawartha Lakes",   -78.45, 44.55, -10,  9),
]


def load_data():
    communities = gpd.GeoDataFrame(
        {"first_nation": [c[0] for c in COMMUNITIES]},
        geometry=[Point(c[1], c[2]) for c in COMMUNITIES],
        crs="EPSG:4326",
    ).to_crs(WEB_MERC)
    cities = gpd.GeoDataFrame(
        {"name": [c[0] for c in CITIES]},
        geometry=[Point(c[1], c[2]) for c in CITIES],
        crs="EPSG:4326",
    ).to_crs(WEB_MERC)
    return communities, cities


def project_water_labels():
    pts = gpd.GeoSeries(
        [Point(lon, lat) for _, lon, lat, _, _ in WATER_LABELS],
        crs="EPSG:4326",
    ).to_crs(WEB_MERC)
    return [
        (name, pt.x, pt.y, rot, size)
        for (name, _, _, rot, size), pt in zip(WATER_LABELS, pts)
    ]


def render(communities, cities, basemap_source=None):
    fig_w, fig_h = 13, 9
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
    ax.set_aspect("equal")

    # Frame: tight box around communities + Toronto, expanded to match the
    # figure's wide aspect so the basemap fills the canvas without distortion.
    frame = gpd.GeoDataFrame(
        geometry=list(communities.geometry) + list(cities.geometry),
        crs=communities.crs,
    )
    minx, miny, maxx, maxy = frame.total_bounds
    pad_x = (maxx - minx) * 0.05
    pad_y_top = (maxy - miny) * 0.18
    pad_y_bot = (maxy - miny) * 0.08
    minx -= pad_x; maxx += pad_x
    miny -= pad_y_bot; maxy += pad_y_top

    target = fig_w / fig_h
    data_w = maxx - minx
    data_h = maxy - miny
    if data_w / data_h < target:
        extra = (data_h * target - data_w) / 2
        minx -= extra; maxx += extra
    else:
        extra = (data_w / target - data_h) / 2
        miny -= extra; maxy += extra

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    cx.add_basemap(ax, source=basemap_source or cx.providers.CartoDB.VoyagerNoLabels,
                   crs=f"EPSG:{WEB_MERC}", zorder=1, attribution=False)

    add_water_labels(ax)
    place_labels(ax, communities, cities)

    ax.set_axis_off()
    add_attribution(ax)

    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    return fig


def place_labels(ax, communities, cities):
    """Plot signatory community filled circles + reference city ring."""
    communities.plot(ax=ax, marker="o", color="#d73027", edgecolor="white",
                     markersize=140, linewidth=1.2, zorder=7)
    cities.plot(ax=ax, marker="o", facecolor="none", edgecolor="#222",
                markersize=140, linewidth=1.6, zorder=7)

    # Communities whose labels should sit tight against the marker (skip
    # collision avoidance so they don't drift away).
    # Per-label placement: offset (x, y) in points + vertical alignment.
    # Hiawatha and Alderville sit on opposite shores of Rice Lake (~11 km
    # apart), so they need vertical separation to keep labels from overlapping.
    close_labels = {
        "Chippewas of Beausoleil":      {"xytext": (9, 0),  "va": "center"},
        "Chippewas of Rama":            {"xytext": (9, 0),  "va": "center"},
        "Curve Lake":                   {"xytext": (9, 0),  "va": "center"},
        "Chippewas of Georgina Island": {"xytext": (9, 0),  "va": "center"},
        "Hiawatha":                     {"xytext": (9, 6),  "va": "bottom"},
        "Mississaugas of Scugog Island":{"xytext": (9, 0),  "va": "center"},
        "Alderville":                   {"xytext": (9, -6), "va": "top"},
    }

    label_overrides = {
        "Chippewas of Beausoleil": "Beausoleil",
        "Chippewas of Georgina Island": "Chippewas of\nGeorgina Island",
        "Mississaugas of Scugog Island": "Mississaugas of\nScugog Island",
    }

    pinned_artists = []
    texts, anchors_x, anchors_y = [], [], []

    for _, row in communities.iterrows():
        key = row["first_nation"].replace(" First Nation", "")
        text_label = label_overrides.get(key, key)
        common = dict(fontsize=10, fontweight="bold", color="#111", zorder=8)
        if key in close_labels:
            placement = close_labels[key]
            pinned_artists.append(ax.annotate(
                text_label,
                xy=(row.geometry.x, row.geometry.y),
                textcoords="offset points",
                **placement,
                **common,
            ))
        else:
            texts.append(ax.text(
                row.geometry.x, row.geometry.y, text_label, **common,
            ))
            anchors_x.append(row.geometry.x)
            anchors_y.append(row.geometry.y)

    for _, row in cities.iterrows():
        texts.append(ax.text(
            row.geometry.x, row.geometry.y, row["name"],
            fontsize=11, fontweight="bold", color="#222", style="italic",
            zorder=8,
        ))
        anchors_x.append(row.geometry.x)
        anchors_y.append(row.geometry.y)

    adjust_text(
        texts, x=anchors_x, y=anchors_y, ax=ax,
        objects=pinned_artists,
        expand=(1.5, 1.7),
        force_text=(0.8, 1.0),
        force_static=(0.5, 0.7),
        only_move={"text": "xy", "static": "xy", "explode": "xy"},
    )


def add_legend(ax):
    handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#d73027",
               markeredgecolor="white", markeredgewidth=1.2, markersize=10,
               label="Williams Treaties First Nation"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="none",
               markeredgecolor="#222", markeredgewidth=1.6, markersize=10,
               label="Reference city"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=9, frameon=True,
              facecolor="white", edgecolor="#888", framealpha=0.95)


def add_water_labels(ax):
    for name, x, y, rot, size in project_water_labels():
        ax.text(
            x, y, name,
            fontsize=size, color="#1f4e7a", style="italic",
            ha="center", va="center", rotation=rot, zorder=5,
        )


def add_scalebar(ax, boundary):
    minx, miny, maxx, _ = ax.get_xlim()[0], *ax.get_ylim(), ax.get_xlim()[1]
    # Web Mercator distortion: approximate by using boundary centroid latitude.
    lat = boundary.to_crs(4326).geometry.union_all().centroid.y
    import math
    m_per_unit = math.cos(math.radians(lat))  # 1 web-merc unit ~ this many real metres
    bar_km = 25
    bar_m = bar_km * 1000
    bar_units = bar_m / m_per_unit

    x0 = minx + (maxx - minx) * 0.04
    y0 = miny + (ax.get_ylim()[1] - miny) * 0.06
    ax.plot([x0, x0 + bar_units], [y0, y0], color="black", lw=3, solid_capstyle="butt", zorder=10)
    ax.plot([x0, x0], [y0 - 1500, y0 + 1500], color="black", lw=1.5, zorder=10)
    ax.plot([x0 + bar_units, x0 + bar_units], [y0 - 1500, y0 + 1500],
            color="black", lw=1.5, zorder=10)
    ax.text(x0 + bar_units / 2, y0 + 2500, f"{bar_km} km",
            ha="center", fontsize=8, zorder=10)


def add_north_arrow(ax):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    ax_x = x1 - (x1 - x0) * 0.04
    ax_y = y1 - (y1 - y0) * 0.10
    ax.annotate("N", xy=(ax_x, ax_y), xytext=(ax_x, ax_y - (y1 - y0) * 0.05),
                arrowprops=dict(facecolor="black", width=4, headwidth=10, headlength=10),
                ha="center", fontsize=11, fontweight="bold", zorder=10)


def add_attribution(ax):
    ax.text(
        0.985, 0.015,
        "Basemap: © OpenStreetMap contributors, © CARTO.",
        transform=ax.transAxes,
        ha="right", va="bottom", fontsize=7, color="#333",
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85),
        zorder=10,
    )


BASEMAP_VARIANTS = {
    "voyager":  (cx.providers.CartoDB.VoyagerNoLabels,
                 "indigenous_communities_williams_treaty.pdf"),
    "osm":      (cx.providers.OpenStreetMap.Mapnik,
                 "indigenous_communities_williams_treaty_osm.pdf"),
    "natgeo":   (cx.providers.Esri.NatGeoWorldMap,
                 "indigenous_communities_williams_treaty_natgeo.pdf"),
    "physical": (cx.providers.Esri.WorldPhysical,
                 "indigenous_communities_williams_treaty_physical.pdf"),
}


def main():
    import sys

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    communities, cities = load_data()
    print(f"Signatory communities: {len(communities)}, cities: {len(cities)}")

    keys = sys.argv[1:] or ["voyager"]
    for key in keys:
        if key not in BASEMAP_VARIANTS:
            print(f"unknown basemap: {key} (choose from {list(BASEMAP_VARIANTS)})")
            continue
        source, filename = BASEMAP_VARIANTS[key]
        out = OUT_DIR / filename
        fig = render(communities, cities, basemap_source=source)
        fig.savefig(out, format="pdf", bbox_inches="tight")
        plt.close(fig)
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
