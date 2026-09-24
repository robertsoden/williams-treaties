"""Render a static map of the Oak Ridges Trail across the Williams Treaty territory.

The trail is a long, thin east-west corridor (~268 km end to end, ~30 km tall),
so the map is laid out as a single wide landscape sheet. Alongside the route it
shows the official LIO trail access points that fall on the corridor and the
points where the trail crosses a watercourse.

Usage:
    env/bin/python scripts/make_oak_ridges_trail_map.py [basemap ...]

    basemap is one or more of: voyager (default), voyager_nolabels, osm,
    natgeo, physical, terrain
"""

import argparse
import math
from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import mapbox_terrain

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT_DIR = ROOT / "new"

TRAIL_PATH = DATA / "datasets" / "environmental" / "oak_ridges_trail.geojson"
ACCESS_PATH = DATA / "datasets" / "infrastructure" / "trail_access_points.geojson"
CROSSINGS_PATH = DATA / "datasets" / "hydrology" / "oak_ridges_trail_stream_crossings.geojson"

WEB_MERC = 3857
ONT_LAMBERT = 3161  # metric CRS for distance/length work

# Figure geometry. The 8:3 aspect roughly matches the trail's own bounding box,
# so the route fills the sheet without a lot of dead space above and below.
FIG_W, FIG_H = 16.0, 6.0
DPI = 200

# Colours mirror the web layer definitions in web/config/layers.yaml so the
# static map and the interactive map read as the same product.
TRAIL_COLOR = "#d94801"
TRAIL_CASING = "#ffffff"
CROSSING_COLORS = {"Permanent": "#2b6cb0", "Intermittent": "#8bb8dc"}
CROSSING_DEFAULT = "#4a90d9"
ACCESS_COLOR = "#1b7837"

# How far from the trail centreline a province-wide access point must sit to
# count as an Oak Ridges Trail access point.
ACCESS_BUFFER_M = 250

# Hillshade is computed from the Mapbox terrain DEM and composited as shadows
# only -- see scripts/mapbox_terrain.py. The DEM is fetched one zoom level above
# the basemap, since relief detail survives downsampling better than tile labels.
#
# The web map uses exaggeration 1.0, but it is viewed zoomed in. Here the whole
# 165 km corridor is on one sheet and the moraine is only ~100-200 m of relief,
# so 1.0 is nearly invisible at this scale; 3.0 makes the landform read.
EXAGGERATION = 3.0
DEM_ZOOM_OFFSET = 1


def load_data(access_buffer_m=ACCESS_BUFFER_M):
    """Load the trail and clip the two point layers to its corridor."""
    trail = gpd.read_file(TRAIL_PATH).to_crs(WEB_MERC)

    corridor = (
        trail.to_crs(ONT_LAMBERT).geometry.union_all().buffer(access_buffer_m)
    )

    access = gpd.read_file(ACCESS_PATH).to_crs(ONT_LAMBERT)
    access = access[access.within(corridor)].to_crs(WEB_MERC)

    crossings = gpd.read_file(CROSSINGS_PATH).to_crs(WEB_MERC)

    return trail, access, crossings


def compute_frame(trail):
    """Trail bounds padded out, then stretched to the figure aspect ratio."""
    minx, miny, maxx, maxy = trail.total_bounds
    pad_x = (maxx - minx) * 0.045
    pad_y = (maxy - miny) * 0.25
    minx -= pad_x
    maxx += pad_x
    miny -= pad_y
    maxy += pad_y

    target = FIG_W / FIG_H
    data_w, data_h = maxx - minx, maxy - miny
    if data_w / data_h < target:
        extra = (data_h * target - data_w) / 2
        minx -= extra
        maxx += extra
    else:
        extra = (data_w / target - data_h) / 2
        miny -= extra
        maxy += extra

    return minx, miny, maxx, maxy


def render(trail, access, crossings, basemap_source, zoom, label_parts=True,
           hillshade=False, exaggeration=EXAGGERATION, dem_zoom_offset=DEM_ZOOM_OFFSET):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    ax.set_aspect("equal")

    minx, miny, maxx, maxy = compute_frame(trail)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    cx.add_basemap(
        ax, source=basemap_source, crs=f"EPSG:{WEB_MERC}",
        zoom=zoom, zorder=1, attribution=False,
    )

    if hillshade:
        # Same recipe as the site's `hillshade` layer: shadows only, over a
        # full-strength basemap. Flat ground is untouched, so nothing washes out.
        mapbox_terrain.add_hillshade(
            ax, zoom=zoom + dem_zoom_offset, zorder=3,
            exaggeration=exaggeration,
        )

    # White casing under the route so it stays legible over dark basemap tiles.
    trail.plot(ax=ax, color=TRAIL_CASING, linewidth=3.4, zorder=5,
               capstyle="round")
    trail.plot(ax=ax, color=TRAIL_COLOR, linewidth=1.8, zorder=6,
               capstyle="round")

    if not crossings.empty:
        colors = [
            CROSSING_COLORS.get(p, CROSSING_DEFAULT)
            for p in crossings.get("permanency", [])
        ] or CROSSING_DEFAULT
        crossings.plot(ax=ax, marker="o", color=colors, markersize=9,
                       edgecolor="white", linewidth=0.4, zorder=7)

    if not access.empty:
        access.plot(ax=ax, marker="s", color=ACCESS_COLOR, markersize=42,
                    edgecolor="white", linewidth=1.0, zorder=8)

    if label_parts:
        add_part_labels(ax, trail)

    add_scalebar(ax)
    add_north_arrow(ax)
    add_legend(ax, access, crossings)
    add_title(ax, trail)
    add_attribution(ax, hillshade=hillshade)

    ax.set_axis_off()
    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
    return fig


def add_part_labels(ax, trail):
    """Label the seven numbered trail sections at the middle of each run.

    Segment names are like "Part 3A" / "Part 3-Rabbit"; they collapse to the
    seven parent parts so the sheet carries seven labels rather than 24.
    """
    if "name" not in trail.columns:
        return

    parts = trail.copy()
    parts["part"] = (
        parts["name"].astype(str)
        .str.extract(r"Part\s*(\d+)", expand=False)
    )
    parts = parts.dropna(subset=["part"])

    for part, group in parts.groupby("part"):
        merged = group.geometry.union_all()
        # interpolate() walks the line itself, so the label lands on the route
        # instead of floating at a bounding-box centre.
        anchor = merged.geoms[len(merged.geoms) // 2] if hasattr(merged, "geoms") else merged
        pt = anchor.interpolate(0.5, normalized=True)
        ax.annotate(
            f"Part {part}",
            xy=(pt.x, pt.y),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center", va="bottom",
            fontsize=8, fontweight="bold", color="#7a2800",
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="none", alpha=0.8),
            zorder=9,
        )


def add_legend(ax, access, crossings):
    handles = [
        Line2D([0], [0], color=TRAIL_COLOR, linewidth=2.4,
               label="Oak Ridges Trail"),
    ]
    if not access.empty:
        handles.append(Line2D(
            [0], [0], marker="s", color="w", markerfacecolor=ACCESS_COLOR,
            markeredgecolor="white", markeredgewidth=1.0, markersize=8,
            label=f"Trail access point ({len(access)})",
        ))
    if not crossings.empty:
        counts = crossings.get("permanency").value_counts() if "permanency" in crossings else {}
        for label, color in CROSSING_COLORS.items():
            n = int(counts.get(label, 0)) if len(counts) else 0
            if not n:
                continue
            handles.append(Line2D(
                [0], [0], marker="o", color="w", markerfacecolor=color,
                markeredgecolor="white", markeredgewidth=0.4, markersize=6,
                label=f"Stream crossing — {label.lower()} ({n})",
            ))

    ax.legend(handles=handles, loc="lower left", fontsize=8, frameon=True,
              facecolor="white", edgecolor="#888", framealpha=0.95,
              borderpad=0.7, labelspacing=0.6).set_zorder(11)


def add_title(ax, trail):
    length_km = trail.to_crs(ONT_LAMBERT).length.sum() / 1000
    ax.text(
        0.005, 0.985,
        "Oak Ridges Trail",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=17, fontweight="bold", color="#111", zorder=11,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.82),
    )
    ax.text(
        0.005, 0.915,
        f"{length_km:,.0f} km of hiking route along the Oak Ridges Moraine, "
        "within the Williams Treaty territory",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=9, color="#444", zorder=11,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.82),
    )


def add_scalebar(ax):
    """Bar scale, corrected for Web Mercator's latitude-dependent stretch."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()

    # Scale is true only along the frame's centre parallel; convert that
    # latitude back from Web Mercator y to get the local metres-per-unit.
    y_mid = (y0 + y1) / 2
    lat = math.degrees(2 * math.atan(math.exp(y_mid / 6378137.0)) - math.pi / 2)
    units_per_metre = 1 / math.cos(math.radians(lat))

    bar_km = 25
    bar_units = bar_km * 1000 * units_per_metre

    bx = x0 + (x1 - x0) * 0.30
    by = y0 + (y1 - y0) * 0.075
    tick = (y1 - y0) * 0.012

    ax.plot([bx, bx + bar_units], [by, by], color="black", lw=3,
            solid_capstyle="butt", zorder=11)
    for x in (bx, bx + bar_units):
        ax.plot([x, x], [by - tick, by + tick], color="black", lw=1.4, zorder=11)
    ax.text(bx + bar_units / 2, by + tick * 1.6, f"{bar_km} km",
            ha="center", va="bottom", fontsize=8, zorder=11,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))


def add_north_arrow(ax):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    ax_x = x1 - (x1 - x0) * 0.02
    ax_y = y1 - (y1 - y0) * 0.10
    ax.annotate(
        "N", xy=(ax_x, ax_y), xytext=(ax_x, ax_y - (y1 - y0) * 0.13),
        arrowprops=dict(facecolor="black", width=3.5, headwidth=9, headlength=9),
        ha="center", fontsize=10, fontweight="bold", zorder=11,
    )


def add_attribution(ax, hillshade=False):
    relief = " Relief: Mapbox Terrain DEM." if hillshade else ""
    ax.text(
        0.995, 0.012,
        "Trail: Oak Ridges Trail Association. Access points: Land Information "
        "Ontario. Stream crossings: Ontario Hydro Network × trail route.\n"
        f"Basemap: © OpenStreetMap contributors, © CARTO.{relief}",
        transform=ax.transAxes, ha="right", va="bottom",
        fontsize=6.5, color="#333", linespacing=1.4,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85),
        zorder=11,
    )


BASEMAP_VARIANTS = {
    "voyager":          (cx.providers.CartoDB.Voyager, "oak_ridges_trail"),
    "voyager_nolabels": (cx.providers.CartoDB.VoyagerNoLabels, "oak_ridges_trail_nolabels"),
    "osm":              (cx.providers.OpenStreetMap.Mapnik, "oak_ridges_trail_osm"),
    "natgeo":           (cx.providers.Esri.NatGeoWorldMap, "oak_ridges_trail_natgeo"),
    "physical":         (cx.providers.Esri.WorldPhysical, "oak_ridges_trail_physical"),
    "terrain":          (cx.providers.Esri.WorldTopoMap, "oak_ridges_trail_topo"),
}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("basemaps", nargs="*", default=["voyager"],
                   help=f"one or more of: {', '.join(BASEMAP_VARIANTS)}")
    p.add_argument("--zoom", type=int, default=11,
                   help="basemap tile zoom level (default 11)")
    p.add_argument("--access-buffer", type=float, default=ACCESS_BUFFER_M,
                   help="metres from the trail an access point may sit (default 250)")
    p.add_argument("--no-part-labels", action="store_true",
                   help="omit the Part 1-7 section labels")
    p.add_argument("--hillshade", action="store_true",
                   help="overlay shadows-only relief from the Mapbox terrain DEM, "
                        "matching the web map's hillshade layer (needs a token)")
    p.add_argument("--exaggeration", type=float, default=EXAGGERATION,
                   help="vertical exaggeration for the hillshade (default 3.0; "
                        "the moraine is subtle, so 2-3 reads better on a wide sheet)")
    p.add_argument("--dem-zoom-offset", type=int, default=DEM_ZOOM_OFFSET,
                   help="DEM zoom relative to the basemap zoom (default +1)")
    p.add_argument("--png", action="store_true",
                   help="also write a PNG alongside the PDF")
    return p.parse_args()


def main():
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    trail, access, crossings = load_data(args.access_buffer)
    print(f"Trail segments: {len(trail)}  "
          f"access points within {args.access_buffer:.0f} m: {len(access)}  "
          f"stream crossings: {len(crossings)}")

    for key in args.basemaps or ["voyager"]:
        if key not in BASEMAP_VARIANTS:
            print(f"unknown basemap: {key} (choose from {list(BASEMAP_VARIANTS)})")
            continue
        source, stem = BASEMAP_VARIANTS[key]
        if args.hillshade:
            stem += "_hillshade"
        fig = render(trail, access, crossings, source, args.zoom,
                     label_parts=not args.no_part_labels,
                     hillshade=args.hillshade,
                     exaggeration=args.exaggeration,
                     dem_zoom_offset=args.dem_zoom_offset)

        out_pdf = OUT_DIR / f"{stem}.pdf"
        fig.savefig(out_pdf, format="pdf", bbox_inches="tight")
        print(f"Wrote {out_pdf}")

        if args.png:
            out_png = OUT_DIR / f"{stem}.png"
            fig.savefig(out_png, format="png", bbox_inches="tight")
            print(f"Wrote {out_png}")

        plt.close(fig)


if __name__ == "__main__":
    main()
