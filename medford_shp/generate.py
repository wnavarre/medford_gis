import geopandas
from geopandas import GeoSeries, GeoDataFrame
import shapely
import numpy as np
import pandas
import best_overlap

from df_shape import *

def clean_dataframe(data): return data.reset_index(drop=True, inplace=False)

def keep(d, to_keep):
    to_keep = set(to_keep)
    for k in to_keep:
        if k not in d:
            raise ValueError("Key not there to begin with: " + k)
    for k in d:
        if k not in to_keep: del(d[k])
    for k in to_keep:
        assert(k in d)

base = geopandas.read_file("../massgis_shp/M176TaxPar_CY24_FY24.shp")

print("LENGTH: ", len(base))
base = base[base.is_valid].reset_index()
print("VALID LENGTH: ", len(base))

# Add in the zoning info.
zoning_table = geopandas.read_file("../medford_zoning/zones.shp")
assert len(zoning_table) == len(set(zoning_table.zo_abbr))

cands_and_labels = zip(zoning_table.geometry, zoning_table.zo_abbr)

base["ZONE"] = best_overlap.find_best_overlaps(base.geometry,
                                               cands_and_labels,
                                               cand_crs=zoning_table.geometry.crs)

assert(len(base["ZONE"].unique()) > 1)

other = geopandas.read_file("../massgis_shp/M176Assess_CY24_FY24.dbf")
for k in other:
    if k not in ("LOC_ID", "USE_CODE"): del other[k]
other = other.dropna(subset=['LOC_ID'])
other['LOC_ID'] = other.LOC_ID.astype(str)
other['USE_CODE_3'] = other.USE_CODE.str[0:3]
other['MIN_COUNT'] = sum([
    (other.USE_CODE_3 == "101"),
    (other.USE_CODE_3 == "102") * 2, # Pathetic, that just means condo...
    (other.USE_CODE_3 == "104") * 2,
    (other.USE_CODE_3 == "105") * 3,
    (other.USE_CODE_3.str[0:2] == "11") * 8 - (other.USE_CODE_3.str == "111") * 4
])

def equals_any(column, values):
    acc = (column == values[0])
    for value in values[1:]:
        acc = acc | (column == value)
    return acc

other['PUBLIC_USE'] = equals_any(
    other.USE_CODE_3,
    ["900", # US GOV
     "930", # Vacant, local
     "931", # Improved, local
     "933", # Vacant Education
     "934", # Improved Ed
     "935", # Improved public safety
     ]
)

base  =  base.dropna(subset=['LOC_ID'])
base['LOC_ID'] = base.LOC_ID.astype(str)


base = base.merge(other, on="LOC_ID", how='left')
print("--> BASE: ", base.keys())
del other

u_geometry = base.unary_union
u = geopandas.GeoDataFrame(
    geometry=geopandas.GeoSeries([ u_geometry ], crs=base.crs)
)
if 0:
    # The Broadway Corridor is sort of important because it has some multi-family
    # zones. In other cases we can probably just ignore partial lots, but
    # being a significant part of Medford's multi-family, we need to attempt
    # to make the appropriate adjustments to present a fair picture...
    broadway_corridor = (shapely.Point(232914.8, 905164.8)
                         .union(shapely.Point(232902.4, 905145.5))
                         .union(shapely.Point(231973.4, 905583.7))
                         .union(shapely.Point(231955.5, 905548.5))).convex_hull
    broadway_corridor_line = u_geometry.exterior.intersection(broadway_corridor)
    somerville = geopandas.read_file("../somerville_shp/M274TaxPar_CY23_FY24.shp")
    somerville = somerville[somerville.geometry.intersects(
        geopandas.GeoSeries(np.full(len(somerville), broadway_corridor), crs=somerville.crs)
    )]
    medford_border_plots = base[
        (base.POLY_TYPE != "ROW") &

        base.geometry.intersects((geopandas.GeoSeries(np.full(len(base), broadway_corridor), crs=somerville.crs))
    )]



    print("Dealing with border plots:")
    for e in medford_border_plots.LOC_ID:
        print(e)
    print()
    print()

    somerville_row = (somerville[somerville.POLY_TYPE == "ROW"].unary_union).intersection(broadway_corridor)
    somerville_plots = somerville[somerville.POLY_TYPE != "ROW"]

    somerville_plots = clean_dataframe(somerville_plots)
    medford_border_plots = clean_dataframe(medford_border_plots)

    # Try to merge plots!
    somerville_geo_to_medford_loc_id = []
    for somerville_plot in somerville_plots.geometry:
        splot_series = GeoSeries(np.full(len(medford_border_plots), somerville_plot.buffer(0.01)),
                                 crs=somerville.crs)
        mx = splot_series.intersection(medford_border_plots).area.idxmax()
        if np.isnan(mx):
            print("No winner")
            continue
        winner = medford_border_plots.LOC_ID[mx]
        somerville_geo_to_medford_loc_id.append((somerville_plot, winner))

    assert (len(somerville_geo_to_medford_loc_id) ==
            len(set(x[1] for x in somerville_geo_to_medford_loc_id)))

    lookup_splots, lookup_medford_loc_ids = zip(*somerville_geo_to_medford_loc_id)
    somerville_table_1 = GeoDataFrame(dict(
        somerville_lot=GeoSeries(lookup_splots, crs=somerville.crs),
        LOC_ID=lookup_medford_loc_ids
    ), geometry="somerville_lot")
    medford_table_1 = GeoDataFrame(dict(
        medford_lot=base.geometry,
        LOC_ID=base.LOC_ID
    ), geometry="medford_lot")
    border_table = somerville_table_1.merge(medford_table_1, how="inner", on="LOC_ID")
    border_table["line"] = GeoSeries(np.full(len(border_table), broadway_corridor_line),
                                     crs=base.crs)
    # For each, trim the line so that we are including only the part near both.
    EPSILON = 0.001
    border_table["line"] = (border_table.line
                            .intersection(border_table.medford_lot.buffer(EPSILON))
                            .intersection(border_table.somerville_lot.buffer(EPSILON)))
    # The idea is we buffer 'line' just a little to act as "glue".
    # This makes the lots intersect a tiny bit at the border, but I don't this this has
    # any practical problem.
    border_table["medford_lot"] = (border_table.line.buffer(EPSILON, cap_style=2)
                                   .union(border_table.medford_lot)
                                   .union(border_table.somerville_lot))
    del border_table["somerville_lot"]
    del border_table["line"]

    # Now bring that into base.
    base = base.merge(border_table, on="LOC_ID", how="left")
    base.geometry.where(pandas.isnull(base.medford_lot),
                        other=base.medford_lot,
                        inplace=True)
    del base["medford_lot"]

    # Add the somerville ROW
    somerville_row_df = fill_missing_nulls(geopandas.GeoDataFrame(dict(
        geometry=geopandas.GeoSeries([somerville_row], crs=base.crs),
        POLY_TYPE=pandas.Series(["ROW"])
    )), base)
    base = geopandas.GeoDataFrame(pandas.concat([base, somerville_row_df], ignore_index=True))

if __name__ == "__main__":
    base.to_parquet("./medford.pqt")
    base.to_file(   "./medford.shp")
    u.to_parquet("./medford_full_city.pqt")
    u.to_file(   "./medford_full_city.shp")
