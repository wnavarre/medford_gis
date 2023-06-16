import itertools
import matplotlib.pyplot as plt
import numpy as np
import pandas
import math
from random import shuffle
import geopandas
import sys
from functools import reduce
from geopandas import GeoSeries, GeoDataFrame
from frame_set_operations import *
from basic_frame_operations import *
from units import *
import df_parallel
#import dask_geopandas as gdask
#import dask
from infect import infect
from flexible_key import *
from fast_rotate import rotate_points_fast, fast_translate
from performance_logging import log_time
from enum import Enum
import copy

gpd = geopandas

THREAD_COUNT = 8
DEBUG_MODE = True
MITRE = 2
BEVEL = 3

GLOBAL_CALLBACK = None

def function_that_does_nothing(*a, **b): pass

dprint = function_that_does_nothing

class LoggingEvent(Enum):
    CHECK_SLICES = 1

    
class DWWorkingTable:
    def __init__(self, source, rads, depth, width):
        assert source.is_single_use()
        source.working_lot() # CHECK...
        self._depth = depth
        self._width = width
        self._slice_count = 0
        self._source = source
        self._data = source.rotated_lots(rads).merge(
            source.rotated_points(rads),
            how="left",
            on="lot_id"
        )
        self["depth_line"] = convex_hull(self._data.point,
                                               fast_translate(self._data.point, 0, depth))
        self._data = self._data[self._data.lot.covers(self._data.depth_line)]
        self.clean()
        self["lft_side"] = convex_hull(self._data.point,
                                             fast_translate(self._data.point, 0, depth),
                                             fast_translate(self._data.point, -BIG_DISTANCE, depth),
                                             fast_translate(self._data.point, -BIG_DISTANCE, depth))
        self["rgt_side"] = convex_hull(self._data.point,
                                             fast_translate(self._data.point, 0, depth),
                                             fast_translate(self._data.point, +BIG_DISTANCE, depth),
                                             fast_translate(self._data.point, +BIG_DISTANCE, depth))
        self["start_width"] = convex_hull(
            fast_translate(self._data.point, -BIG_DISTANCE, 0    ),
            fast_translate(self._data.point, +BIG_DISTANCE, 0    )
        )
        self["stop_width"] = convex_hull(
            fast_translate(self._data.point, -BIG_DISTANCE, depth),
            fast_translate(self._data.point, +BIG_DISTANCE, depth)
        )
        del self._data["point"]
        self._update_width_slice()
        self._slice_count = 1
    def __setitem__(self, k, v):
        if hasattr(v, "set_crs"):
            crs = self.source().crs()
            dprint("CRS:", crs)
            assert crs is not None
            v = v.set_crs(crs=crs)
        self._data[k] = v
    def key_to_id(self): return self.source().key_to_id()
    def empty(self): return not len(self._data)
    def depth(self): return self._depth
    def current_lot_ids(self): return np.unique(self._data.lot_id.to_numpy())
    def slice_count(self): return self._slice_count
    def _update_width_slice(self):
        self._data["width_slice_mask"] = df_convex_hull(self._data, "start_width", "stop_width")
        self._data["width_slice"]      = self._data.width_slice_mask.intersection(self._data.lot)
        if (self._data.width_slice.geom_type == "Polygon").all(): return
        pre_explosion_count = len(self._data)
        self._data = self._data.explode(column="width_slice", ignore_index=True)
        assert len(self._data) >= pre_explosion_count
        self._data = self._data[self._data.width_slice.intersects(self._data.depth_line)]
        assert len(self._data) == pre_explosion_count
        self.clean()
    def _prune_losers(self):
        needed_area = self._depth * self._width / self._slice_count
        # Each row corresponds to a slice; each column corresponds to a point.
        # Goal is to reject the whole point if one of its slices lacks the needed area.
        point_slice_success = ((self._data.width_slice.area >= needed_area)
                               .to_numpy()
                               .reshape(self._slice_count, -1))
        point_success = point_slice_success.all(0)
        self._data = self._data[np.tile(point_success, self._slice_count)]
        self.clean()
    def _catch_immediate_winners(self):
        lft_invert = (self._data.width_slice_mask
                      .intersection(self._data.lft_side)
                      .difference(self._data.lot))
        rgt_invert = (self._data.width_slice_mask
                      .intersection(self._data.rgt_side)
                      .difference(self._data.lot))
        slice_width = rgt_invert.bounds.minx - lft_invert.bounds.maxx
        # Each row corresponds to a slice; each column corresponds to a point.
        point_success = ((slice_width >= self._width)
                         .to_numpy()
                         .reshape(self._slice_count, -1)).all(0)
        if not point_success.any(): return None
        one_slice_of_lot_id = self._data.lot_id.to_numpy()[0:len(point_success)]
        winners = one_slice_of_lot_id[point_success]
        infect(one_slice_of_lot_id, point_success)
        remaining_points_mask = np.tile(
            np.logical_not(point_success),
            self._slice_count
        )
        self._data = self._data[remaining_points_mask]
        self.clean()
        return winners
    def check_sliced(self):
        self._prune_losers()
        return self._catch_immediate_winners()
    def do_slicing(self):
        front = self._data.copy(deep=False)
        back = self._data.copy(deep=False)
        del front["stop_width"]
        del back["start_width"]
        self._slice_count *= 2
        shift_amount = self._depth / self._slice_count
        assert shift_amount >= 0.000001
        shifted_start = front.start_width.translate(0, shift_amount)
        front["stop_width"] = shifted_start
        back["start_width"] = shifted_start
        self._data = gpd.GeoDataFrame(pandas.concat((front, back), ignore_index=True))
        self._update_width_slice()
    def clean(self, points_too=False):
        self._data = clean_dataframe(self._data)
        if points_too: self._frontage_points = clean_dataframe(self._frontage_points)
    def crs(self):
        out = self._source.crs()
        assert out is not None
        return out
    def lot(self): return self._data.lot
    def source(self): return self._source

class DWCandidatesTable:
    def __init__(self, data, cache_key=None):
        assert (data.geometry.crs is not None) or (data.crs is not None)
        self._data = GeoDataFrame(dict(
            strict_lot=data.geometry,
            lot_id=get_matching_key(data, "lot_id", "geometry_id")
        ), geometry="strict_lot", crs=data.geometry.crs)
        assert self._data.crs is not None
        assert self.lot_id().dtype == np.uint64
        minx, miny, maxx, maxy = self.strict_lot().total_bounds
        self._rotation_point = ((minx + maxx) / 2), ((miny + maxy) / 2)
        self._is_reusable = True
        if cache_key is not None:
            self._cache_key = data[cache_key]
            self._key_to_id = dict(
                zip(data[cache_key], self._data.lot_id)
            )
        self._modified = False
    def empty(self): return not len(self._data)
    def cache_key(self): return self._cache_key
    def key_to_id(self): return self._key_to_id
    def clean(self, points_too=False):
        self._modified = True
        self._data = clean_dataframe(self._data)
        if points_too: self._frontage_points = clean_dataframe(self._frontage_points)
    def lot_id_mask(self, lot_ids):
        assert not self._modified
        return mask_for_value_set(self._data, "lot_id", lot_ids, True)
    def is_reusable(self): return self._is_reusable
    def is_single_use(self): return not self._is_reusable
    def single_use_copy(self):
        out = copy.copy(self)
        out._data = self._data.copy(deep=False)
        out._is_reusable = False
        return out
    def crs(self):
        assert self._data.crs is not None
        return self._data.crs
    def strict_lot(self): return self._data.strict_lot
    def working_lot(self): return self._data.working_lot
    def lot_id(self): return self._data.lot_id
    def discard_lots(self, vals):
        assert not self._is_reusable
        self._data = discard_matching(self._data, "lot_id", vals)
        self._frontage_points = discard_matching(self._frontage_points, "lot_id", vals)
        self.clean(True)
    def rotated_lots(self, rads):
        # TODO: Do the "too narrow" optimization!
        return GeoDataFrame(dict(
            lot=self.working_lot().rotate(rads, self._rotation_point, use_radians=True),
            lot_id=self._data.lot_id
        ), geometry="lot")
    def rotated_points(self, rads):
        return GeoDataFrame(dict(
            lot_id=self._frontage_points.lot_id,
            point=rotate_points_fast(self._frontage_points.geometry,
                                     rads, origin=self._rotation_point)
        ), geometry="point")
    def set_frontage_points(self, points, *, buffer_lots=True):
        points.lot_id   # Check
        points.geometry # Check
        self._frontage_points = points
        if buffer_lots:
            self._data["working_lot"] = (self.strict_lot()
                                         .buffer(EPSILON, join_style=MITRE)
                                         .simplify(EPSILON / 4))
            # The simplify is because otherwise rotation is liable to
            # create an invalid polygon: good luck debugging that!
            del (self._data)["strict_lot"]
            self._data = self._data.set_geometry("working_lot")
            self._data.geometry
        return self
    def infer_frontage_points_from_lines(self, lines, *, buffer_lots=True):
        pieces, cur_distance = [], 0
        ll = GeoDataFrame(dict(
            geometry=lines,
            lot_id=self.lot_id()
        ))
        for loop_count in itertools.count():
            cur_distance = loop_count * 0.3
            ll = ll[ll.geometry.length >= cur_distance]
            if not len(ll): break
            pieces.append(GeoDataFrame(dict(
                lot_id=ll.lot_id,
                point=ll.geometry.interpolate(cur_distance)
            )))
        return self.set_frontage_points(GeoDataFrame(pandas.concat(pieces, ignore_index=True)).set_geometry("point"), buffer_lots=buffer_lots)
    def infer_frontage_from_geometries(self, right_of_way_geo, property_geo, *, buffer_lots=True):
        # Assume that frontage is all points on the border that are
        # within 1 meter of the right of way and at least 3 centimeters from
        # any other property.
        shp = len(self._data),
        border_near_row = (GeoSeries(np.full(shp, right_of_way_geo.buffer(1, join_style=MITRE)),
                                     crs=self.crs())
                           .intersection(self.strict_lot().exterior))
        neighboring_property = (GeoSeries(np.full(shp, property_geo), crs=self.crs())
                                .difference(self.strict_lot())
                                .intersection(self.strict_lot().
                                              envelope.buffer(2, join_style=MITRE)));
        lines = border_near_row.difference(neighboring_property)
        return self.infer_frontage_points_from_lines(lines, buffer_lots=buffer_lots)

def apply_frontage_distance_test(data, depth, width):
    """
    We need enough of the area to be within the required lot depth to matter.
    """
    area_near_frontage = data.frontage.buffer(depth).intersection(data.geometry).area
    data = data[area_near_frontage >= ((depth - EPSILON) * (width - EPSILON))]
    return clean_dataframe(data)

def check_working_table(table):
    """
    * geometry (The parcel)
    * geometry_id (uniquely identifies the parcel)
    * point (a point on the parcel's frontage to test)
    * point_id (should be unique for EVERY row!!!)

    Depth is parallel to y axis with the frontage point having the lowest Y-value of the depth.

    Description of algorithm:
    * Draw the depth on the geometry. Immediate fail if it goes outside the geometry.
    * Recusively slice the geometry with lines perpendicular to the depth into 2^n pieces (beginning n=0).
    * * Do this separately on the left and right side of the depth. (So double the slices but across 2 cols)
    * Examine the full slice for LOSERS on the basis of area.
    * Using the 2^(n + 1) slicing geometries as the "universe", create the inverse as the lot's geometry.
    * Compute the extrema of these inverse. Infer a minimum width within the slice in order to
      try to immediately declare a winner.
    """
    
    log_time("Doing preparatory work")
    slice_goal = table.depth() * 30
    winners_list = []
    while True:
        winners = table.check_sliced()
        if winners is not None: winners_list.append(np.unique(winners))
        if table.slice_count() >= slice_goal: break
        if table.empty(): break
        table.do_slicing()
    winners_list.append(table.current_lot_ids())
    out = np.concatenate(winners_list)
    table.source().discard_lots(out)
    return out

class SimplifiedRational:
    def __init__(self, numerator, denominator):
        gcd = math.gcd(numerator, denominator)
        self._numerator = numerator // gcd
        self._denominator = denominator // gcd
    def __float__(self): return self._numerator / self._denominator
    def denominator(self): return self._denominator
        
def all_angle_ratios(n=1000):
    """
    An iterable of n rationals evenly spaced between 0 and 1. (Zero is included, 1 is not).
    Multiply by math.tau to get angles.
    """
    ratios = [ SimplifiedRational(i, n) for i in range(n) ]
    ratios.sort(key=lambda r: r.denominator())
    ratios = [ float(r) for r in ratios]
    return ratios

def dw_winners_array_impl(unrotated_table, depth, width, *, angles=1000):
    """
    data is a dataframe with columns:
    * geometry (The parcel)
    * geometry_id (uniquely identifies the parcel)
    """
    partial_results = []
    angles = list(all_angle_ratios(angles))
    if unrotated_table.is_reusable(): unrotated_table = unrotated_table.single_use_copy()
    assert unrotated_table.is_single_use()
    for idx, angle in enumerate(angles):
        if unrotated_table.empty(): break
        working_table = DWWorkingTable(unrotated_table, angle * math.tau, depth, width)
        res = check_working_table(working_table)
        if (res is None) or (0 == len(res)): continue
        partial_results.append(res)
    if not partial_results:
        return []
    return np.unique(np.concatenate(partial_results))

def dw_winners_array(df, row, all_property, depth, width, angles=1000):
    table = DWCandidatesTable(df).infer_frontage_from_geometries(row, all_property).set_single_use()
    return dw_winners_array_impl(table, depth, width, angles=angles)

def nonone(ls): return [ x for x in ls if (x is not None) ]

def dw_winners_mask_feet_impl(cand_table, depth, width, *, cache=None, **argv):
    print(   "##########################################################")
    log_time("###################Entering algorithm (depth={}, width={})".format(depth, width))
    print(   "##########################################################")
    original_table, cand_table = cand_table, cand_table.single_use_copy()
    if cache is not None:
        # cache_key will generally be the name of a string column
        # while geometry_id will generally be an arbitrary integer
        winners_st, losers_st = cache.retrieve_results(depth, width)
        cache_winners_array = np.array(nonone(key_to_id.get(w) for w in winners_st), dtype=int)
        cache_win_lose_array = np.concatenate([
            cache_winners_array,
            np.array(nonone(cache_key_to_geometry_id.get(l) for l in losers_st), dtype=int)
        ])
        cand_table.discard_lots(cache_win_lose_array)
        mask_c = original_table.lot_id_mask(cache_winners_array)
        del cache_winners_array
        del cache_win_lose_array
    else:
        print("CACHE IS NONE!")
    a = dw_winners_array_impl(cand_table, depth * FEET, width * FEET, **argv)
    mask_a = original_table.lot_id_mask(a)
    if cache is not None:
        print("STORING!")
        cache.store_winners(depth, width, original_table.cache_key()[mask_a])
        cache.store_losers(depth, width, original_table.cache_key()[np.logical_not(mask_a)])
        return mask_a | mask_c
    else:
        print("CACHE IS NONE!")
        return mask_a

def dw_winners_mask_feet(data, possible_frontage, definite_non_frontage, depth, width,
                         cache=None, **argv):
    return dw_winners_mask_feet_impl(
        DWCandidatesTable(data, cache_key=None if cache is None else cache.cache_key)
        .infer_frontage_from_geometries(possible_frontage, definite_non_frontage),
        depth, width, cache=None, **argv)
