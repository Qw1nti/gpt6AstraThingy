import unittest

from veil_win.core import Box
from veil_win.tracking import MotionTracker


def face(left, top=30, category=1):
    return Box(left, top, left+40, top+40, .9, category)


class TrackingTests(unittest.TestCase):
    def test_capture_delay_is_compensated_and_prediction_is_bounded(self):
        tracker = MotionTracker()
        tracker.update([face(10)], ["old"], 1, 1.05, (400, 200), .3)
        tracker.update([face(30)], ["new"], 1.1, 1.15, (400, 200), .3)
        boxes, patches = tracker.render(1.15, (400, 200), .3)
        self.assertEqual(boxes[0].left, 40)  # 200px/sec * 50ms capture delay.
        self.assertEqual(patches, ["new"])
        self.assertEqual(tracker.render(1.25, (400, 200), .3)[0][0].left, 54)
        self.assertEqual(tracker.render(1.35, (400, 200), .3)[0][0].left, 54)

    def test_missed_detection_holds_briefly_then_expires(self):
        tracker = MotionTracker()
        tracker.update([face(10)], [], 1, 1.1, (400, 200), .3)
        tracker.update([], [], 1.2, 1.3, (400, 200), .3)
        self.assertTrue(tracker.render(1.35, (400, 200), .3)[0])
        self.assertFalse(tracker.render(1.41, (400, 200), .3)[0])

    def test_association_is_one_to_one_and_patches_follow_their_boxes(self):
        tracker = MotionTracker()
        tracker.update([face(10), face(100)], ["a", "b"], 1, 1, (400, 200), .3)
        tracker.update([face(90), face(20)], ["B", "A"], 1.1, 1.1, (400, 200), .3)
        boxes, patches = tracker.render(1.2, (400, 200), .3)
        self.assertEqual([box.left for box in boxes], [30, 80])
        self.assertEqual(patches, ["A", "B"])

    def test_scene_jump_resets_velocity_and_obsolete_positions(self):
        tracker = MotionTracker()
        tracker.update([face(10)], [], 1, 1, (800, 200), .3)
        tracker.update([face(30)], [], 1.1, 1.1, (800, 200), .3)
        tracker.update([face(500)], [], 1.2, 1.2, (800, 200), .3)
        self.assertEqual(tracker.render(1.3, (800, 200), .3)[0], [face(500)])

    def test_out_of_order_results_are_ignored_and_categories_do_not_match(self):
        tracker = MotionTracker()
        tracker.update([face(10)], [], 1, 1, (400, 200), .3)
        tracker.update([face(300)], [], .9, 1.1, (400, 200), .3)
        self.assertEqual(tracker.render(1.1, (400, 200), .3)[0], [face(10)])
        tracker.update([face(20, category=3)], [], 1.2, 1.2, (400, 200), .3)
        self.assertEqual(tracker.render(1.3, (400, 200), .3)[0], [face(20, category=3)])

    def test_prediction_clips_at_screen_edge(self):
        tracker = MotionTracker()
        tracker.update([face(320)], [], 1, 1, (400, 200), .3)
        tracker.update([face(350)], [], 1.1, 1.1, (400, 200), .3)
        boxes, _ = tracker.render(1.22, (400, 200), .3)
        self.assertEqual((boxes[0].left, boxes[0].right), (386, 400))


if __name__ == "__main__":
    unittest.main()
