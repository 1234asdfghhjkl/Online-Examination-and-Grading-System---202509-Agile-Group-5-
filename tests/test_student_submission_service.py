import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from services.student_submission_service import get_student_submissions

class StudentSubmissionServiceTest(unittest.TestCase):

    @patch("services.student_submission_service.check_results_released")
    @patch("services.student_submission_service.get_exam_by_id")
    @patch("services.student_submission_service.db.collection")
    def test_get_submissions_released(self, mock_collection, mock_get_exam, mock_check_release):
        """Positive: Fetch submissions where results are released."""
        
        # 1. Mock Firestore Data
        mock_doc = MagicMock()
        mock_doc.id = "SUB_001"
        mock_doc.to_dict.return_value = {
            "exam_id": "EXAM_1",
            "student_id": "S1",
            "mcq_score": 10,
            "submitted_at": datetime(2025, 1, 1)
        }
        
        # Mock the query chain: collection().where().stream()
        mock_stream = MagicMock()
        mock_stream.__iter__.return_value = [mock_doc]
        mock_collection.return_value.where.return_value.stream.return_value = [mock_doc]

        # 2. Mock Exam Data
        mock_get_exam.return_value = {"title": "Python Final", "exam_date": "2025-01-01"}

        # 3. Mock Release Status (Released)
        mock_check_release.return_value = (True, "2025-01-02", "10:00")

        # Execute
        results = get_student_submissions("S1")

        # Assertions
        self.assertEqual(len(results), 1)
        sub = results[0]
        self.assertEqual(sub["exam_title"], "Python Final")
        self.assertTrue(sub["results_released"])
        self.assertEqual(sub["submission_id"], "SUB_001")

    @patch("services.student_submission_service.check_results_released")
    @patch("services.student_submission_service.get_exam_by_id")
    @patch("services.student_submission_service.db.collection")
    def test_get_submissions_pending(self, mock_collection, mock_get_exam, mock_check_release):
        """Positive: Fetch submissions where results are pending (not released)."""
        
        # 1. Mock Firestore Data
        mock_doc = MagicMock()
        mock_doc.id = "SUB_002"
        mock_doc.to_dict.return_value = {"exam_id": "EXAM_2", "student_id": "S1"}
        
        mock_collection.return_value.where.return_value.stream.return_value = [mock_doc]

        # 2. Mock Exam Data
        mock_get_exam.return_value = {"title": "Pending Exam"}

        # 3. Mock Release Status (Not Released)
        mock_check_release.return_value = (False, None, None)

        # Execute
        results = get_student_submissions("S1")

        # Assertions
        self.assertEqual(len(results), 1)
        sub = results[0]
        self.assertFalse(sub["results_released"])
        self.assertEqual(sub["exam_title"], "Pending Exam")

    def test_get_submissions_no_id(self):
        """Negative: Return empty list if student_id is missing."""
        results = get_student_submissions("")
        self.assertEqual(results, [])

if __name__ == "__main__":
    unittest.main()