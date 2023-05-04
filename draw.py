import contextily as cx
import geopandas
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

parcels = geopandas.read_file("./medford_shp/M176TaxPar_CY21_FY20.shp")
parcels = parcels[parcels.ZONE == "GR"]
parcels = parcels.to_crs(epsg=3857)
fig, ax = plt.subplots(figsize=(10, 10))

too_small = parcels["SHAPE_Area"] < 557
my_red = "#731C27"
my_green = "#2F4B26"

parcels['color'] = np.where(too_small, 0, 1)

my_cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
    "my_cmap", [(0, my_red), (1, my_green)])

parcels.plot(column="color",
             categorical=True,
             categories=[0, 1],
             cmap=my_cmap,
             ax=ax,
             legend=True,
             legend_kwds={
                 "labels" : ["A", "B"]
             })

###cx.add_basemap(ax)

if __name__ == "__main__":
    fig.show()
    input()
