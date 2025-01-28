import shapely
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

def go_generic(parcels, make_categories, name, *, ax_function=None):
    fig, ax = plt.subplots(figsize=(10, 10), dpi=300)
    if ax_function is not None: ax = ax_function(ax)
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
    return ax

def make_categories_4(parcels):
    return [
        Category("Public", BLACK, parcels["PUBLIC_USE"] == "True"),
        Category("Too small", RED, parcels["SHAPE_Area"] < 278.7),
        Category("Already 2+ units", YELLOW, parcels["MIN_COUNT"] > 1.9),
        Category("Buildable", GREEN)
    ]

def make_categories_sf(parcels):
    return [ Category("SFH", BLACK) ]

def go_lteq_units(parcels, count, **argkv):
    return go_generic(parcels[parcels.MIN_COUNT <= (count + .1)],
                      lambda x: [ Category("1 <= UNIT COUNT <= {}".format(count), BLACK) ],
                      "UNIT_LT_{}.png".format(count),
                      **argkv)

def go_geq_units(parcels, count, **argkv):
    return go_generic(parcels[parcels.MIN_COUNT >= (count - .1)],
                      lambda x: [ Category("UNIT COUNT >= {}".format(count), BLACK) ],
                      "UNIT_GT_{}.png".format(count),
                      **argkv)
    
def filter_sf(parcels, region=None):
    parcels = parcels[ parcels.MIN_COUNT == 1 ]
    if region is not None:
        return parcels[parcels.intersects(region)]
    else:
        return parcels

def go(parcels, name): go_generic(parcels, make_categories_4, name)

def make_ax_fixer(xlim, ylim):
    def ax_fixer(ax):
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        return ax
    return ax_fixer

if __name__ == "__main__":
    housing_parcels = parcels[parcels.MIN_COUNT > .9]
    ax_fixer = None
    south_medford_nr2 = shapely.ops.unary_union([
        regions.MEDFORD_MAIN_BROADWAY_BOUNDS,
        regions.MISSITUK_DISTRICT,
        regions.BOB        
    ])
    for count in [1, 2, 4, 8]:
        if ax_fixer is None:
            ax = go_geq_units(housing_parcels, count)
            ax_fixer = make_ax_fixer(ax.get_xlim(), ax.get_ylim())
        else:
            go_geq_units(housing_parcels, count, ax_function=ax_fixer)
        go_lteq_units(housing_parcels, count, ax_function=ax_fixer)
    go_generic(filter_sf(parcels, regions.GR.SOUTH.rect()),
               make_categories_sf,
               "single_family_homes.png")
    go_generic(filter_sf(parcels, regions.GR.SOUTH.rect()),
               make_categories_sf,
               "single_family_homes.svg")
    go(parcels[parcels.intersects(regions.MEDFORD_MAIN_BROADWAY_BOUNDS)], "magoun.png")
    go(parcels[parcels.intersects(regions.MISSITUK_DISTRICT)], "missituk.png")
    go(parcels[parcels.intersects(regions.BOB)], "bob.png")
    go(parcels[parcels.intersects(south_medford_nr2)], "south_nr2.png")
