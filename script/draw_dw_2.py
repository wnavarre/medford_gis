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
from frame_set_operations import *
from performance_logging import *
from ticker import *

log_time("beginning full process")
raw_parcels = geopandas.read_parquet("../medford_shp/medford.pqt",
                                     columns=["geometry",
                                              "POLY_TYPE",
                                              "ZONE",
                                              "LOC_ID"]).to_crs(epsg=3857)
print("raw_parcels.crs", raw_parcels.crs)
all_right_of_way = raw_parcels.geometry[raw_parcels.POLY_TYPE == "ROW"].unary_union

parcels = raw_parcels[(raw_parcels.POLY_TYPE == "FEE") | (raw_parcels.POLY_TYPE == "TAX")]
#parcels = parcels[parcels.geometry.exterior.length < 2000]
#parcels = parcels[GR.SOUTH.rect().covers(parcels.geometry)]
parcels = clean_dataframe(parcels)

def lot_big_enough(features, idx):
    print("len(features)", len(features))
    out = BoolTickerResult(np.ones((len(features),), dtype=bool))
    return out

fig, ax = bool_ticker(parcels, lot_big_enough, GR.SOUTH, count_x=1, count_y=1,
                      width=7/3, true_color=GOOD_COLOR, false_color=BAD_COLOR,
                      legend_kwds={'loc': "upper right", 'fontsize' : 6 })

fig.subplots_adjust(hspace=2/72, wspace=2/72, left=0, right=1, top=1, bottom=0)

if __name__ == "__main__":
    fig.savefig("./draw_dw_2_out.png")
