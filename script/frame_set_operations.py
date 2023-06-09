from basic_frame_operations import *
import numpy as np
import pandas

def mask_for_value_set(data, column_name, values_to_mark, mark_value_bool):
    values_to_mark = np.unique(values_to_mark)
    left = pandas.DataFrame(dict(key=data[column_name]))
    right = pandas.DataFrame(dict(
        key  = values_to_mark,
        ones = np.ones((len(values_to_mark),), dtype=int)
    ))
    data2 = left.merge(right, on="key", how="left")
    data2 = data2.reset_index(drop=True)
    assert(len(data2) == len(left))
    assert(len(data2) == len(data))
    if mark_value_bool:
        return (data2["ones"] == 1)
    else:
        return (data2["ones"] != 1)

def remove_small_groups(data, group_column_name, minimum_size):
    is_ok_values = data.groupby(group_column_name).size() >= minimum_size
    is_ok_rows = is_ok_values.loc[data[group_column_name]]
    is_ok_rows.reset_index(inplace=True, drop=True)
    return clean_dataframe(data.loc[is_ok_rows])

def action_on_matching(data, column_name, values_to_do, is_keep):
    mask = mask_for_value_set(data, column_name, values_to_do, is_keep)
    return clean_dataframe(data[mask])

def keep_matching(data, column_name, values_to_keep):
    return action_on_matching(data, column_name, values_to_keep, True)

def discard_matching(data, column_name, values_to_discard):
    return action_on_matching(data, column_name, values_to_discard, False)

def convex_hull(h, *t):
    for e in t: h = h.union(e)
    return h.convex_hull
def df_convex_hull(df, h, *t, set_crs=None):
    if set_crs is None:
        return convex_hull(df[h], *[df[e] for e in t])
    else:
        return convex_hull(set_crs(df[h]), *[set_crs(df[e]) for e in t])

def keep_columns(df, *keep_columns):
    keep_columns = set(keep_columns)
    del_columns = []
    for e in df.columns:
        if e not in keep_columns: del_columns.append(e)
    return df.drop_columns(del_columns)
