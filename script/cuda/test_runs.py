import numpy as np
import unittest
from unittest import TestCase
from runs_bindings import runs_right, depth_type, depth_max, runs_left, runs_both_sides

class RightJustDepth(TestCase):
    def test_zeros(self):
        begins = np.zeros(6, dtype=depth_type)
        depths = np.array([ 1, 3, 4, 1, 5, 4 ], dtype=depth_type)
        out = runs_right(begins, depths, 6)
        self.assertEqual(list(out), [ 0 ] * 6)
    def test_one(self):
        begins = np.zeros(6, dtype=depth_type)
        depths = np.array([ 1, 3, 4, 1, 5, 4 ], dtype=depth_type)
        out = runs_right(begins, depths, 5)
        self.assertEqual(list(out), [ 0, 0, 0, 0, 1, 0])
    def test_simple_run(self):
        begins = np.zeros(7, dtype=depth_type)
        depths = np.array([ 1, 3, 4, 1, 5, 4, 5 ], dtype=depth_type)
        out = runs_right(begins, depths, 3)
        self.assertEqual(list(out), [ 0, 2, 1, 0, 3, 2, 1])

class LeftJustDepth(TestCase):
    def test_zeros(self):
        begins = np.zeros(6, dtype=depth_type)
        depths = np.array([ 1, 3, 4, 1, 5, 4 ], dtype=depth_type)
        out = runs_left(begins, depths, 6)
        self.assertEqual(list(out), [ 0 ] * 6)
    def test_one(self):
        begins = np.zeros(6, dtype=depth_type)
        depths = np.array([ 1, 3, 4, 1, 5, 4 ], dtype=depth_type)
        out = runs_left(begins, depths, 5)
        self.assertEqual(list(out), [ 0, 0, 0, 0, 0, 0])
    def test_simple_run(self):
        begins = np.zeros(7, dtype=depth_type)
        depths = np.array([ 1, 3, 4, 1, 5, 4, 5 ], dtype=depth_type)
        out = runs_left(begins, depths, 3)
        self.assertEqual(list(out), [ 0, 0, 1, 0, 0, 1, 2])

class RightJustStart(TestCase):
    def test_increasing(self):
        begins = np.array([10, 20, 30, 40, 50, 60], dtype=depth_type)
        depths = np.array([depth_max] * 6,    dtype=depth_type)
        out = runs_right(begins, depths, 3)
        self.assertEqual(list(out), [ 1 ] * 6)
    def test_decreasing(self):
        begins = np.array([60, 50, 40, 30, 20, 10], dtype=depth_type)
        depths = np.array([depth_max] * 6,    dtype=depth_type)
        out = runs_right(begins, depths, 3)
        self.assertEqual(list(out), [ 6, 5, 4, 3, 2, 1 ])

class JustDepth(TestCase):
    def test_zeros(self):
        begins = np.zeros(6, dtype=depth_type)
        depths = np.array([ 1, 3, 4, 1, 5, 4 ], dtype=depth_type)
        out = runs_both_sides(begins, depths, 6)
        self.assertEqual(list(out), [ 0 ] * 6)
    def test_one(self):
        begins = np.zeros(6, dtype=depth_type)
        depths = np.array([ 1, 3, 4, 1, 5, 4 ], dtype=depth_type)
        out = runs_both_sides(begins, depths, 5)
        self.assertEqual(list(out), [ 0, 0, 0, 0, 1, 0])
    def test_simple_run(self):
        begins = np.zeros(7, dtype=depth_type)
        depths = np.array([ 1, 3, 4, 1, 5, 4, 5 ], dtype=depth_type)
        out = runs_both_sides(begins, depths, 3)
        self.assertEqual(list(out), [ 0, 2, 2, 0, 3, 3, 3])

class OverflowConcerns(TestCase):
    def test_one_big_start(self):
        begins = np.array([         255         ] * 7, dtype=depth_type)
        depths = np.array([ 1, 3, 4, 1, 5, 4, 5 ], dtype=depth_type)
        out = runs_both_sides(begins, depths, 3)
        self.assertEqual(list(out), [ 0, 2, 2, 0, 3, 3, 3])

if __name__ == '__main__': unittest.main()
