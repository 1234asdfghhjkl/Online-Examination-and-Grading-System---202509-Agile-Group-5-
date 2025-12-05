# tests/test_grading_deadline.py
import unittest
from unittest.mock import patch
from datetime import datetime

# Import the function under test
# This function determines if the "uploading period" is over
from services.exam_service import check_grading_locked

# --- Mock Data ---

# An exam with a deadline set in the future
EXAM_OPEN = {
    "exam_id": "exam_future",
    "title": "Future Exam",
    "grading_deadline_date": "2030-01-01",
    "grading_deadline_time": "23:59",
}

# An exam with a deadline set in the past
EXAM_CLOSED = {
    "exam_id": "exam_past",
    "title": "Past Exam",
    "grading_deadline_date": "2020-01-01",
    "grading_deadline_time": "23:59",
}

# An exam with no deadline configured (Legacy/Default)
EXAM_NO_DEADLINE = {
    "exam_id": "exam_legacy",
    "title": "Legacy Exam",
    "grading_deadline_date": "",
    "grading_deadline_time": "",
}


class GradingDeadlineTest(unittest.TestCase):

    # We patch 'get_exam_by_id' to return our mock exam data
    # We patch 'datetime' in the service module to control "now" for consistent testing
    @patch("services.exam_service.datetime")
    @patch("services.exam_service.get_exam_by_id")
    def test_01_grading_period_is_open(self, mock_get_exam, mock_datetime):
        """
        User Story Scenario: The deadline has not passed yet.
        Expected: Grading is UNLOCKED (False). The lecturer can still upload grades.
        """
        # Setup: Return an exam with a deadline in 2030
        mock_get_exam.return_value = EXAM_OPEN

        # Setup: Simulate "Current Time" as today (2024)
        # Note: We ensure strptime works as expected while mocking now()
        mock_datetime.strptime.side_effect = datetime.strptime
        mock_datetime.now.return_value = datetime(2024, 12, 1, 12, 0, 0)

        # Action
        is_locked, message, details = check_grading_locked("exam_future")

        # Assert
        self.assertFalse(is_locked, "Grading should be OPEN before the deadline")
        self.assertIn("remaining", message)
        self.assertGreater(details["time_remaining_days"], 0)

    @patch("services.exam_service.datetime")
    @patch("services.exam_service.get_exam_by_id")
    def test_02_grading_period_is_closed(self, mock_get_exam, mock_datetime):
        """
        User Story Scenario: The deadline has passed.
        Expected: Grading is LOCKED (True). Admin can now release results.
        """
        # Setup: Return an exam with a deadline in 2020
        mock_get_exam.return_value = EXAM_CLOSED

        # Setup: Simulate "Current Time" as today (2024)
        mock_datetime.strptime.side_effect = datetime.strptime
        mock_datetime.now.return_value = datetime(2024, 12, 1, 12, 0, 0)

        # Action
        is_locked, message, details = check_grading_locked("exam_past")

        # Assert
        self.assertTrue(is_locked, "Grading should be LOCKED after the deadline")
        self.assertIn("Locked", message)
        self.assertIn("time_passed_days", details)

    @patch("services.exam_service.get_exam_by_id")
    def test_03_no_deadline_set(self, mock_get_exam):
        """
        Edge Case: The admin never set a deadline.
        Expected: Grading is UNLOCKED (False) by default to prevent blocking.
        """
        mock_get_exam.return_value = EXAM_NO_DEADLINE

        is_locked, message, _ = check_grading_locked("exam_legacy")

        self.assertFalse(is_locked, "Grading should be OPEN if no deadline is set")
        self.assertIn("No deadline set", message)

    @patch("services.exam_service.get_exam_by_id")
    def test_04_exam_not_found(self, mock_get_exam):
        """
        Edge Case: The exam ID does not exist in the database.
        Expected: Returns Locked=True (Fail safe) to prevent errors.
        """
        mock_get_exam.return_value = None

        is_locked, message, details = check_grading_locked("non_existent_id")

        self.assertTrue(is_locked)
        self.assertEqual(message, "Exam not found")


if __name__ == "__main__":
    unittest.main()
