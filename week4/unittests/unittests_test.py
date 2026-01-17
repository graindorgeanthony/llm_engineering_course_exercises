import unittest
import sys
import os

# Ensure the parent directory is in sys.path to allow importing the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import test

class TestMathOperations(unittest.TestCase):

    def test_add_positive_integers(self):
        self.assertEqual(test.add(3, 7), 10)

    def test_add_negative_integers(self):
        self.assertEqual(test.add(-1, -1), -2)

    def test_add_mixed_integers(self):
        self.assertEqual(test.add(-5, 5), 0)

    def test_add_floats(self):
        self.assertAlmostEqual(test.add(1.1, 2.2), 3.3, places=7)

    def test_multiply_positive_integers(self):
        self.assertEqual(test.multiply(3, 7), 21)

    def test_multiply_negative_integers(self):
        self.assertEqual(test.multiply(-2, -5), 10)

    def test_multiply_mixed_integers(self):
        self.assertEqual(test.multiply(-4, 5), -20)

    def test_multiply_by_zero(self):
        self.assertEqual(test.multiply(100, 0), 0)

    def test_multiply_floats(self):
        self.assertAlmostEqual(test.multiply(2.5, 4.0), 10.0)

    def test_add_strings(self):
        # Python allows string addition as concatenation
        self.assertEqual(test.add("hello", " world"), "hello world")

    def test_multiply_string_int(self):
        # Python allows string multiplication (repetition)
        self.assertEqual(test.multiply("a", 3), "aaa")

if __name__ == '__main__':
    unittest.main()
