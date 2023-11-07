#include <stddef.h>
#include <stdint.h>

struct Range;

typedef uint8_t DEPTH_TYPE;

enum SetFlags {
    SetMiddle = 0,
    SetBegin  = 1,
    SetEnd    = 2,
    SetBoth   = 3
};

struct Range {
    uint8_t    is_begin_run;
    DEPTH_TYPE begin_depth_y;
    DEPTH_TYPE depth;
};
