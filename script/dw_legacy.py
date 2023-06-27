from dw import *

class GDistance(DistanceBase):
    def __init__(self, val): self._val = val
    def feet(self): return self._val
    def gis(self): return self._val

def check_dw_point_y_depth(df, depth, width):
    depth = GDistance(depth)
    width = GDistance(width)
    assert df.crs is not None
    geometry_df = (df.groupby("geometry_id", as_index=False)
                   .first()[["geometry", "geometry_id"]]
                   .set_crs(crs=df.crs))
    points_df = df[["point", "geometry_id"]]
    points_df = points_df.rename({
        "geometry_id": "lot_id"
    }, axis=1).set_geometry("point").set_crs(crs=df.crs)
    assert points_df.crs is not None
    assert geometry_df.crs is not None
    assert "geometry_id" not in points_df
    assert "lot_id" in points_df
    table = DWCandidatesTable(geometry_df, depth, width).set_frontage_points(points_df)
    return check_working_table(DWWorkingTable(table, 0))
