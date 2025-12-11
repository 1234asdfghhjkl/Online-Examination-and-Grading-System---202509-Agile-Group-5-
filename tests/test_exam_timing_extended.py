import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from services.exam_timing import check_exam_access

# Malaysia Timezone for consistency
MY_TZ = timezone(timedelta(hours=8))

class ExamTimingExtendedTest(unittest.TestCase):

    @patch("services.exam_timing.get_server_time")
    @patch("services.exam_timing.db.collection")
    def test_access_denied_not_published(self, mock_collection, mock_server_time):
        """Negative: Exam exists but is in 'draft' mode."""
        
        # Mock Exam Data
        mock_exam = {
            "status": "draft",
            "exam_date": "2025-12-01",
            "start_time": "10:00",
            "duration": 60
        }
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = mock_exam
        mock_collection.return_value.document.return_value.get.return_value = mock_doc

        result = check_exam_access("E_DRAFT")

        self.assertFalse(result["can_access"])
        self.assertEqual(result["status"], "not_published")

    @patch("services.exam_timing.get_server_time")
    @patch("services.exam_timing.db.collection")
    def test_access_denied_exam_ended(self, mock_collection, mock_server_time):
        """Negative: Current time is after exam end time."""
        
        # Exam: 10:00 to 11:00
        mock_exam = {
            "status": "published",
            "exam_date": "2025-12-01",
            "start_time": "10:00",
            "duration": 60
        }
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = mock_exam
        mock_collection.return_value.document.return_value.get.return_value = mock_doc

        # Current Time: 11:01 (Ended)
        mock_server_time.return_value = datetime(2025, 12, 1, 11, 1, tzinfo=MY_TZ)

        result = check_exam_access("E_ENDED")

        self.assertFalse(result["can_access"])
        self.assertEqual(result["status"], "ended")

    @patch("services.exam_timing.db.collection")
    def test_access_denied_not_found(self, mock_collection):
        """Negative: Exam ID does not exist in DB."""
        
        mock_doc = MagicMock()
        mock_doc.exists = False # Does not exist
        mock_collection.return_value.document.return_value.get.return_value = mock_doc

        result = check_exam_access("E_NONEXISTENT")

        self.assertFalse(result["can_access"])
        self.assertEqual(result["status"], "not_found")

if __name__ == "__main__":
    unittest.main()