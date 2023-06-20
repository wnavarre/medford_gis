import geopandas
from shapely import LineString

INPUT_CRS="26986"
OUTPUT_CRS=3857

class Region:
    def __init__(self, line, key_loc="upper left"):
        self._line_series = geopandas.GeoSeries([line], crs=INPUT_CRS).to_crs(crs=OUTPUT_CRS)
        self.key_loc = key_loc
    def rect(self): return self._line_series.envelope[0]
    def bounds(self): return self._line_series.total_bounds
    def ratio(self):
        xmin, ymin, xmax, ymax = self.bounds()
        height = abs(ymax - ymin)
        width  = abs(xmax - xmin)
        return width / height

class FULL_CITY:
    FULL       = Region(LineString([(228672, 904939), (235432, 911573)]))
class GR:
    HILLSIDE   = Region(LineString([(230426, 907575), (231676, 906494)]))
    WEST       = Region(LineString([(229455, 908695), (230575, 907277)]), key_loc="upper left")
    SOUTH      = Region(LineString([(231737, 907433), (233154, 905117)]))
    EAST       = Region(LineString([(232175, 908589), (233720, 907614)]))
    WELLINGTON = Region(LineString([(233455, 908416), (234853, 906216)]))
    _TABLE = [
        ("Hillside", HILLSIDE.rect()),
        ("West Medford", WEST.rect()),
        ("South Medford", SOUTH.rect()),
        ("East Medford", EAST.rect()),
        ("Wellington", WELLINGTON.rect()),
    ]
    FRAME_DICT = next(
        dict(geometry=geopandas.GeoSeries(geo, crs=OUTPUT_CRS),
             name=nm) for (nm, geo) in (zip(*_TABLE),)
    )
    assert("geometry" in FRAME_DICT)
    FRAME = geopandas.GeoDataFrame(FRAME_DICT, crs=OUTPUT_CRS)
