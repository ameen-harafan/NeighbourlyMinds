import unittest

from contrast_calculator import (
    badge_for_ratio,
    contrast_ratio,
    evaluate_pair,
    normalize_hex,
    relative_luminance,
)


class TestContrastCalculator(unittest.TestCase):

    def test_black_white_is_21_to_1(self):
        self.assertAlmostEqual(contrast_ratio("#FFFFFF", "#000000"), 21.0, places=10)

    def test_identical_colours_are_1_to_1(self):
        self.assertAlmostEqual(contrast_ratio("#FFFFFF", "#FFFFFF"), 1.0, places=10)

    def test_order_does_not_change_ratio(self):
        a = contrast_ratio("#FFFFFF", "#505050")
        b = contrast_ratio("#505050", "#FFFFFF")
        self.assertAlmostEqual(a, b, places=12)

    def test_boundary_fail_example(self):
        # Against white, #959595 is just below 3:1.
        ratio = contrast_ratio("#FFFFFF", "#959595")
        self.assertLess(ratio, 3.0)
        self.assertEqual(badge_for_ratio(ratio), "Low contrast")

    def test_boundary_pass_example(self):
        # Against white, #949494 is just above 3:1.
        ratio = contrast_ratio("#FFFFFF", "#949494")
        self.assertGreater(ratio, 3.0)
        self.assertEqual(badge_for_ratio(ratio), "Improved contrast")

    def test_badge_exact_boundary(self):
        self.assertEqual(badge_for_ratio(2.99), "Low contrast")
        self.assertEqual(badge_for_ratio(3.00), "Improved contrast")
        self.assertEqual(badge_for_ratio(3.01), "Improved contrast")

    def test_hex_without_hash_is_accepted(self):
        self.assertEqual(normalize_hex("ffffff"), "#FFFFFF")

    def test_invalid_hex_raises(self):
        with self.assertRaises(ValueError):
            normalize_hex("#FFFF")

    def test_result_contains_expected_fields(self):
        result = evaluate_pair("#F5F5F5", "#505050")
        self.assertGreaterEqual(result.contrast_ratio, 1.0)
        self.assertIn(result.badge, {"Low contrast", "Improved contrast"})

    def test_relative_luminance_limits(self):
        self.assertAlmostEqual(relative_luminance("#000000"), 0.0, places=12)
        self.assertAlmostEqual(relative_luminance("#FFFFFF"), 1.0, places=12)


if __name__ == "__main__":
    unittest.main()
