#include <cuda.h>
#include "runs.h"
#include <iostream>

extern "C" {

namespace {

static constexpr uint8_t StepNone  = 0;
static constexpr uint8_t StepRight = 1;
static constexpr uint8_t StepLeft  = 2;
static constexpr uint8_t StepSubtract = 4;

#define BLOCK_SIZE 256

__global__ void kernal_set_size_t(size_t * out,
                                  size_t   value,
                                  size_t   count) {
    const size_t idx = threadIdx.x + blockDim.x * blockIdx.x;
    if (idx < count) { out[idx] = value; }
}

__device__ __inline__ int qualifies_as_part_of_run(Range range,
                                                   DEPTH_TYPE required_frontage_height,
                                                   DEPTH_TYPE required_depth) {
    return(range.begin_depth_y <= required_frontage_height) &&
        (range.depth >= required_frontage_height - range.begin_depth_y) &&
        (required_depth <= range.depth - (required_frontage_height - range.begin_depth_y));
}

// Into `dest`, we will write (out_val - run_length)
__global__ void subtract_max_run_right(DEPTH_TYPE depth_required,
                                       Range const * data,
                                       size_t      * dest,
                                       size_t        count,
                                       size_t        max_out_val) {
    size_t out_val = max_out_val;
    size_t cur_idx = threadIdx.x + blockDim.x * blockIdx.x;
    if (cur_idx >= count) return;
    Range range = data[cur_idx];
    DEPTH_TYPE const frontage_height = range.begin_depth_y;
    uint8_t          satisfied = 1;
    if (range.depth < depth_required) { goto finish; }
    ++cur_idx; --out_val;
    for ( ; cur_idx < count; ++cur_idx) {
        range = data[cur_idx];
        if ((range.is_begin_run && !satisfied) || (!out_val)) {
            goto finish;
        }
        satisfied = satisfied && (!range.is_begin_run);
        if ((!satisfied) && qualifies_as_part_of_run(range, frontage_height, depth_required)) {
            satisfied = 1;
            --out_val;
        }
    }
 finish:
    dest[threadIdx.x + blockDim.x * blockIdx.x] = out_val;
}

__global__ void subtract_max_run_left_in_place(DEPTH_TYPE depth_required,
                                               Range const * data,
                                               size_t      * dest,
                                               size_t        count) {
    // We don't count the initial one;
    // Similar to the RIGHT version, we subtract, but this time we
    // do that from an initial value.
    size_t cur_idx = threadIdx.x + blockDim.x * blockIdx.x;
    if (cur_idx >= count) { return; }
    auto range = data[cur_idx];
    const auto depth_start = range.begin_depth_y;
    if (range.depth < depth_required) {
        return; // don't even need to write anything.
    }
    size_t out_val = dest[cur_idx];
    bool is_last = true;
    bool is_satisfied = true;
    while (cur_idx && out_val) {
        --cur_idx;
        range = data[cur_idx];
        if (is_last && !is_satisfied) { break; }
        is_satisfied = is_satisfied && !is_last;
        if ((!is_satisfied) && qualifies_as_part_of_run(range, depth_start, depth_required)) {
            is_satisfied = 1;
            --out_val;
        }
        is_last = range.is_begin_run;
    }
    dest[threadIdx.x + blockDim.x * blockIdx.x] = out_val;
}

__global__ void subtract_from(size_t amount_to_subtract_from,
                              size_t * data,
                              size_t   count) {
    size_t idx = threadIdx.x + blockDim.x * blockIdx.x;
    if (idx < count) {
        data += idx;
        *data = amount_to_subtract_from - *data;
    }
}

size_t ceiling_division(size_t dividend, size_t divisor) {
    return (dividend + divisor - 1) / divisor;
}

int help_runs(DEPTH_TYPE const * begin_depths,
              DEPTH_TYPE const * depths,
              DEPTH_TYPE         required_depth,
              size_t           * output,
              size_t             count,
              uint8_t            steps_todo) {
    int result = 100;
    int cudares = 0;
    Range  * ranges  = NULL;
    Range  * dranges = NULL;
    size_t * dout    = NULL;
    ranges = (Range*) calloc(count, sizeof(Range));
    if (auto local_res = cudaMalloc((void**)(&dranges), sizeof(Range) * count)) {
        result=101; goto clean_up;
    }
    if (cudaMalloc((void**)(&dout),   sizeof(size_t) * count)) { result=102; goto clean_up; }
    if (!ranges)                                               { result=103; goto clean_up; }
    for (size_t i = 0; i < count; ++i) {
        ranges[i].is_begin_run  = 1;
        ranges[i].begin_depth_y = begin_depths[i];
        ranges[i].depth         = depths[i];
    }
    if (cudaMemcpy(dranges, ranges, sizeof(Range) * count, cudaMemcpyHostToDevice)) {
        result = 2; goto clean_up;
    }
    if (steps_todo & StepRight) {
        subtract_max_run_right<<<ceiling_division(count, BLOCK_SIZE), BLOCK_SIZE>>>
            (required_depth,
             dranges,
             dout,
             count,
             1024);
    } else {
        kernal_set_size_t<<<ceiling_division(count, BLOCK_SIZE), BLOCK_SIZE>>>
            (dout,
             1024,
             count);
    }
    if (steps_todo & StepLeft) {
        subtract_max_run_left_in_place<<<ceiling_division(count, BLOCK_SIZE), BLOCK_SIZE>>>
            (required_depth,
             dranges,
             dout,
             count);
    }
    if (steps_todo & StepSubtract) {
        subtract_from<<<ceiling_division(count, BLOCK_SIZE), BLOCK_SIZE>>>(1024, dout, count);
    }
    if (cudaMemcpy(output, dout, sizeof(size_t) * count, cudaMemcpyDeviceToHost)) {
        result = 3; goto clean_up;
    }
    result = 0;
 clean_up:
    free(ranges);
    cudaFree(dranges);
    cudaFree(dout);
    return result;
}
} // anonymous namespace

int runs_right(DEPTH_TYPE const * begin_depths,
               DEPTH_TYPE const * depths,
               DEPTH_TYPE         required_depth,
               size_t           * output,
               size_t             count) {
    return help_runs(begin_depths,
                     depths,
                     required_depth,
                     output,
                     count,
                     StepRight | StepSubtract);
}

int runs_left(DEPTH_TYPE const * begin_depths,
              DEPTH_TYPE const * depths,
              DEPTH_TYPE         required_depth,
              size_t           * output,
              size_t             count) {
    return help_runs(begin_depths,
                     depths,
                     required_depth,
                     output,
                     count,
                     StepLeft | StepSubtract);
}

int runs_both_sides(DEPTH_TYPE const * begin_depths,
                    DEPTH_TYPE const * depths,
                    DEPTH_TYPE         required_depth,
                    size_t           * output,
                    size_t             count) {
    return help_runs(begin_depths,
                     depths,
                     required_depth,
                     output,
                     count,
                     StepLeft | StepRight | StepSubtract);
}
} // extern "C"

