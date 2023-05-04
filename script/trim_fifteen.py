import load_data
import util
import math

def trim(s, ft):
    boundary = s.boundary
    fifteen_setback = boundary.buffer(util.feet_to_meters(ft))
    trimmed = s.difference(fifteen_setback)
    return trimmed

def trim_15(): return trim(load_data.gdf["geometry"], 15)

def with_trim_15_area():
    trimmed = trim_15()
    areas = trimmed.area
    geo = load_data.gdf.copy()    
    geo.insert(len(geo.columns),
               "Trimmed Areas 15",
               areas)
    return geo

def trim_unusable_space(s, ft):
    """
    ft *roughly* corresponds to half the minimum
    width of a piece of the building.
    """
    trimmed = trim(s, ft)
    accessible_to = trimmed.buffer(util.feet_to_meters(ft), join_style=2)
    trimmed = trimmed.union(accessible_to)
    return trimmed.intersection(s)
