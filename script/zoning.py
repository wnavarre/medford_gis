import pandas
from geopandas import *

def find_zones(plots, zone_names, zone_shapes, *, default="NOZONE"):
    length, = plots.shape
    win_area = pandas.Series(data=([0.0] * length)) 
    win_name = pandas.Series(data=(["NOZONE"] * length))
    for zone_name, zone_shape in zip(zone_names, zone_shapes):
        print("Doing", zone_name)
        zone_area = plots.intersection(zone_shape).area
        beat = zone_area > win_area
        win_area.mask(beat, other=zone_area, inplace=True)
        win_name.mask(beat, other=zone_name, inplace=True)
    return win_name

