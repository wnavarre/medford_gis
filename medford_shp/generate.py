import geopandas
import numpy as np
import best_overlap

def keep(d, to_keep):
    to_keep = set(to_keep)
    for k in to_keep:
        if k not in d:
            raise ValueError("Key not there to begin with: " + k)
    for k in d:
        if k not in to_keep: del(d[k])
    for k in to_keep:
        assert(k in d)

base = geopandas.read_file("../massgis_shp/M176TaxPar_CY21_FY20.shp")

# Add in the zoning info.
zoning_table = geopandas.read_file("../medford_zoning/zones.shp")
assert len(zoning_table) == len(set(zoning_table.zo_abbr))

cands_and_labels = zip(zoning_table.geometry, zoning_table.zo_abbr)

base["ZONE"] = best_overlap.find_best_overlaps(base.geometry,
                                               cands_and_labels,
                                               cand_crs=zoning_table.geometry.crs)

assert(len(base["ZONE"].unique()) > 1)

if __name__ == "__main__":
    base.to_parquet("./medford.pqt")
    base.to_file("./medford.shp")
