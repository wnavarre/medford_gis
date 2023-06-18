import numpy as np
from geopandas import GeoSeries

def find_best_overlaps(target_shapes, cands_and_labels, epsilon=0.0001, cand_crs=None):
    assert cand_crs is not None
    npshape = (len(target_shapes),)
    out   = np.empty(npshape, dtype=object)
    score = np.zeros(npshape, dtype=float)
    for cand, label in cands_and_labels:
        cand_series = GeoSeries(
            np.full(npshape, cand),
            crs=cand_crs
        )
        overlap_amt = cand_series.intersection(target_shapes).area
        winning = overlap_amt > score
        score = np.where(winning.to_numpy(), overlap_amt.to_numpy(), score)
        out[winning] = label
    return out
        
