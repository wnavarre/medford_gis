import random
import contextily as cx
import geopandas
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pylab
from medford_regions import GR, FULL_CITY
from mapping import *
from units import *
from basic_frame_operations import *
from dw import dw_winners_mask_feet
import dw
from dw_cache import DWCache
from frame_set_operations import *
from performance_logging import *
from ticker import *

log_time("beginning full process")
raw_parcels = geopandas.read_parquet("../medford_shp/medford.pqt",
                                     columns=["geometry",
                                              "POLY_TYPE",
                                              "ZONE",
                                              "LOC_ID"]).to_crs(epsg=3857)

all_right_of_way = raw_parcels.geometry[raw_parcels.POLY_TYPE == "ROW"].unary_union

parcels = raw_parcels[(raw_parcels.POLY_TYPE == "FEE") | (raw_parcels.POLY_TYPE == "TAX")]
parcels = parcels[parcels.geometry.exterior.length < 1500]

assert parcels.geometry.is_valid.all()

assert len(parcels)

cache = DWCache("dwcache")
cache.cache_key = "LOC_ID"
assert len(parcels[cache.cache_key]) == len(set(parcels[cache.cache_key]))

parcels["geometry_id"] = np.arange(0, len(parcels), dtype=np.uint64)
parcels = clean_dataframe(parcels)

all_parcels = parcels.geometry.unary_union

print("MAX LENGTH: ", parcels.geometry.exterior.length.max())

#parcels = parcels[(parcels.ZONE == 'APT1') |
#                  (parcels.ZONE == 'APT2') |
#                  (parcels.ZONE == 'C1')]
#parcels = clean_dataframe(parcels)

del raw_parcels

def lot_big_enough_flexible(features, depth, width):
    return dw_winners_mask_feet(parcels,
                                all_right_of_way,
                                all_parcels,
                                depth, width,
                                cache=cache)

CWANTS = []

print("DOING CWANTS")
for i in range(22):
    for j in range(22):
        CWANTS.append(((i + 1) * 5, (j + 1)*5))

random.shuffle(CWANTS)

for depth, width in CWANTS:
    big = max(depth, width)
    small = min(depth, width)
    if small * 2 < big: continue
    print("DOING CWANTS depth={} width={}".format(depth, width))
    lot_big_enough_flexible(parcels, depth, width)

print("DONE WITH CWANTS")
WANTS = [(60, 60),
         (80, 80),
         (50, 50),
         (70, 70),
         (100, 75),
         (100, 90),
         (60, 60),
         (50, 40),
         (30, 30),
         (10, 10),
         (60, 60),
         (50, 50),
         (40, 40),
         (60, 50),
         (60, 40),
         (60, 30),
         (100, 80),
         (100, 50),
         (100, 40)]

def lot_big_enough(features, idx):
    depth, width = WANTS[idx]
    res = lot_big_enough_flexible(features, depth, width)
    out = BoolTickerResult(res)
    out.true_label  = "> d={}  and w={}".format(depth, width)
    out.false_label = "< d={}  and w={}".format(depth, width)
    return out

parcels = clean_dataframe(parcels)

fig, ax = bool_ticker(parcels, lot_big_enough, FULL_CITY.FULL, count_x=1, count_y=1,
                      width=7, true_color=GOOD_COLOR, false_color=BAD_COLOR,
                      legend_kwds={'loc': "upper right", 'fontsize' : 6 })

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
    fig.savefig("./out2.png")
