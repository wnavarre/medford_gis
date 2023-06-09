import math
import geopandas

def rotate_xy_fast(x, y, rads, origin):
    origin_x, origin_y = origin
    sine = math.sin(rads)
    cosine = math.cos(rads)
    x = x - origin_x
    y = y - origin_y
    x_new = (x * cosine - y * sine)
    y_new = (x * sine + y * cosine)
    x_new += origin_x
    y_new += origin_y
    return x_new, y_new

def rotate_points_fast(points, rads, origin):
    x, y = rotate_xy_fast(points.x.to_numpy(), points.y.to_numpy(), rads, origin)
    return geopandas.GeoSeries(geopandas.points_from_xy(x, y, crs=points.crs))

def fast_translate(points, dx, dy):
    x = points.x.to_numpy() + dx
    y = points.y.to_numpy() + dy
    return geopandas.GeoSeries(geopandas.points_from_xy(x, y, crs=points.crs))
