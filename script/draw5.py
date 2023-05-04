import contextily as cx
import geopandas
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pylab
import medford_regions
from mapping import *
from ticker import *

dpi = 300

parcels = geopandas.read_file("../medford_shp/M176TaxPar_CY21_FY20.shp")
parcels = parcels[parcels.ZONE == "GR"]
parcels = parcels.to_crs(epsg=3857)

def lot_too_small(features, idx):
    ft = 6000 - 500 * idx
    out = BoolTickerResult(features["SHAPE_Area"] >= (0.3048**2) * ft)
    out.true_label = "> {} sq. ft.".format(ft)
    out.false_label = "< {} sq. ft.".format(ft)
    return out

REGION = medford_regions.GR.SOUTH

fig, ax = bool_ticker(parcels, lot_too_small, REGION, count_x=3, count_y=3, width=7/3, true_color=GREEN, false_color=RED,
                      legend_kwds={'loc': "upper right", 'fontsize' : 10 })

fig.subplots_adjust(hspace=2/72, wspace=2/72, left=0, right=1, top=1, bottom=0)

for i, e in enumerate(ax):
    e.set_xticks([])
    e.set_yticks([])
    e.patch.set_edgecolor('black')
    e.patch.set_linewidth(1)
    e.spines['bottom'].set_color('black')
    e.spines['top'].set_color('black')
    e.spines['right'].set_color('black')
    e.spines['left'].set_color('black')

if __name__ == "__main__":
    fig.savefig("./ticker.png")
    fig.savefig("./ticker.svg")

