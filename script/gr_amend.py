import contextily as cx
import geopandas
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pylab
import medford_regions as regions
from mapping import *

parcels = geopandas.read_parquet("../medford_shp/medford.pqt")
parcels = parcels[parcels.SHAPE_Area < 21000]
parcels = parcels.reset_index()

def go_generic(parcels, make_categories, name):
    fig, ax = plt.subplots(figsize=(10, 10), dpi=300)

    draw_categories(
        parcels.to_crs(epsg=3857),
        make_categories(parcels),
        ax=ax,
        legend=ax,
        legend_kwds=dict(loc="upper right")
    )
    if 0:
        gr = regions.GR.SOUTH

        gr.plot(ax=forward_legend_func(ax),
                #column="name",
                color="grey",
                categorical=True,
                legend=False,
                alpha=.5)

    plt.axis("off")
    cx.add_basemap(ax)
    fig.savefig(name, dpi=216, bbox_inches="tight")

def make_categories_4(parcels):
    return [
        Category("Public", BLACK, parcels["PUBLIC_USE"] == "True"),
        Category("Too small", RED, parcels["SHAPE_Area"] < 278.7),
        Category("Already 2+ units", YELLOW, parcels["MIN_COUNT"] > 1.9),
        Category("Buildable", GREEN)
    ]

def make_categories_sf(parcels):
    return [ Category("SFH", BLACK) ]

def filter_sf(parcels, region=None):
    parcels = parcels[ parcels.MIN_COUNT == 1 ]
    if region is not None:
        return parcels[parcels.intersects(region)]
    else:
        return parcels

def go(parcels, name): go_generic(parcels, make_categories_4, name)
    
if __name__ == "__main__":
    go_generic(filter_sf(parcels, regions.GR.SOUTH.rect()),
               make_categories_sf,
               "single_family_homes.png")
    go_generic(filter_sf(parcels, regions.GR.SOUTH.rect()),
               make_categories_sf,
               "single_family_homes.svg")
    go(parcels[parcels.intersects(regions.MEDFORD_MAIN_BROADWAY_BOUNDS)], "magoun.png")
    go(parcels[parcels.intersects(regions.MISSITUK_DISTRICT)], "missituk.png")
    go(parcels[parcels.intersects(regions.BOB)], "bob.png")
