import geopandas

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
base = geopandas.read_file("../massgis_shp/M176TaxPar_CY21_FY20.shp")

assert("LOC_ID" in lookup)
keep(lookup, {"LOC_ID", "ZONING"})

base["LOC_ID_ST"] = base["LOC_ID"].astype("|S20")
lookup["LOC_ID_ST"] = lookup["LOC_ID"].astype("|S20")
del(lookup["LOC_ID"])
res = lookup.rename(columns={"ZONING": "ZONE"}, inplace=True)
assert(res is None)
assert("LOC_ID" not in lookup)
assert("ZONE" in lookup)
assert("LOC_ID_ST" in lookup)

# Add in the zoning info.
assert(len(lookup["ZONE"].unique()) > 1)
assert("ZONE" not in base)
base = base.join(lookup.set_index("LOC_ID_ST"), on="LOC_ID_ST", rsuffix="__R")
assert(len(base["ZONE"].unique()) > 1)


del(base["LOC_ID_ST"])
#del(base["LOC_ID_ST__R"])

if __name__ == "__main__":
    base.to_file("./M176TaxPar_CY21_FY20.shp")
    base.to_file("../script/augmented/tax_plots.shp")
