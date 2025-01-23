import contextily as cx
import geopandas
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pylab
import medford_regions as regions
from mapping import *

parcels = geopandas.read_file("../medford_shp/medford.shp")
parcels = parcels[parcels.ZONE == "GR"]
#parcels = parcels.to_crs(epsg=3857)


fig, ax = plt.subplots(figsize=(10, 10), dpi=300)

draw_categories(
    parcels,
    [
        Category("Big enough", GREEN, parcels["SHAPE_Area"] >= 557),
        Category("Too Small", RED),
    ],
    ax=ax,
    legend=ax,
    legend_kwds=dict(loc="upper right")
)

gr = regions.GR.FRAME

gr.plot(ax=forward_legend_func(ax),
        #column="name",
        color="grey",
        categorical=True,
        legend=False,
        alpha=.5)

plt.axis("off")
#cx.add_basemap(ax)

if __name__ == "__main__":
    fig.savefig('sample.svg', bbox_inches="tight")
