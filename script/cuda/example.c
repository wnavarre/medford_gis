#include <stddef.h>
#include <stdint.h>

typedef uint8_t DEPTH_TYPE;

int runs_right(DEPTH_TYPE const * begin_depths,
               DEPTH_TYPE const * depths,
               DEPTH_TYPE         required_depth,
               uint64_t         * output,
               uint64_t           count) {
    size_t i;
    for (i = 0; i < count; ++i) {
        output[i] = i;
    }
    return 0;
}
