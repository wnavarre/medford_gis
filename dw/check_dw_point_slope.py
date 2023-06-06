import numpy as np
import pandas
import math
from random import shuffle
import geopandas
import sys
from geopandas import GeoSeries, GeoDataFrame
gpd = geopandas

BIG_DISTANCE = 4096 * 64

def ensure_point_id(data):
    try:
        data["point_id"]
    except KeyError:
        data["point_id"] = np.arange(0, len(data))

def clean_dataframe(data, geo=True):
    data = data.reset_index(drop=True)
    if geo: data.set_geometry("width_slice", inplace=True)
    return data

def with_updated_width_slice(data):
    slice_quadrilaterals = data.stop_width.union(data.start_width).convex_hull
    width_slice = data.width_slice
    del data["width_slice"]
    data["width_slice"] = width_slice.intersection(slice_quadrilaterals)
    if (data.width_slice.geom_type == "Polygon").all(): return data
    pre_explosion_count = len(data)
    data.explode(column="width_slice", ignore_index=True)
    assert pre_explosion_count <= len(data)
    data = data[data.width_slice.intersects(data.depth_line)]
    assert pre_explosion_count == len(data)
    return data

def check_sliced(data, depth, width, slice_count):
    """
    Same columns as check_dw_point_angle, and also uses:
    * width_slice
    
    Passes other columns thru to the filtered result.
    width_slice is removed.
    """
    print("Checking slice_count=", slice_count)
    before_count = len(data)
    needed_area = depth * width / slice_count
    areas = data.width_slice.area
    area_bools = data.width_slice.area >= needed_area
    data = data[area_bools]
    if len(data) == before_count: return data
    data = clean_dataframe(data)
    is_ok_point = data.groupby("point_id").size() >= slice_count
    is_ok_rows = is_ok_point.loc[data.point_id]
    is_ok_rows.reset_index(inplace=True, drop=True)
    out = data.loc[is_ok_rows]
    return out

def do_slicing(data, depth, slice_count, unit_translation):
    """
    All of the inputs describe the OLD.
    Returns tuple of NEW:
    data, slice_count
    """
    front = data.copy(deep=False)
    back  = data.copy(deep=False)
    del front["stop_width"]
    del back["start_width"]
    new_slice_count = slice_count * 2
    print("Slicing new_slice_count=", new_slice_count)
    shift_amount = depth / new_slice_count
    assert shift_amount >= 0.000001
    print("Shifting start")
    shifted_start = front.start_width.translate(
        shift_amount * unit_translation[0],
        shift_amount * unit_translation[1]
    )
    front["stop_width"] = shifted_start
    back["start_width"] = shifted_start
    print("Concatenating...")
    data = gpd.GeoDataFrame(pandas.concat((front, back), ignore_index=True))
    print("Updating width slice...")
    data = with_updated_width_slice(data)
    print("Done-- len(data) is", len(data))
    return data, new_slice_count

def check_dw_point_angle(data, depth, width, rads):
    """
    data is a dataframe with columns:
    * geometry (The parcel)
    * geometry_id (uniquely identifies the parcel)
    * point (a point on the parcel's frontage to test)
    * point_id (should be unique for EVERY row!!!)
    """
    try:
        data["point_id"]
    except KeyError:
        data["point_id"] = np.arange(0, len(data))
    # We will join against input_ids later to get a final result later.
    input_ids = pandas.DataFrame(dict(geometry_id=data.geometry_id, point_id=data.point_id))
    sincos = math.cos(rads), math.sin(rads)
    full_translation = (depth * sincos[0], depth * sincos[1])
    data["end_point"] = data.point.translate(*full_translation)
    data["depth_line"] = data.end_point.union(data.point).convex_hull

    data = data[data["geometry"].covers(data["depth_line"])]
    data = clean_dataframe(data, False)
    negate_tuple = lambda x: tuple(-e for e in x)
    width_angle = rads + math.pi / 2
    big_translation = (BIG_DISTANCE * math.cos(width_angle),
                       BIG_DISTANCE * math.sin(width_angle))

    start_width_a = data.point.translate(*big_translation)
    start_width_b = data.point.translate(*negate_tuple(big_translation))
    data["start_width"] = (start_width_a.union(start_width_b)).convex_hull
    end_width_a = data.end_point.translate(*big_translation)
    end_width_b = data.end_point.translate(*negate_tuple(big_translation))
    data["stop_width"] = (end_width_a.union(end_width_b)).convex_hull
    data["width_slice"] = data["geometry"]
    del data["geometry"]
    data.set_geometry("width_slice", inplace=True)
    data = with_updated_width_slice(data)
    slice_goal = depth * 30
    slice_count = 1
    while True:
        # Check
        data = check_sliced(data, depth, width, slice_count)
        if slice_count >= slice_goal: break
        if len(data) == 0: break
        # Prepare
        data, slice_count = do_slicing(data, depth, slice_count, sincos)
    return data["geometry_id"].unique()

def RationalNumber(float):
    def __new__(cl, numerator, denominator):
        return float.__new__(cl, float(numerator) / denominator)
    def __init__(self, numerator, denominator):
        self._simplified = False
        self._numerator = numerator
        self._denominator = denominator
    def simplify(self):
        if self._simplified: return
        gcd = math.gcd(self._numerator, self._denominator)
        self._numerator = self._numerator // gcd
        self._denominator = self._denominator // gcd
        self._simplified = True
    def __str__(self):
        self.simplify()
        return "({} / {})".format(self._numerator, self._denominator)
        
def all_angle_ratios(n=1000):
    """
    An iterable of n rationals evenly spaced between 0 and 1. (Zero is included, 1 is not).
    Multiply by math.tau to get angles.
    """
    return (i/n for i in range(n))

def interpolate_frontage(data_in):
    src = data_in.copy(deep=False)
    src["frontage_length"] = src["frontage"].length
    pieces = []
    cur_distance = 0
    step = 0.1 # MAGIC NUMBER
    while True:
        src = src[src["frontage_length"] >= cur_distance]
        if 0 == len(src): break
        src["point"] = src["frontage"].interpolate(cur_distance)
        cur_distance += step
        cp = src.copy(deep=False)
        del cp["frontage"]
        pieces.append(cp)
        del src["point"]
    out = GeoDataFrame(pandas.concat(pieces))
    return clean_dataframe(out, False)

def compute_frontage(geometry, possible_frontage, definite_non_frontage):
    # Estimate the frontage area to be all of the property lines within 1m of of "possible_frontage"
    # And at least 1 cm away from definite_non_frontage.
    # *But* explicitly exclude each property's *own* area from definite_non_frontage.
    shape = (len(geometry),)
    possible_frontage = possible_frontage.buffer(1, join_style=2) # MAGIC_NUMBER 1
    possible_frontage = GeoSeries(np.full(shape, possible_frontage))
    # Mitre join to try to avoid weird efffects at corner.
    definite_non_frontage = GeoSeries(np.full(shape, definite_non_frontage)).difference(geometry).buffer(0.01, join_style=3) # MAGIC_NUMBER 0.01
    frontage = geometry.exterior.intersection(possible_frontage)
    frontage = frontage.difference(definite_non_frontage)
    return frontage

def dw_winners_array(data, possible_frontage, definite_non_frontage, depth, width):
    """
    data is a dataframe with columns:
    * geometry (The parcel)
    * geometry_id (uniquely identifies the parcel)
    """
    data["frontage"] = compute_frontage(data.geometry, possible_frontage, definite_non_frontage)
    print(data["geometry_id"].dtype)
    data = interpolate_frontage(data)
    ensure_point_id(data)
    partial_results = []
    angles = list(all_angle_ratios())
    shuffle(angles)
    for angle in angles:
        sys.stdout.flush()
        print("~~~~~~ANGLE:", angle)
        if len(data) == 0: break
        res = check_dw_point_angle(data, depth, width, angle * math.tau)
        if 0 == len(res): continue
        partial_results.append(res)
        right = pandas.DataFrame(dict(
            geometry_id=res,
            ones = np.ones((len(res),), dtype=int)
        ))
        print("type(data[geo_id]): ", data["geometry_id"].dtype)
        print("type(right[geo_id]): ", right["geometry_id"].dtype)
        print("ABOUT TO DO THE JOIN!")
        sys.stdout.flush()
        data2 = data.merge(right, on="geometry_id", how="left")
        data2 = data2.reset_index(drop=True)
        data = data[data2["ones"] != 1]
        data = clean_dataframe(data, False)
    return np.unique(np.concatenate(partial_results))
