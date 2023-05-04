import geopandas
import load_data
import zoning

plot_table = load_data.gdf
zoning_table = geopandas.read_file("../medford_zoning/zones.shp").to_crs("26986")

zoning_names = zoning.find_zones(
    plot_table.geometry,
    zoning_table["zo_abbr"],
    zoning_table.geometry)

zoning_names.mask(plot_table[] != "FEE", other="NOFEE", inplace=true)

plot_table["ZONE"] = zoning_names


if __name__ == "__main__": plot_table.to_file("augmented/tax_plots.shp")
