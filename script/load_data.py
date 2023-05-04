import geopandas
path_to_data = "../medford_shape/M176TaxPar_CY21_FY20.shp"
gdf = geopandas.read_file(path_to_data)
tax_parcels = gdf["geometry"]
parcels = tax_parcels.explode(index_parts=True)

