import geopandas
import numpy as np

def keep(d, to_keep):
    to_keep = set(to_keep)
    for k in to_keep:
        if k not in d:
            raise ValueError("Key not there to begin with: " + k)
    for k in d:
        if k not in to_keep: del(d[k])
    for k in to_keep:
        assert(k in d)

lookup = geopandas.read_file("../massgis_shp/M176Assess_CY21_FY20.dbf")
lookup = lookup[np.logical_not(lookup.LOC_ID.isna().to_numpy())]
lookup = lookup[np.logical_not(lookup.ZONING.isna().to_numpy())]
lookup = lookup.groupby("LOC_ID").first()
lookup.reset_index(inplace=True)

base = geopandas.read_file("../massgis_shp/M176TaxPar_CY21_FY20.shp")

assert("LOC_ID" in lookup)

keep(lookup, {"LOC_ID", "ZONING"})

lookup.rename(columns={"ZONING": "ZONE"}, inplace=True)
assert("ZONE" in lookup)

# Add in the zoning info.
assert(len(lookup["ZONE"].unique()) > 1)
assert("ZONE" not in base)
base = base.merge(lookup, on="LOC_ID", how="left")
base.geometry
assert(len(base["ZONE"].unique()) > 1)

if __name__ == "__main__":
    base.to_parquet("./medford.pqt")
