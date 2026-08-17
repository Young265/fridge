import unittest

from app import should_auto_confirm_recognition
from pi_fridge_camera import Prediction, is_uploadable


class RecognitionPolicyTests(unittest.TestCase):
    def test_reliable_high_confidence_label_is_auto_confirmed(self):
        self.assertTrue(should_auto_confirm_recognition("tomato", 0.95))

    def test_low_confidence_label_requires_review(self):
        self.assertFalse(should_auto_confirm_recognition("tomato", 0.70))

    def test_lower_precision_label_is_still_recognized_but_requires_review(self):
        self.assertFalse(should_auto_confirm_recognition("cabbage", 0.99))

    def test_korean_alias_uses_same_review_policy(self):
        self.assertFalse(should_auto_confirm_recognition("양배추", 0.99))

    def test_default_camera_policy_does_not_limit_ingredient_classes(self):
        self.assertTrue(is_uploadable(Prediction("apple", 0.90, [])))
        self.assertTrue(is_uploadable(Prediction("lettuce", 0.90, [])))


if __name__ == "__main__":
    unittest.main()
