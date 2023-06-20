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
#import dask_geopandas as gdask
#import dask
from infect import infect
from flexible_key import *
from fast_rotate import rotate_points_fast, fast_translate
from performance_logging import log_time, TimerLog
from enum import Enum
import copy

def nonone(ls): return [ x for x in ls if (x is not None) ]

gpd = geopandas

THREAD_COUNT = 8
DEBUG_MODE = True
MITRE = 2
BEVEL = 3

GLOBAL_CALLBACK = None

def function_that_does_nothing(*a, **b): pass

dprint = print

class LoggingEvent(Enum):
    CHECK_SLICES = 1

DEBUG_MODE = True

class DistanceBase: pass

class DistanceFeet(DistanceBase):
    __slots__ = ("_ft", "_m")
    def __init__(self, ft):
        self._ft = ft
        self._m = ft * FEET
    def gis(self):  return self._m
    def feet(self): return self._ft

def make_distance(v, default=DistanceFeet):
    if isinstance(v, DistanceBase): return v
    return default(v)

def narrow_lot_ids(frame, depth, width):
    needed = min(depth.gis(), width.gis()) - 0.1 * MILLIMETER
    bounds = frame.lot.bounds
    h = bounds.maxx - bounds.minx
    v = bounds.maxy - bounds.miny
    too_narrow = (h < needed) | (v < needed)
    if not too_narrow.any(): return None
    out = frame.lot_id[too_narrow]
    print("Identified {} lots that fail based on the width test!".format(len(out)))
    return out

class DWWorkingTable:
    def __init__(self, source, rads):
        timer = TimerLog("Constructed DWWorkingTable")
        source.working_lot() # CHECK...
        depth = source._depth
        width = source._width
        self._depth = depth
        self._width = width
        self._slice_count = 0
        self._source = source
        rotated_lots = source.rotated_lots(rads)
        width_test_failures = narrow_lot_ids(rotated_lots, depth, width)
        if width_test_failures is not None:
            self.source().discard_lots(width_test_failures)
        self._data = rotated_lots.merge(
            source.rotated_points(rads),
            how="left",
            on="lot_id"
        )
        depth = depth.gis()
        width = width.gis()
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
            fast_translate(self._data.point, -BIG_DISTANCE, 0),
            fast_translate(self._data.point, +BIG_DISTANCE, 0)
        )
        self["stop_width"] = convex_hull(
            fast_translate(self._data.point, -BIG_DISTANCE, depth),
            fast_translate(self._data.point, +BIG_DISTANCE, depth)
        )
        del self._data["point"]
        self._update_width_slice()
        self._slice_count = 1
        timer.stop()
    def __setitem__(self, k, v):
        if hasattr(v, "set_crs"):
            crs = self.source().crs()
            assert crs is not None
            v = v.set_crs(crs=crs)
        self._data[k] = v
    def key_to_id(self): return self.source().key_to_id()
    def empty(self): return not len(self._data)
    def depth_gis(self): return self._depth.gis()
    def width_gis(self): return self._width.gis()
    def depth_feet(self): return self._depth.feet()
    def width_feet(self): return self._width.feet()
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
        needed_area = (self.depth_gis()) * (self.width_gis()) / self._slice_count
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
        point_success = ((slice_width >= self.width_gis())
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
        shift_amount = self.depth_gis() / self._slice_count
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
    def __init__(self, data, depth, width, cache=None):
        assert (data.geometry.crs is not None) or (data.crs is not None)
        self._depth = depth
        self._width = width
        self._data = GeoDataFrame(dict(
            strict_lot=data.geometry,
            lot_id=get_matching_key(data, "lot_id", "geometry_id")
        ), geometry="strict_lot", crs=data.geometry.crs)
        self._lot_id_for_output = self._data.lot_id
        assert self._data.crs is not None
        assert self.lot_id().dtype == np.uint64
        minx, miny, maxx, maxy = self.strict_lot().total_bounds
        self._rotation_point = ((minx + maxx) / 2), ((miny + maxy) / 2)
        self._cache = cache
        if cache is not None:
            cache_key = cache.cache_key
            key_to_id = dict(
                zip(data[cache_key], self._data.lot_id)
            )
            winners_st, losers_st = cache.retrieve_results(depth.feet(), width.feet())
            cache_winners_array = np.array(nonone(key_to_id.get(w) for w in winners_st), dtype=int)
            self._cache_winners_mask = self.lot_id_mask(cache_winners_array)
            cache_win_lose_array = np.concatenate([
                cache_winners_array,
                np.array(nonone(key_to_id.get(l) for l in losers_st), dtype=int)
            ])
            self.discard_lots(cache_win_lose_array, frontage_points=False)
            self._info_for_cache_save = self.combine_key_and_id(self._data.lot_id, data, cache_key)
            self.trim(-1, dry_run=True)
    @staticmethod
    def combine_key_and_id(id_series, table, cache_key_nm):
        left  = pandas.DataFrame(dict(lot_id=id_series))
        right = pandas.DataFrame(dict(
            lot_id=get_matching_key(table, "lot_id", "geometry_id"),
            cache_key=table[cache_key_nm]
        ))
        return left.merge(right, on="lot_id", how="inner")
    def depth_gis(self): return self._depth.gis()
    def width_gis(self): return self._width.gis()
    def depth_feet(self): return self._depth.feet()
    def width_feet(self): return self._width.feet()
    def trim(self, desired_count, *, dry_run=False):
        assert self.count() >= desired_count
        assert len(self._data) == len(self._info_for_cache_save)
        if DEBUG_MODE:
            assert (self._data.lot_id == self._info_for_cache_save.lot_id).all()
        if dry_run: return None
        trim_mask = np.concatenate([
            np.ones((desired_count,), dtype=bool),
            np.zeros((self.count() - desired_count,), dtype=bool)
        ])
        new_data = GeoDataFrame({
            "geometry": self._data.strict_lot[trim_mask],
            "lot_id"  : self._data.lot_id[trim_mask],
            self._cache.cache_key : self._info_for_cache_save.cache_key[trim_mask]
        }, geometry="geometry", crs=self.crs())
        return DWCandidatesTable(new_data, self._depth, self._width, cache=self._cache)
    def log_winners_in_cache(self, winning_ids):
        if self._cache is None: return
        winning_mask = mask_for_value_set(self._info_for_cache_save,
                                          "lot_id",
                                          winning_ids,
                                          True)
        losing_mask = np.logical_not(winning_mask)
        self._cache.store_winners(self.depth_feet(), self.width_feet(),
                                  self._info_for_cache_save.cache_key[winning_mask])
        self._cache.store_losers(self.depth_feet(), self.width_feet(),
                                 self._info_for_cache_save.cache_key[losing_mask])
    def __len__(self): return self.count()
    def count(self): return len(self._data)
    def empty(self): return not self.count()
    def cache_key(self): return self._cache_key
    def key_to_id(self): return self._key_to_id
    def clean(self, points_too=False):
        self._modified = True
        self._data = clean_dataframe(self._data)
        if points_too: self._frontage_points = clean_dataframe(self._frontage_points)
    def lot_id_mask(self, lot_ids):
        return mask_for_value_set(self._data, "lot_id", lot_ids, True)
    def crs(self):
        assert self._data.crs is not None
        return self._data.crs
    def strict_lot(self): return self._data.strict_lot
    def working_lot(self): return self._data.working_lot
    def lot_id(self): return self._data.lot_id
    def filter_by_area(self):
        minimum_area = self.depth_gis() * self.width_gis()
        lots = self._data.lot_id[self.working_lot().area < minimum_area]
        self.discard_lots(lots)
        return len(lots)
    def full_winners_mask(self, winning_ids):
        if winning_ids is None: return self._cache_winners_mask
        df = pandas.DataFrame(dict(
            the=self._lot_id_for_output
        ))
        out = mask_for_value_set(df, "the", winning_ids, True)
        if self._cache is None:
            return out
        else:
            return self._cache_winners_mask | out
    def discard_lots(self, vals, *, frontage_points=True):
        """
        Returns the mask used to do the discard from _data.
        """
        data_mask = mask_for_value_set(self._data, "lot_id", vals, False)
        self._data = self._data[data_mask]
        if frontage_points:
            self._frontage_points = discard_matching(self._frontage_points, "lot_id", vals)
        self.clean(frontage_points)
        return data_mask
    def rotated_lots(self, rads):
        # TODO: Do the "too narrow" optimization!
        print("Rotating {} lots.".format(len(self._data)))
        return GeoDataFrame(dict(
            lot=self.working_lot().rotate(rads, self._rotation_point, use_radians=True),
            lot_id=self._data.lot_id
        ), geometry="lot")
    def rotated_points(self, rads):
        print("Rotating {} points.".format(len(self._frontage_points)))
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
            cur_distance = loop_count * 0.45
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
        dprint("Inferring frontage for {} geometries".format(len(self._data)))
        shp = len(self._data),
        border_near_row = (GeoSeries(np.full(shp, right_of_way_geo.buffer(1, join_style=MITRE)),
                                     crs=self.crs())
                           .intersection(self.strict_lot().exterior))
        neighboring_property = (GeoSeries(np.full(shp, property_geo), crs=self.crs())
                                .difference(self.strict_lot())
                                .intersection(self.strict_lot().
                                              envelope.buffer(2, join_style=MITRE)));
        lines = border_near_row.difference(neighboring_property)
        self.infer_frontage_points_from_lines(lines, buffer_lots=buffer_lots)
        dprint("Infered frontage for {} geometries".format(len(self._data)))
        return self

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
    slice_goal = table.depth_gis() * 30
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

def dw_winners_array_impl(cand_table, angles=1000):
    """
    data is a dataframe with columns:
    * geometry (The parcel)
    * geometry_id (uniquely identifies the parcel)
    """
    print(   "##########################################################")
    log_time("###################Entering algorithm (depth={}, width={})".format(
        cand_table.depth_feet(), cand_table.width_feet()
    ))
    print(   "##########################################################")
    partial_results = []
    angles = list(all_angle_ratios(angles))
    
    print("Eliminated {} lots by area.".format(cand_table.filter_by_area()))
    for idx, angle in enumerate(angles):
        timer = TimerLog("Handled one angle.")
        if cand_table.empty(): break
        working_table = DWWorkingTable(cand_table, angle * math.tau)
        res = check_working_table(working_table)
        if (res is not None) and len(res): partial_results.append(res)
        timer.stop()
    if not partial_results:
        return []
    return np.unique(np.concatenate(partial_results))

def dw_winners_array(df, row, all_property, depth_in, width_in, angles=1000):
    depth, width = map(make_distance, (depth_in, width_in))
    table = DWCandidatesTable(df, depth, width).infer_frontage_from_geometries(row, all_property)
    return dw_winners_array_impl(table, angles=angles)

def dw_winners_mask_feet(data, possible_frontage, definite_non_frontage, depth_in, width_in,
                         cache=None, **argv):
    depth, width = map(make_distance, (depth_in, width_in))
    LIMIT = 800
    def go(cur_cand_table, *, final=False):
        cur_cand_table.infer_frontage_from_geometries(possible_frontage, definite_non_frontage)
        winners_result = dw_winners_array_impl(cur_cand_table, **argv)
        cur_cand_table.log_winners_in_cache(winners_result)
        if not final: return None
        return cur_cand_table.full_winners_mask(winners_result)
    last_length = None
    while True:
        candidate_table = DWCandidatesTable(data, depth, width, cache=cache)
        if last_length is not None:
            assert last_length > len(candidate_table)
            last_length = len(candidate_table)
        print("{} geometries need work".format(len(candidate_table)))
        if not len(candidate_table): return candidate_table.full_winners_mask(None)
        if candidate_table.count() <= LIMIT: return go(candidate_table, final=True)
        if cache is None:
            raise ValueError("Cache required for datasets over {} geometries.".format(LIMIT))
        candidate_table = candidate_table.trim(LIMIT)
        go(candidate_table)
        candidate_table = None
