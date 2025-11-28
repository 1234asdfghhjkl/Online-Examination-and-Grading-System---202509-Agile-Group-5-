# tests/test_mcq.py
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

# Import the function you want to test
from web.mcq import post_mcq_builder

# Define a valid form submission body
VALID_FORM_BODY = urlencode({
    "exam_id": "test_exam_101",
    "question_text": "What is the capital of France?",
    "option_a": "Berlin",
    "option_b": "Madrid",
    "option_c": "Paris",
    "option_d": "Rome",
    "correct_option": "C",
    "marks": "3",
})

# Mock return value for get_mcq_questions_by_exam 
# (simulates a successful save leading to a preview list)
MOCK_QUESTION_LIST = [
    {"id": "q1", "question_no": 1, "options": {}, "correct_option": "A", "marks": 5}
]


class MCQBuilderTest(unittest.TestCase):
    
    # Decorum order (Top to Bottom): 4, 3, 2, 1
    # Function arguments order (Left to Right): 1, 2, 3, 4

    # --- Test 1: Success Case ---
    
    # 4. Outermost Patch (mock_create_mcq)
    @patch('web.mcq.create_mcq_question') 
    # 3. New Patch: get_mcq_questions_by_exam (Required for rebuilding the preview HTML)
    @patch('web.mcq.get_mcq_questions_by_exam', return_value=MOCK_QUESTION_LIST) 
    # 2. Middle Patch (exam_exists)
    @patch('web.mcq.exam_exists', return_value=True) 
    # 1. Innermost Patch (render)
    @patch('web.mcq.render') 
    def test_mcq_creation_success(self, render, exam_exists, mock_get_questions, mock_create_mcq):
        """Test case for a successful MCQ question creation (Expects 200)."""
        
        # NOTE: Arguments order: render, exam_exists, mock_get_questions, mock_create_mcq

        response_html, status_code = post_mcq_builder(
            exam_id="test_exam_101", 
            body=VALID_FORM_BODY
        )
        
        self.assertEqual(status_code, 200, "Should return 200 OK on success")
        mock_create_mcq.assert_called_once()
        mock_get_questions.assert_called_once()
        
        rendered_context = render.call_args[0][1]
        self.assertIn("successfully", rendered_context['success_html'])


    # --- Test 2: Missing Field Failure ---
    
    @patch('web.mcq.create_mcq_question')
    @patch('web.mcq.get_mcq_questions_by_exam', return_value=MOCK_QUESTION_LIST)
    @patch('web.mcq.exam_exists', return_value=True)
    @patch('web.mcq.render')
    def test_mcq_creation_missing_field(self, render, exam_exists, mock_get_questions, mock_create_mcq):
        """Test case for a failed creation due to a missing required field (marks)."""
        
        invalid_body = urlencode({
            "exam_id": "test_exam_101",
            "question_text": "A question",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "correct_option": "C",
            "marks": "",  # Missing value
        })
        
        response_html, status_code = post_mcq_builder(
            exam_id="test_exam_101", 
            body=invalid_body
        )
        
        self.assertEqual(status_code, 400, "Should return 400 Bad Request on validation error")
        mock_create_mcq.assert_not_called()
        
        rendered_context = render.call_args[0][1]
        self.assertIn("Marks allocation is required", rendered_context['errors_html'])


    # --- Test 3: Invalid Correct Option ---
    
    @patch('web.mcq.create_mcq_question')
    @patch('web.mcq.get_mcq_questions_by_exam', return_value=MOCK_QUESTION_LIST)
    @patch('web.mcq.exam_exists', return_value=True)
    @patch('web.mcq.render')
    def test_mcq_creation_invalid_correct_option(self, render, exam_exists, mock_get_questions, mock_create_mcq):
        """
        Test case for a failed creation due to an invalid correct_option value (e.g., 'E').
        """
        invalid_body = urlencode({
            "exam_id": "test_exam_101",
            "question_text": "A question",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "correct_option": "E",  # Invalid value
            "marks": "3",
        })

        response_html, status_code = post_mcq_builder(
            exam_id="test_exam_101",
            body=invalid_body
        )

        self.assertEqual(status_code, 400, "Should return 400 Bad Request on validation error")
        mock_create_mcq.assert_not_called()

        rendered_context = render.call_args[0][1]
        self.assertIn("Correct answer must be one of A, B, C, or D.", rendered_context['errors_html'])


if __name__ == '__main__':
    unittest.main()