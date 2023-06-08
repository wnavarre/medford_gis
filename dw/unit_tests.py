import unittest
import shapely
import pandas
import pandas as pd
from shapely import MultiPoint, Point
from check_dw_point_slope import *
import geopandas as gpd
from geopandas import GeoSeries, GeoDataFrame
import math
import numpy as np

def translate(geo, coords):
    return shapely.transform(geo, lambda x: x + coords)
    
def basic_rect(x, y, translation=(0., 0.)):
    out = MultiPoint([(0., 0.), (x, y)]).envelope
    return translate(out, translation)

def basic_line(x, y, translation=(0., 0.)):
    out = MultiPoint([(0., 0.), (x, y)]).convex_hull
    return translate(out, translation)

class TestCheckSliced(unittest.TestCase):
    def test_1(self):
        rect = basic_rect(75, 41)
        corner = basic_rect(100, 100, (10, 20))
        lot = shapely.difference(rect, corner)
        bottom = basic_line(BIG_DISTANCE * 2, 0, (-BIG_DISTANCE, 0))
        middle = translate(bottom, (0, 20))
        top = translate(bottom, (0, 40))
        lots = GeoSeries([lot] * 2)
        depth_line = basic_line(0, 40., (0., 4.))
        df = gpd.GeoDataFrame(dict(
            geometry=[Point(0., 0.)] * 2,
            geometry_id=["LOT"] * 2,
            point_id=[0] * 2,
            width_slice=lots,
            start_width=GeoSeries([bottom, middle]),
            stop_width=GeoSeries([middle, top]),
            depth_line=GeoSeries([depth_line] * 2)
        ))
        df = with_updated_width_slice(df)
        res, _ = check_sliced(df, 40, 20, 2)
        self.assertEqual(len(res), 0)

class TestDWPointSlope(unittest.TestCase):
    def test_notched_rectangle(self):
        rect = MultiPoint([(0., 0.), (15.05, 40.05)]).envelope
        notch = MultiPoint([(14.9, 30.), (100., 35.)]).envelope
        notched_rect = shapely.difference(rect, notch)
        point = Point(4., 0.)
        df = gpd.GeoDataFrame(dict(
            geometry=[notched_rect],
            geometry_id=["NOTCHED_RECT"],

            point=GeoSeries([point])
        ), geometry="geometry")
        res = check_dw_point_angle(df, 40, 15, math.pi / 2)
        res = set(iter(res))
        self.assertEqual(res, set())
    def test_straight_rectangle_variations(self):
        rect = MultiPoint([(0., 0.), (15.05, 40.05)]).envelope
        notch = MultiPoint([(14.9, 30.), (100., 30.1)]).envelope
        long_but_narrow_rect = MultiPoint([(0., 0.), (14.5, 250)])
        notched_rect = shapely.difference(rect, notch)
        point = Point(4., 0.)
        df = gpd.GeoDataFrame(dict(
            geometry=[rect, notched_rect, long_but_narrow_rect],
            geometry_id=["RECT", "NOTCHED_RECT", "LONG_BUT_NARROW"],
            point=GeoSeries([point, point, point])
        ))
        res = check_dw_point_angle(df, 40, 15, math.pi / 2)
        res = set(iter(res))
        self.assertEqual(res, set(["RECT"]))

class RectangularNeighborhood(unittest.TestCase):
    def test_basic(self):
        geometry = [ basic_rect(25, 45),
                     basic_rect(15, 35, (25, 0)),
                     basic_rect(40, 20, (40, 0)),
                     basic_rect(25, 45, (80, 0)) ]
        geometry = GeoSeries(geometry)
        geometry_union = geometry.unary_union
        assert geometry.area.sum() == geometry_union.area
        names = ["GOOD", "BAD", "SIDEWAYS", "GOOD2"]
        df = gpd.GeoDataFrame(dict(
            geometry=geometry,
            geometry_id=np.array(list(range(len(names))))
        ))
        frontage = basic_rect(1000, 1, (0, -1.5))
        res = dw_winners_array(df, frontage, geometry_union, 39, 19)
        res = set(iter(res))
        res = set(names[i] for i in res)
        self.assertEqual(res, set(["GOOD", "GOOD2"]))
if __name__ == '__main__': unittest.main()

