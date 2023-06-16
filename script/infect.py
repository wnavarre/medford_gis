from numba import jit

@jit("void(u8[:], b1[:])", nopython=True)
def infect_impl(vals, bools):
    n = len(vals)
    for idx in range(n - 1):
        bools[idx] = bools[idx] or (bools[idx - 1] and (vals[idx] == vals[idx - 1]))
    for idx in range(n - 1, 0, -1):
        bools[idx - 1] = bools[idx - 1] or (bools[idx] and (vals[idx] == vals[idx - 1]))

def infect(vals, bools):
    assert len(vals) == len(bools), ("len(vals) = {}; len(bools) = {};".format(len(vals), len(bools)))
    try:
        vals = vals.to_numpy()
    except:
        pass
    try:
        bools = bools.to_numpy()
    except:
        pass
    return infect_impl(vals, bools)
