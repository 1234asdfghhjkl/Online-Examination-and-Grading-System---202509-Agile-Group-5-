# tests/test_grade_short.py
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

# Import the handler function
from web.grading import post_save_short_answer_grades

# --- MOCK Data ---

MOCK_SUBMISSION_ID = "SUB-101"
MOCK_EXAM_ID = "EID-101"

# Submission data structure returned by get_submission_with_questions (required by the handler)
MOCK_SUBMISSION_DATA = {
    "submission_id": MOCK_SUBMISSION_ID,
    "exam_id": MOCK_EXAM_ID,
    "student_id": "student_001",
    # short_answer_questions tells the handler which fields to expect
    "short_answer_questions": [
        {"question_no": 1, "max_marks": 10},
        {"question_no": 2, "max_marks": 5},
    ],
    "mcq_score": 15,
    "mcq_total": 20,
}

# Form data simulating a successful POST submission
VALID_GRADING_FORM_BODY = urlencode({
    "submission_id": MOCK_SUBMISSION_ID,
    
    # Grade for Question 1 (10 marks max)
    "marks_1": "8.5",
    "max_marks_1": "10",
    "feedback_1": "Good effort, but missed one key point.",
    
    # Grade for Question 2 (5 marks max)
    "marks_2": "5",
    "max_marks_2": "5",
    "feedback_2": "Perfect answer.",
})

# Expected data structure passed to save_short_answer_grades service function
EXPECTED_GRADES_DICT = {
    "1": {
        "marks": 8.5, 
        "max_marks": 10.0,
        "feedback": "Good effort, but missed one key point.",
    },
    "2": {
        "marks": 5.0, 
        "max_marks": 5.0,
        "feedback": "Perfect answer.",
    },
}


class GradeShortAnswerTest(unittest.TestCase):

    # --- Test 1: Successful Grade Submission ---
    
    @patch('web.grading.save_short_answer_grades')
    @patch('web.grading.get_submission_with_questions', return_value=MOCK_SUBMISSION_DATA)
    def test_grade_short_answer_success(self, mock_get_submission, mock_save_grades):
        """
        Test case for a successful submission of short answer grades.
        Checks if the service function is called with the correctly parsed data.
        """
        
        response_html, status_code = post_save_short_answer_grades(body=VALID_GRADING_FORM_BODY)

        # 1. Assert HTTP Status
        self.assertEqual(status_code, 200, "Should return 200 OK on successful save and redirect.")
        
        # 2. Assert Service Calls
        mock_get_submission.assert_called_once_with(MOCK_SUBMISSION_ID)
        
        # 3. Assert save_short_answer_grades was called with correctly parsed/typed data
        mock_save_grades.assert_called_once_with(
            MOCK_SUBMISSION_ID,
            EXPECTED_GRADES_DICT
        )
        
        # 4. Assert Redirect (to the submissions list)
        self.assertIn(f'url=/grade-submissions?exam_id={MOCK_EXAM_ID}', response_html)


    # --- Test 2: Missing Submission ID Failure ---
    
    @patch('web.grading.save_short_answer_grades')
    @patch('web.grading.get_submission_with_questions')
    def test_grade_short_answer_missing_submission_id(self, mock_get_submission, mock_save_grades):
        """Test case for missing submission_id in the form body (Expects 400)."""
        
        invalid_body = urlencode({
            "submission_id": "", # Missing/empty ID
            "marks_1": "5",
        })
        
        response_html, status_code = post_save_short_answer_grades(body=invalid_body)

        self.assertEqual(status_code, 400, "Should return 400 Bad Request for missing ID.")
        self.assertIn("Missing submission ID", response_html)
        mock_get_submission.assert_not_called()
        mock_save_grades.assert_not_called()

    
    # --- Test 3: Submission Not Found Failure ---
    
    @patch('web.grading.save_short_answer_grades')
    @patch('web.grading.get_submission_with_questions', return_value=None)
    def test_grade_short_answer_submission_not_found(self, mock_get_submission, mock_save_grades):
        """Test case where submission ID is valid but not found in DB (Expects 404)."""
        
        response_html, status_code = post_save_short_answer_grades(body=VALID_GRADING_FORM_BODY)

        self.assertEqual(status_code, 404, "Should return 404 Not Found.")
        self.assertIn("Submission not found", response_html)
        mock_get_submission.assert_called_once()
        mock_save_grades.assert_not_called()
        
    
    # --- Test 4: Handling Empty/Zero Marks/Feedback ---
    
    @patch('web.grading.save_short_answer_grades')
    @patch('web.grading.get_submission_with_questions', return_value=MOCK_SUBMISSION_DATA)
    def test_grade_short_answer_empty_marks_and_feedback(self, mock_get_submission, mock_save_grades):
        """
        Test case for submitting empty/zero marks and empty feedback.
        Checks if they are correctly defaulted to 0.0 and empty string.
        """
        
        # Form data with missing marks, zero marks, and empty feedback
        zero_grade_form_body = urlencode({
            "submission_id": MOCK_SUBMISSION_ID,
            
            # Question 1: Marks missing (should default to 0.0)
            "marks_1": "", 
            "max_marks_1": "10",
            "feedback_1": "", # Empty feedback
            
            # Question 2: Marks explicitly zero
            "marks_2": "0", 
            "max_marks_2": "5",
            "feedback_2": "",
        })
        
        expected_zero_grades_dict = {
            "1": {
                "marks": 0.0, 
                "max_marks": 10.0,
                "feedback": "",
            },
            "2": {
                "marks": 0.0, 
                "max_marks": 5.0,
                "feedback": "",
            },
        }

        _, status_code = post_save_short_answer_grades(body=zero_grade_form_body)

        self.assertEqual(status_code, 200)
        
        # Assert save_short_answer_grades was called with correctly defaulted data
        mock_save_grades.assert_called_once_with(
            MOCK_SUBMISSION_ID,
            expected_zero_grades_dict
        )


if __name__ == '__main__':
    unittest.main()