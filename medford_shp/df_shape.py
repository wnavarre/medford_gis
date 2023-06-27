import numpy as np

def fill_missing_nulls(df, desired_shape):
    for name in desired_shape.columns:
        series = desired_shape[name]
        if name in df.columns: continue
        df[name] = type(series)(np.empty((len(df),), dtype=series.dtype))
    return df
