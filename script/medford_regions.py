import geopandas
from shapely import LineString

INPUT_CRS="26986"
OUTPUT_CRS=3857

class Region:
    def __init__(self, pretty_name, line, key_loc="upper left"):
        self._line_series = geopandas.GeoSeries([line], crs=INPUT_CRS).to_crs(crs=OUTPUT_CRS)
        self.key_loc = key_loc
    def rect(self): return self._line_series.envelope[0]
    def bounds(self): return self._line_series.total_bounds
    def ratio(self):
        xmin, ymin, xmax, ymax = self.bounds()
        height = abs(ymax - ymin)
        width  = abs(xmax - xmin)
        return width / height

class RegionSet:
    def __init__(self, regions_dict, code, pretty_name):
        self._regions_dict = regions_dict
        for k, v in regions_dict.items(): setattr(self, k, v)
    def items(self): return self._regions_dict.items()

class FULL_CITY:
    FULL       = Region("Medford, MA", LineString([(228672, 904939), (235432, 911573)]))

GR = RegionSet(dict(
    HILLSIDE   = Region("Hillside", LineString([(230426, 907575), (231676, 906494)])),
    WEST       = Region("West Medford", LineString([(229455, 908695), (230575, 907277)]), key_loc="upper left"),
    SOUTH      = Region("South Medford", LineString([(231737, 907433), (233154, 905117)])),
    EAST       = Region("East Medford", LineString([(232175, 908589), (233720, 907614)])),
    WELLINGTON = Region("Wellington", LineString([(233455, 908416), (234853, 906216)])),
), "GR", "General Residential Zoning District")
