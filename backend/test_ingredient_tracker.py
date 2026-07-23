import unittest

from ingredient_tracker import (
    IngredientCrossingTracker,
    TrackObservation,
    TrackingSettings,
)


def observation(y: int, label: str = "apple") -> TrackObservation:
    return TrackObservation(label, (40, y - 10, 60, y + 10), payload=y)


class IngredientCrossingTrackerTests(unittest.TestCase):
    def make_tracker(self, **overrides) -> IngredientCrossingTracker:
        values = {
            "inside_direction": "down",
            "outer_line_ratio": 0.35,
            "inner_line_ratio": 0.65,
            "stable_zone_frames": 2,
            "max_center_distance_ratio": 0.5,
            "max_missed_frames": 2,
        }
        values.update(overrides)
        return IngredientCrossingTracker(TrackingSettings(**values))

    def update(self, tracker, *items):
        events = []
        for item in items:
            observations = [] if item is None else [item]
            events.extend(tracker.update(observations, 100, 100))
        return events

    def test_emits_in_after_stable_full_crossing(self):
        tracker = self.make_tracker()

        events = self.update(
            tracker,
            observation(20),
            observation(22),
            observation(50),
            observation(70),
            observation(72),
        )

        self.assertEqual(1, len(events))
        self.assertEqual("in", events[0].direction)
        self.assertEqual("apple", events[0].label)
        self.assertEqual(72, events[0].observation.payload)

    def test_emits_out_after_stable_full_crossing(self):
        tracker = self.make_tracker()

        events = self.update(
            tracker,
            observation(80),
            observation(78),
            observation(50),
            observation(30),
            observation(28),
        )

        self.assertEqual(["out"], [event.direction for event in events])

    def test_jitter_near_one_line_does_not_emit(self):
        tracker = self.make_tracker()

        events = self.update(
            tracker,
            observation(30),
            observation(32),
            observation(36),
            observation(34),
            observation(37),
            observation(33),
        )

        self.assertEqual([], events)

    def test_short_occlusion_keeps_track(self):
        tracker = self.make_tracker()

        events = self.update(
            tracker,
            observation(20),
            observation(22),
            None,
            observation(70),
            observation(72),
        )

        self.assertEqual(["in"], [event.direction for event in events])

    def test_expired_track_does_not_create_false_crossing(self):
        tracker = self.make_tracker(max_missed_frames=1)

        events = self.update(
            tracker,
            observation(20),
            observation(22),
            None,
            None,
            observation(70),
            observation(72),
        )

        self.assertEqual([], events)

    def test_reversed_camera_direction(self):
        tracker = self.make_tracker(inside_direction="up")

        events = self.update(
            tracker,
            observation(80),
            observation(78),
            observation(50),
            observation(30),
            observation(28),
        )

        self.assertEqual(["in"], [event.direction for event in events])

    def test_tracks_same_label_objects_independently(self):
        tracker = self.make_tracker(stable_zone_frames=1)
        tracker.update([observation(20), TrackObservation("apple", (70, 15, 90, 25))], 100, 100)

        events = tracker.update(
            [observation(70), TrackObservation("apple", (70, 65, 90, 75))],
            100,
            100,
        )

        self.assertEqual(2, len(events))
        self.assertTrue(all(event.direction == "in" for event in events))


if __name__ == "__main__":
    unittest.main()
