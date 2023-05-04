import geopandas
path_to_data = "../ZoningAtlas/zoning_atlas.shp"
gdf = geopandas.read_file(path_to_data)
gdf = gdf[gdf["muni"] == "Medford"]
gdf.to_crs("26986").to_file("./zones.shp")
