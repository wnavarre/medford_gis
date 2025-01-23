import contextily as cx
import geopandas
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pylab
import medford_regions as regions
from mapping import *

parcels = geopandas.read_file("../medford_shp/medford.shp")
#parcels = parcels[parcels.ZONE == "GR"]
parcels = parcels[parcels.SHAPE_Area < 21000]
parcels = parcels[parcels.intersects(regions.GR.SOUTH.rect())]
parcels = parcels.reset_index()
#parcels = parcels.to_crs(epsg=3857)


fig, ax = plt.subplots(figsize=(10, 10), dpi=300)

draw_categories(
    parcels,
    [
        Category("Public", BLACK, parcels["PUBLIC_USE"] == "True"),
        Category("Too small", RED, parcels["SHAPE_Area"] < 278.7),
        Category("Already 2+ units", YELLOW, parcels["MIN_COUNT"] > 1.9),
        Category("Buildable", GREEN)
    ],
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

if __name__ == "__main__":
    fig.savefig('sample.png', dpi=216, bbox_inches="tight")
