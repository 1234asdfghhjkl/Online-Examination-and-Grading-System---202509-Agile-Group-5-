import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json
from urllib.parse import urlencode

from web.student_exam import (
    get_student_dashboard, 
    get_student_exam, 
    post_submit_student_exam
)

class StudentExamRoutesTest(unittest.TestCase):

    # --- MOCK RENDER ---
    def mock_render_side_effect(self, template_name, context):
        """Mock render to return a string with context data for verification"""
        return f"Template: {template_name} | Context: {context}"

    # =========================================================================
    # 1. STUDENT DASHBOARD TESTS
    # =========================================================================

    @patch("web.student_exam.render")
    @patch("services.student_submission_service.get_student_submissions")
    @patch("web.student_exam.get_all_published_exams")
    def test_get_dashboard_success(self, mock_get_exams, mock_get_subs, mock_render):
        """Positive: Dashboard loads with exams and submissions."""
        mock_render.side_effect = self.mock_render_side_effect
        
        # Mock Data
        mock_get_exams.return_value = [
            {"exam_id": "E1", "title": "Math Final", "duration": 60, "exam_date": "2025-10-10"}
        ]
        mock_get_subs.return_value = [
            {"exam_title": "History Quiz", "exam_id": "E0", "results_released": True}
        ]

        response, status = get_student_dashboard("S123")

        self.assertEqual(status, 200)
        self.assertIn("Template: student_dashboard.html", response)
        self.assertIn("Math Final", response) # Available exam
        self.assertIn("History Quiz", response) # Past submission

    @patch("web.student_exam.render")
    @patch("services.student_submission_service.get_student_submissions")
    @patch("web.student_exam.get_all_published_exams")
    def test_get_dashboard_empty(self, mock_get_exams, mock_get_subs, mock_render):
        """Positive: Dashboard loads cleanly with no data."""
        mock_render.side_effect = self.mock_render_side_effect
        mock_get_exams.return_value = []
        mock_get_subs.return_value = []

        response, status = get_student_dashboard("S123")

        self.assertEqual(status, 200)
        self.assertIn("No exams have been published yet", response)

    # =========================================================================
    # 2. EXAM ROOM ACCESS TESTS (GET)
    # =========================================================================

    @patch("web.student_exam.render")
    @patch("web.student_exam.get_server_time")
    @patch("web.student_exam.check_student_submission_status")
    @patch("web.student_exam.check_exam_access")
    @patch("web.student_exam.get_exam_by_id")
    def test_get_exam_active_access(self, mock_get_exam, mock_check_access, mock_check_sub, mock_server_time, mock_render):
        """Positive: Student accesses an active exam."""
        mock_render.side_effect = self.mock_render_side_effect
        
        # Setup Mocks
        mock_get_exam.return_value = {"title": "Active Exam", "duration": 60, "instructions": "Do well"}
        mock_check_access.return_value = {
            "can_access": True, "status": "active", "exam_start": datetime.now(), "exam_end": datetime.now()
        }
        mock_check_sub.return_value = {"has_submitted": False}
        mock_server_time.return_value = datetime(2025, 1, 1, 12, 0, 0)

        response, status = get_student_exam("E1", "S1")

        self.assertEqual(status, 200)
        self.assertIn("Template: student_exam.html", response)
        self.assertIn("'exam_status': 'active'", response)

    @patch("web.student_exam.render")
    @patch("web.student_exam.get_server_time")
    @patch("web.student_exam.check_student_submission_status")
    @patch("web.student_exam.check_exam_access")
    @patch("web.student_exam.get_exam_by_id")
    def test_get_exam_early_access(self, mock_get_exam, mock_check_access, mock_check_sub, mock_server_time, mock_render):
        """Negative/Flow: Student arrives before exam starts."""
        mock_render.side_effect = self.mock_render_side_effect
        
        mock_get_exam.return_value = {"title": "Future Exam"}
        mock_check_access.return_value = {
            "can_access": False, "status": "before_start", "message": "Starts soon"
        }
        mock_check_sub.return_value = {"has_submitted": False}
        mock_server_time.return_value = datetime.now()

        response, status = get_student_exam("E1", "S1")

        self.assertEqual(status, 200) # Page loads, but status is 'before_start'
        self.assertIn("'exam_status': 'before_start'", response)

    @patch("web.student_exam.render")
    def test_get_exam_missing_params(self, mock_render):
        """Negative: Missing parameters."""
        mock_render.side_effect = self.mock_render_side_effect
        
        response, status = get_student_exam("", "S1")
        self.assertEqual(status, 400)
        self.assertIn("Missing exam ID", response)

    @patch("web.student_exam.render")
    @patch("web.student_exam.get_exam_by_id")
    def test_get_exam_not_found(self, mock_get_exam, mock_render):
        """Negative: Exam does not exist."""
        mock_render.side_effect = self.mock_render_side_effect
        mock_get_exam.return_value = None
        
        response, status = get_student_exam("BAD_ID", "S1")
        self.assertEqual(status, 404)
        self.assertIn("not found", response)

    # =========================================================================
    # 3. EXAM SUBMISSION TESTS (POST)
    # =========================================================================

    # FIX: Patch the SERVICE directly because the import is inside the function
    @patch("services.grading_service.save_grading_result")
    @patch("services.grading_service.grade_mcq_submission")
    @patch("web.student_exam.db.collection")
    @patch("web.student_exam.check_student_submission_status")
    def test_post_submit_success(self, mock_check_sub, mock_db_coll, mock_grade, mock_save_grade):
        """Positive: Successful submission of exam."""
        
        # Mock not submitted yet
        mock_check_sub.return_value = {"has_submitted": False}
        
        # Mock Firestore .document().set()
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "SUB_123"
        mock_db_coll.return_value.document.return_value = mock_doc_ref

        # Prepare Form Data
        answers = {"mcq_1": "A", "sa_2": "Answer text"}
        body = urlencode({
            "exam_id": "E1", 
            "student_id": "S1", 
            "answers": json.dumps(answers)
        })

        response, status = post_submit_student_exam(body)

        self.assertEqual(status, 200)
        self.assertIn("Submission successful", response)
        
        # Verify DB save called
        mock_doc_ref.set.assert_called_once()
        # Verify grading triggered
        mock_grade.assert_called_once()

    @patch("web.student_exam.render")
    @patch("web.student_exam.check_student_submission_status")
    def test_post_submit_double_submission(self, mock_check_sub, mock_render):
        """Negative: Try to submit an already submitted exam."""
        mock_render.side_effect = self.mock_render_side_effect
        
        # Mock ALREADY submitted
        mock_check_sub.return_value = {"has_submitted": True}

        body = urlencode({"exam_id": "E1", "student_id": "S1"})
        
        response, status = post_submit_student_exam(body)

        self.assertEqual(status, 400)
        self.assertIn("already submitted", response)

if __name__ == "__main__":
    unittest.main()