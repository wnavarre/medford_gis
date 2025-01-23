import contextily as cx
import geopandas
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pylab

parcels = geopandas.read_file("./medford_shp/medford.shp")
parcels = parcels[parcels.ZONE == "GR"]
parcels = parcels.to_crs(epsg=3857)
fig, ax = plt.subplots(figsize=(10, 10))


too_small = parcels["SHAPE_Area"] < 557
my_red = "#731C27"
my_green = "#2F4B26"

parcels['color'] = np.where(too_small, 0, 1)

my_cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
    "my_cmap", [(0, my_red), (1, my_green)])

special_legend_ax = with_special_legend_func(ax)
parcels_plotted = parcels.plot(column="color",
                               categorical=True,
                               categories=[0, 1],
                               cmap=my_cmap,
                               legend=True,
                               legend_kwds={
                                   "labels": ["A", "B"],
                               },
                               ax=special_legend_ax)
fig_legend = plt.figure(figsize=(3, 2))

for args, kwargs in special_legend_ax.calls_to_legend:
    kwargs["loc"] = "center"
    fig_legend.legend(*args, **kwargs)


#fig_legend.legend(parcels_plotted.get_legend_handles_labels()[0],
#                  ("A", "B"),
#                  loc='center')

cx.add_basemap(ax)

if __name__ == "__main__":
    fig.show()
    fig_legend.show()
    input()
