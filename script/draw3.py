oimport contextily as cx
import geopandas
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pylab
from mapping import *

parcels = geopandas.read_file("../medford_shp/M176TaxPar_CY21_FY20.shp")
parcels = parcels[parcels.ZONE == "GR"]
parcels = parcels.to_crs(epsg=3857)


fig, ax = plt.subplots(figsize=(10, 10))

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

cx.add_basemap(ax)

if __name__ == "__main__":
    fig.show()
    input()
