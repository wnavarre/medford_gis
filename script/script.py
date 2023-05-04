import geopandas
import trim_fifteen
import load_data
from trim_fifteen import *

parcels = load_data.parcels
envelope_trim = trim(parcels, 15)
assert(isinstance(envelope_trim.dtype, geopandas.array.GeometryDtype))
usable = trim_fifteen.trim_unusable_space(envelope_trim, 8)
usable_file = geopandas.GeoDataFrame(
    {
        'A_USABLE' : usable.area,
        'geometry' : usable
    },
    crs=load_data.gdf.crs
)
usable_file = usable_file.loc[usable_file.geometry.geom_type == "Polygon"]
usable_file.to_file("./out/usable.shp")


envelope_file = geopandas.GeoDataFrame(
    {
        'geometry': envelope_trim
    },
    crs=load_data.gdf.crs
)
envelope_file = envelope_file.loc[envelope_file.geometry.geom_type == "Polygon"]
envelope_file.to_file("./out/envelope.shp")
