# tests/test_student_view_result.py
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import re 

# FIX 1: Corrected import path (kept from previous successful fixes)
from web.student_result_routes import get_student_result_view, get_student_result_pdf

# --- Helper Function for String Normalization ---
def normalize_html(html_string):
    """Removes leading/trailing whitespace and collapses multiple internal whitespace/newlines."""
    # Replace multiple spaces/newlines/tabs with a single space
    html_string = re.sub(r'\s+', ' ', html_string)
    # Strip leading/trailing space
    return html_string.strip()

# Mock the template_engine module to prevent template rendering errors
def mock_render(template_name, context):
    """Mock implementation for the render function."""
    content_html = context.get('content_html', 'content_placeholder')
    
    # FIX: Return ONLY the HTML content string (not a tuple).
    # This prevents the route function from returning a nested tuple, 
    # which caused the TypeError in normalize_html().
    return f"Template: {template_name}\nContent: {content_html}"

# FIX 2: Corrected patch path for render function (kept from previous successful fixes)
@patch('web.student_result_routes.render', side_effect=mock_render)
class StudentResultViewTest(unittest.TestCase):
    
    # --- Mock Data Setup ---
    MOCK_EXAM_ID = "EID-ABC"
    MOCK_STUDENT_ID = "S007"
    MOCK_PDF_BYTES = b"PDF_FILE_CONTENT"

    MOCK_SUCCESS_RESULT_DATA = {
        "exam": {"title": "Final Python Exam"},
        "submitted_at": datetime(2025, 12, 1, 10, 0, 0),
        "overall_total": 100,
        "overall_obtained": 85.5,
        "overall_percentage": 85.5,
        "mcq_total": 40,
        "mcq_obtained": 30,
        "sa_total": 60,
        "sa_obtained": 55.5,
        "mcq_results": [
            {
                "question_no": 1, 
                "question_text": "What is Python?",
                "option_a": "A snake", "option_b": "A language", "option_c": "A car", "option_d": "A fruit",
                "correct_answer": "B", 
                "student_answer": "B",
                "is_correct": True,
                "marks": 5, "marks_obtained": 5,
            }
        ],
        "sa_results": [
            {
                "question_no": 2,
                "question_text": "Explain OOP.",
                "student_answer": "Object-oriented programming...",
                "sample_answer": "Encapsulation, Inheritance, etc.",
                "max_marks": 10,
                "awarded_marks": 8,
                "feedback": "Missing polymorphism detail.",
            }
        ],
    }
    
    # --- Test Cases for get_student_result_view ---

    def test_view_missing_ids(self, mock_render_fn):
        """Test case for missing exam_id or student_id (Expects 400)."""
        response, status = get_student_result_view("", self.MOCK_STUDENT_ID)
        self.assertEqual(status, 400)
        normalized_response = normalize_html(response)
        self.assertIn("<h4>Error</h4>", normalized_response)
        self.assertIn("<p>Missing exam ID or student ID.</p>", normalized_response)

    @patch('web.student_result_routes.check_results_released', return_value=(False, "2025-12-15", "10:00"))
    @patch('web.student_result_routes.get_exam_by_id', return_value={"title": "Midterm Exam"})
    def test_view_results_pending_with_date(self, mock_get_exam, mock_check_released, mock_render_fn):
        """Test case where results are not yet released but a date is set (Expects 200)."""
        response, status = get_student_result_view(self.MOCK_EXAM_ID, self.MOCK_STUDENT_ID)
        self.assertEqual(status, 200)
        normalized_response = normalize_html(response)
        self.assertIn("<h2>⏰ Results Not Yet Released</h2>", normalized_response)
        self.assertIn("will be available on:", normalized_response)
        self.assertIn("2025-12-15 at 10:00", normalized_response)

    @patch('web.student_result_routes.check_results_released', return_value=(False, None, None))
    @patch('web.student_result_routes.get_exam_by_id', return_value={"title": "Midterm Exam"})
    def test_view_results_pending_no_date(self, mock_get_exam, mock_check_released, mock_render_fn):
        """Test case where results are not yet released and no date is set (Expects 200)."""
        response, status = get_student_result_view(self.MOCK_EXAM_ID, self.MOCK_STUDENT_ID)
        self.assertEqual(status, 200)
        normalized_response = normalize_html(response)
        self.assertIn("<h2>⏰ Results Not Yet Released</h2>", normalized_response)
        self.assertIn("The instructor has not set a release date yet", normalized_response)

    @patch('web.student_result_routes.check_results_released', return_value=(True, "2025-12-01", "00:00"))
    @patch('web.student_result_routes.get_student_result', return_value=None)
    def test_view_no_submission_found(self, mock_get_result, mock_check_released, mock_render_fn):
        """Test case where results are released but no submission exists (Expects 404)."""
        response, status = get_student_result_view(self.MOCK_EXAM_ID, self.MOCK_STUDENT_ID)
        self.assertEqual(status, 404)
        normalized_response = normalize_html(response)
        self.assertIn("<h4>No Submission Found</h4>", normalized_response)
        self.assertIn("<p>You have not submitted this exam yet.</p>", normalized_response)

    @patch('web.student_result_routes.check_results_released', return_value=(True, "2025-12-01", "00:00"))
    @patch('web.student_result_routes.get_student_result', return_value=MOCK_SUCCESS_RESULT_DATA)
    def test_view_success_content_check(self, mock_get_result, mock_check_released, mock_render_fn):
        """Test case for successful result viewing (Expects 200) and content check."""
        response, status = get_student_result_view(self.MOCK_EXAM_ID, self.MOCK_STUDENT_ID)
        self.assertEqual(status, 200)
        normalized_response = normalize_html(response)

        # Content assertions (now guaranteed to run successfully after TypeError fix)
        self.assertIn("score-value\">85.5/100", normalized_response) # Overall
        self.assertIn("score-value\">30/40", normalized_response)   # MCQ
        self.assertIn("score-value\">55.5/60", normalized_response) # Short Answer
        
        self.assertIn("<h5>Question 1 ✅ (5/5 marks)</h5>", normalized_response)
        self.assertIn("<strong>Your Answer:</strong> B", normalized_response)
        self.assertIn("<strong>Correct Answer:</strong> B", normalized_response)
        
        self.assertIn("<h5>Question 2 (8/10 marks)</h5>", normalized_response)
        self.assertIn("<strong>📝 Your Answer:</strong>", normalized_response)
        self.assertIn("<strong>💬 Instructor Feedback:</strong>", normalized_response)

        mock_get_result.assert_called_once_with(self.MOCK_EXAM_ID, self.MOCK_STUDENT_ID)
        
    # --- Test Cases for get_student_result_pdf ---
    
    def test_pdf_missing_ids(self, mock_render_fn):
        """Test case for missing exam_id or student_id for PDF (Expects 400)."""
        # The route function now returns 3 values (content, status, {})
        response, status, headers = get_student_result_pdf("", self.MOCK_STUDENT_ID)
        self.assertEqual(status, 400)
        self.assertIn("Error: Missing exam ID or student ID", response) 

    @patch('web.student_result_routes.check_results_released', return_value=(False, "2025-12-15", "10:00"))
    def test_pdf_results_not_released(self, mock_check_released, mock_render_fn):
        """Test case where results are not released for PDF generation (Expects 403)."""
        response, status, headers = get_student_result_pdf(self.MOCK_EXAM_ID, self.MOCK_STUDENT_ID)
        self.assertEqual(status, 403)
        self.assertIn("Error: Results not yet released", response)

    @patch('web.student_result_routes.check_results_released', return_value=(True, "2025-12-01", "00:00"))
    @patch('web.student_result_routes.get_student_result', return_value=None)
    def test_pdf_no_submission_found(self, mock_get_result, mock_check_released, mock_render_fn):
        """Test case where no submission exists for PDF generation (Expects 404)."""
        response, status, headers = get_student_result_pdf(self.MOCK_EXAM_ID, self.MOCK_STUDENT_ID)
        self.assertEqual(status, 404)
        self.assertIn("Error: No submission found", response)

    # FIX 9: Corrected patch path for generate_result_pdf to target its source module (kept from previous successful fixes)
    @patch('services.pdf_service.generate_result_pdf', return_value=MOCK_PDF_BYTES)
    @patch('web.student_result_routes.check_results_released', return_value=(True, "2025-12-01", "00:00"))
    @patch('web.student_result_routes.get_student_result', return_value=MOCK_SUCCESS_RESULT_DATA)
    def test_pdf_success(self, mock_get_result, mock_check_released, mock_generate_pdf, mock_render_fn):
        """Test case for successful PDF generation (Expects 200 and correct headers)."""
        response, status, headers = get_student_result_pdf(self.MOCK_EXAM_ID, self.MOCK_STUDENT_ID)
        
        self.assertEqual(status, 200)
        self.assertEqual(response, self.MOCK_PDF_BYTES)

        self.assertEqual(headers.get("Content-Type"), "application/pdf")
        self.assertIn('attachment; filename="result_Final_Python_Exam_S007.pdf"', headers.get("Content-Disposition"))
        
        mock_get_result.assert_called_once_with(self.MOCK_EXAM_ID, self.MOCK_STUDENT_ID)
        mock_generate_pdf.assert_called_once()


if __name__ == '__main__':
    # Add a mock for the pdf_service module before running tests
    import sys
    sys.modules["services.pdf_service"] = MagicMock()
    unittest.main()