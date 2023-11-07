import ctypes
import numpy as np

depth_type = np.uint8
depth_max = 255

lib = ctypes.CDLL('./librangeruns.so')
lib.runs_right.argtypes = [
    np.ctypeslib.ndpointer(dtype=depth_type, ndim=1, flags='C_CONTIGUOUS'),
    np.ctypeslib.ndpointer(dtype=depth_type, ndim=1, flags='C_CONTIGUOUS'),
    ctypes.c_uint8,
    np.ctypeslib.ndpointer(dtype=np.uint64, ndim=1, flags=('C_CONTIGUOUS', 'W')),
    ctypes.c_uint64
]
lib.runs_left.argtypes = [
    np.ctypeslib.ndpointer(dtype=depth_type, ndim=1, flags='C_CONTIGUOUS'),
    np.ctypeslib.ndpointer(dtype=depth_type, ndim=1, flags='C_CONTIGUOUS'),
    ctypes.c_uint8,
    np.ctypeslib.ndpointer(dtype=np.uint64, ndim=1, flags=('C_CONTIGUOUS', 'W')),
    ctypes.c_uint64
]
lib.runs_both_sides.argtypes = [
    np.ctypeslib.ndpointer(dtype=depth_type, ndim=1, flags='C_CONTIGUOUS'),
    np.ctypeslib.ndpointer(dtype=depth_type, ndim=1, flags='C_CONTIGUOUS'),
    ctypes.c_uint8,
    np.ctypeslib.ndpointer(dtype=np.uint64, ndim=1, flags=('C_CONTIGUOUS', 'W')),
    ctypes.c_uint64
]

lib.runs_right.restype = ctypes.c_int
lib.runs_left.restype = ctypes.c_int
def runs_right(begin_depths, depths, required_depth):
    count = min(len(x) for x in [ begin_depths, depths ])
    output = np.zeros(count, dtype=np.uint64)
    res = lib.runs_right(begin_depths, depths, required_depth, output, count)
    if res:
        raise ValueError("Received bad result from C: {}".format(res))
    return output

def runs_left(begin_depths, depths, required_depth):
    count = min(len(x) for x in [ begin_depths, depths ])
    output = np.zeros(count, dtype=np.uint64)
    res = lib.runs_left(begin_depths, depths, required_depth, output, count)
    if res:
        raise ValueError("Received bad result from C: {}".format(res))
    return output

def runs_both_sides(begin_depths, depths, required_depth):
    count = min(len(x) for x in [ begin_depths, depths ])
    output = np.zeros(count, dtype=np.uint64)
    res = lib.runs_both_sides(begin_depths, depths, required_depth, output, count)
    if res:
        raise ValueError("Received bad result from C: {}".format(res))
    return output

lib.runs_right.argtypes = [
    np.ctypeslib.ndpointer(dtype=depth_type, ndim=1, flags='C_CONTIGUOUS'),
    np.ctypeslib.ndpointer(dtype=depth_type, ndim=1, flags='C_CONTIGUOUS'),
    ctypes.c_uint8,
    np.ctypeslib.ndpointer(dtype=np.uint64, ndim=1, flags=('C_CONTIGUOUS', 'W')),
    ctypes.c_uint64
]

