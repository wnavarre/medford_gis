import os
from shutil import rmtree
import unittest
import shapely
import pandas
import pandas as pd
from shapely import MultiPoint, Point
from dw import *
import geopandas as gpd
from geopandas import GeoSeries, GeoDataFrame
import math
import numpy as np
import dw_cache
from dw_cache import DWCache, DWCacheFile
from dw_legacy import *

EPSG=3857

def translate(geo, coords):
    return shapely.transform(geo, lambda x: x + coords)
    
def basic_rect(x, y, translation=(0., 0.)):
    out = MultiPoint([(0., 0.), (x, y)]).envelope
    return translate(out, translation)

def basic_line(x, y, translation=(0., 0.)):
    out = MultiPoint([(0., 0.), (x, y)]).convex_hull
    return translate(out, translation)

class TestCheckSliced:
    """
    Disabled for now because it's a pain to adapt these to the new convention...
    """
    def test_1(self):
        rect = basic_rect(75, 41)
        corner = basic_rect(100, 100, (10, 20))
        lot = shapely.difference(rect, corner)
        bottom = basic_line(BIG_DISTANCE * 2, 0, (-BIG_DISTANCE, 0))
        middle = translate(bottom, (0, 20))
        top = translate(bottom, (0, 40))
        lots = GeoSeries([lot] * 2).set_crs(epsg=3857)
        depth_line = basic_line(0, 40., (0., 4.))
        df = gpd.GeoDataFrame(dict(
            geometry=lots,
            geometry_id=np.array([1, 1], dtype=np.uint64),
            point_id=np.array([0, 0], dtype=np.uint64),
            start_width=GeoSeries([bottom, middle]).set_crs(epsg=3857),
            stop_width=GeoSeries([middle, top]).set_crs(epsg=3857),
            depth_line=GeoSeries([depth_line] * 2).set_crs(epsg=3857)
        ))
        df = with_updated_width_slice(df, is_first=True)
        data, winners = check_sliced(df, 40, 20, 2)
        self.assertEqual(len(data), 0)
        self.assertEqual(len(winners), 0)
    def test_winner(self):
        SET_CRS = dict(epsg=3857)
        GeoSeries().set_crs(epsg=3857)
        box = shapely.box(0., 0., 20.5, 40.5)
        d = 40
        w = 20
        df = gpd.GeoDataFrame(dict(
            geometry=GeoSeries([box]).set_crs(**SET_CRS),
            geometry_id=np.array([0], dtype=np.uint64),
            point_id=np.array([10], dtype=np.uint64),
            start_width=GeoSeries([basic_line(BIG_DISTANCE * 2, 0, (-BIG_DISTANCE, 0))]).set_crs(**SET_CRS),
            stop_width=GeoSeries( [basic_line(BIG_DISTANCE * 2, 0, (-BIG_DISTANCE, d))]).set_crs(**SET_CRS),
            depth_line=GeoSeries( [basic_line(0, d, (3, 0))]).set_crs(**SET_CRS)
        ))
        print("df.depth_line[0]", df.depth_line[0])
        df = with_updated_width_slice(df, is_first=True)
        print("df.lft_side[0]", df.lft_side[0])
        print("df.rgt_side[0]", df.rgt_side[0])
        data, winners = check_sliced(df, d, w, 1)
        self.assertFalse(len(data))
        self.assertTrue(len(winners))

class TestDWPointSlope(unittest.TestCase):
    def test_notched_rectangle(self):
        rect = MultiPoint([(0., 0.), (15.05, 40.05)]).envelope
        notch = MultiPoint([(14.9, 30.), (100., 35.)]).envelope
        notched_rect = shapely.difference(rect, notch)
        point = Point(4., 0.)
        df = gpd.GeoDataFrame(dict(
            geometry=GeoSeries([notched_rect]).set_crs(epsg=3857),
            geometry_id=np.array([0], dtype=np.uint64),
            point=GeoSeries([point]).set_crs(epsg=3857)
        ), geometry="geometry")
        res = check_dw_point_y_depth(df, 40, 15)
        res = set(iter(res))
        self.assertEqual(res, set())
    def test_straight_rectangle_variations(self):
        rect = MultiPoint([(0., 0.), (15.05, 40.05)]).envelope
        notch = MultiPoint([(14.9, 30.), (100., 30.1)]).envelope
        long_but_narrow_rect = MultiPoint([(0., 0.), (14.5, 250)])
        notched_rect = shapely.difference(rect, notch)
        point = Point(4., 0.)
        RECT, NOTCHED_RECT, LONG_BUT_NARROW = range(3)
        df = gpd.GeoDataFrame(dict(
            geometry=GeoSeries([rect, notched_rect, long_but_narrow_rect]).set_crs(epsg=3857),
            geometry_id=np.array(list(range(3)), dtype=np.uint64),
            point=GeoSeries([point, point, point]).set_crs(epsg=3857)
        ))
        res = check_dw_point_y_depth(df, 40, 15)
        res = set(iter(res))
        self.assertEqual(res, set([RECT]))
    def test_rectangular_neighborhood(self):
        geometry = [ basic_rect(25, 45),
                     basic_rect(15, 35, (25, 0)),
                     basic_rect(40, 20, (40, 0)),
                     basic_rect(25, 45, (80, 0)) ]
        geometry = GeoSeries(geometry).set_crs(epsg=3857)
        geometry_union = geometry.unary_union
        assert geometry.area.sum() == geometry_union.area
        names = ["GOOD", "BAD", "SIDEWAYS", "GOOD2"]
        df = gpd.GeoDataFrame(dict(
            geometry=geometry,
            geometry_id=np.array(list(range(len(names))), dtype=np.uint64),
            point=GeoSeries([Point(5., 0.),
                             Point(28., 0.),
                             Point(45., 0.),
                             Point(81., 0.)]).set_crs(epsg=3857)
        ))
        res = check_dw_point_y_depth(df, 39, 19)
        res = set(iter(res))
        res = set(names[i] for i in res)
        self.assertEqual(res, set(["GOOD", "GOOD2"]))
        
class TestRectangularNeighborhood(unittest.TestCase):
    def test_basic(self):
        geometry = [ basic_rect(25, 45),
                     basic_rect(15, 35, (25, 0)),
                     basic_rect(40, 20, (40, 0)),
                     basic_rect(25, 45, (80, 0)) ]
        geometry = GeoSeries(geometry).set_crs(epsg=3857)
        geometry_union = geometry.unary_union
        assert geometry.area.sum() == geometry_union.area
        names = ["GOOD", "BAD", "SIDEWAYS", "GOOD2"]
        df = gpd.GeoDataFrame(dict(
            geometry=geometry,
            geometry_id=np.array(list(range(len(names))), dtype=np.uint64)
        ))
        frontage = basic_rect(1000, 1, (0, -1.5))
        res = dw_winners_array(df, frontage,
                               geometry_union,
                               GDistance(39), GDistance(19),
                               angles=4)
        res = set(iter(res))
        res = set(names[i] for i in res)
        self.assertEqual(res, set(["GOOD", "GOOD2", "SIDEWAYS"]))

class TestExact(unittest.TestCase):
    def names(self): return ["GOOD", "BAD"]
    def df(self):
        geometry = GeoSeries([ basic_rect(20, 40),
                               basic_rect(19.9, 39.9, (20., 0.)) ]).set_crs(epsg=3857)
        return gpd.GeoDataFrame(dict(
            geometry=geometry,
            geometry_id=np.array(list(range(len(self.names()))), dtype=np.uint64)
        ))
    def frontage(self): return basic_rect(1000, 1, (0, -1))
    def test_exact_rectangle(self):
        df = self.df()
        res = dw_winners_array(df, self.frontage(), df["geometry"].unary_union,
                               GDistance(40), GDistance(20), angles=100)
        names = self.names()
        res = set(iter(res))
        res = set(names[i] for i in res)
        self.assertEqual(res, set(["GOOD"]))
    def test_exact_rectangle_rotated(self):
        ANGLE = .38 * math.tau
        df = self.df()
        new_geometry = df.geometry.rotate(ANGLE, origin=(0, 0), use_radians=True)
        del df["geometry"]
        df["geometry"] = new_geometry
        frontage = shapely.affinity.rotate(self.frontage(), ANGLE, origin=(0, 0), use_radians=True)
        print("ROTATED FRONTAGE", frontage)
        print("ROTATED GEOMETRY", df["geometry"])
        res = dw_winners_array(df, frontage, df["geometry"].unary_union,
                               GDistance(40), GDistance(20), angles=100)
        names = self.names()
        res = set(iter(res))
        res = set(names[i] for i in res)
        self.assertEqual(res, set(["GOOD"]))

class TestCache(unittest.TestCase):
    def clean_cache(self):
        p = "dw_TEST_cachedir"
        if os.path.exists(p): rmtree(p)
        os.mkdir(p)
        return DWCache(p)
    def test_empty(self):
        c = self.clean_cache()
        w, l = c.retrieve_results(20, 20)
        self.assertFalse(w)
        self.assertFalse(l)
    def test_basic(self):
        c = self.clean_cache()
        winners_in = ["A", "B", "C"]
        losers_in = ["D", "E", "F"]
        c.store_winners(20, 20, winners_in)
        c.store_losers(20, 20, losers_in)
        w, l = c.retrieve_results(20, 20)
        self.assertEqual(set(w), set(winners_in))
        self.assertEqual(set(l), set(losers_in))
        w, l = c.retrieve_results(30, 30)
        self.assertEqual(set(w), set())
        self.assertEqual(set(l), set(losers_in))
        w, l = c.retrieve_results(10, 10)
        self.assertEqual(set(w), set(winners_in))
        self.assertEqual(set(l), set())
    def test_basic_redundant(self):
        c = self.clean_cache()
        winners_in = ["A", "B", "C"]
        losers_in = ["D", "E", "F"]
        c.store_winners(20, 20, winners_in)
        c.store_losers(20, 20, losers_in)
        c.store_losers(10, 10, losers_in)
        w, l = c.retrieve_results(20, 20)
        self.assertEqual(set(w), set(winners_in))
        self.assertEqual(set(l), set(losers_in))
        w, l = c.retrieve_results(30, 30)
        self.assertEqual(set(w), set())
        self.assertEqual(set(l), set(losers_in))
        w, l = c.retrieve_results(10, 10)
        self.assertEqual(set(w), set(winners_in))
        self.assertEqual(set(l), set(losers_in))

class TestCacheFile(unittest.TestCase):
    def dead_cache(self): return DWCache("/tmp/example/")
    def clean_cache(self): return self.dead_cache()
    def test_constructor(self):
        c = self.clean_cache()
        DWCacheFile(c, "20_20_yes_ft.dwcache")
        DWCacheFile(c, "20_20_no_ft.dwcache")
    def test_exact_yes(self):
        c = self.clean_cache()
        entry = DWCacheFile(c, "20_20_yes_ft.dwcache")
        self.assertEqual(entry.implies_about_cand(20, 20), dw_cache.IMPLIES_SUCCESS)
    def test_exact_no(self):
        c = self.clean_cache()
        entry = DWCacheFile(c, "20_20_no_ft.dwcache")
        self.assertEqual(entry.implies_about_cand(20, 20), dw_cache.IMPLIES_FAILURE)
    def test_implied_yes(self):
        c = self.clean_cache()
        entry = DWCacheFile(c, "20_20_yes_ft.dwcache")
        self.assertEqual(entry.implies_about_cand(10, 10), dw_cache.IMPLIES_SUCCESS)
    def test_not_implied_yes(self):
        c = self.clean_cache()
        entry = DWCacheFile(c, "20_20_yes_ft.dwcache")
        self.assertIsNone(entry.implies_about_cand(30, 30))
    def test_implied_no(self):
        c = self.clean_cache()
        entry = DWCacheFile(c, "20_20_no_ft.dwcache")
        self.assertEqual(entry.implies_about_cand(30, 30), dw_cache.IMPLIES_FAILURE)
    def test_not_implied_no(self):
        c = self.clean_cache()
        entry = DWCacheFile(c, "20_20_no_ft.dwcache")
        self.assertIsNone(entry.implies_about_cand(10, 10))
    def test_40_20_no_exact(self):
        c = self.clean_cache()
        entry = DWCacheFile(c, "40_20_no_ft.dwcache")
        self.assertEqual(entry.implies_about_cand(40, 20), dw_cache.IMPLIES_FAILURE)

if __name__ == '__main__': unittest.main()
