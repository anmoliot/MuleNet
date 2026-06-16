import unittest
from ml_models import calibrate_score

class TestCalibration(unittest.TestCase):

    def test_calibrate_baseline(self):
        # A low raw composite score should map to a low calibrated score
        score = calibrate_score(10.0)
        self.assertLess(score, 20.0)
        self.assertGreaterEqual(score, 0.0)

    def test_calibrate_midpoint(self):
        # Score around 45 (midpoint) should be around 50%
        score = calibrate_score(45.0)
        self.assertTrue(45.0 <= score <= 55.0)

    def test_calibrate_high(self):
        # A high raw composite score should map to a high calibrated score
        score = calibrate_score(90.0)
        self.assertGreater(score, 85.0)
        self.assertLessEqual(score, 100.0)

    def test_calibrate_extreme(self):
        # Extreme high raw score should cap at 100
        score = calibrate_score(500.0)
        self.assertEqual(score, 100.0)
