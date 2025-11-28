# tests/test_create_exam.py
import unittest
from unittest.mock import patch, ANY
from urllib.parse import urlencode

from web.exams import post_submit_exam, post_publish_exam

VALID_FORM_BODY = urlencode({
    "exam_id": "test_exam_103",  # Existing ID simulates an update
    "title": "Introduction to Unit Testing",
    "description": "A short test on mocking and patch.",
    "duration": "60",
    "exam_date": "2025-12-01",
    "start_time": "10:00",
    "end_time": "11:00",
    "instructions": "Answer all questions honestly.",
})


class ExamHandlerTest(unittest.TestCase):

    # --- Test 1: Success Case (Save/Update Draft via post_submit_exam) ---
    
    # Mock services used to determine the review page buttons
    @patch('web.exams.has_short_for_exam', return_value=False)
    @patch('web.exams.has_mcq_for_exam', return_value=True)
    # Mock the save function, returning a faked ID
    @patch('web.exams.save_exam_draft', return_value="test_exam_103") 
    # Mock external validation, returning no errors
    @patch('web.exams.validate_exam_date', return_value=[]) 
    @patch('web.exams.validate_exam', return_value=[]) 
    # Mock the render engine
    @patch('web.exams.render') 
    def test_exam_submit_success(self, render, mock_validate_exam, mock_validate_date, mock_save_draft, mock_has_mcq, mock_has_short):
        """Test case for a successful exam draft submission (Expects 200 and calls save_exam_draft)."""

        _, status_code = post_submit_exam(body=VALID_FORM_BODY)

        self.assertEqual(status_code, 200, "Should return 200 OK on successful save")
        mock_save_draft.assert_called_once_with(
            exam_id='test_exam_103',
            title='Introduction to Unit Testing',
            description='A short test on mocking and patch.',
            duration='60',
            instructions='Answer all questions honestly.',
            exam_date='2025-12-01',
            start_time='10:00',
            end_time='11:00'
        )
        
        # Check that the redirect/review page is rendered
        render.assert_called_once_with('exam_review.html', ANY)
        
        # Check the context to ensure the button labels were set correctly
        rendered_context = render.call_args[0][1]
        self.assertEqual(rendered_context['exam_id'], 'test_exam_103')
        # has_mcq=True, has_short=False (based on mock values)
        self.assertIn('View / Edit MCQ', rendered_context['mcq_button_label'])
        self.assertIn('Build Short Answers', rendered_context['short_button_label'])


    # --- Test 2: Failure Case (Validation Errors in post_submit_exam) ---
    
    @patch('web.exams.save_exam_draft') # We assert this is NOT called
    @patch('web.exams.validate_exam_date', return_value=['Invalid date format.'])
    @patch('web.exams.validate_exam', return_value=['Title is required.'])
    @patch('web.exams.render')
    def test_exam_submit_validation_failure(self, render, mock_validate_exam, mock_validate_date, mock_save_draft):
        """Test case for validation errors (Expects 400 and does NOT call save_exam_draft)."""
        
        # Invalid data that triggers both validate_exam and validate_exam_date errors
        invalid_body = urlencode({
            "exam_id": "",
            "title": "", 
            "description": "Valid description",
            "duration": "10",
            "exam_date": "bad_date", 
            "start_time": "10:00",
            "end_time": "11:00",
            "instructions": "Inst",
        })

        _, status_code = post_submit_exam(body=invalid_body)

        self.assertEqual(status_code, 400, "Should return 400 Bad Request on validation error")
        mock_save_draft.assert_not_called()
        
        # Check that the error page is rendered (create_exam.html)
        render.assert_called_once_with('create_exam.html', ANY)

        rendered_context = render.call_args[0][1]
        self.assertIn('Title is required.', rendered_context['errors_html'])
        self.assertIn('Invalid date format.', rendered_context['errors_html'])
        # Check form data is preserved in the context
        self.assertEqual(rendered_context['title'], '') 
        self.assertEqual(rendered_context['exam_date'], 'bad_date')


    # --- Test 3: Publish Exam Success (post_publish_exam) ---
    
    @patch('web.exams.publish_exam') # Mock the function that changes the status to published
    @patch('web.exams.save_exam_draft', return_value="test_exam_103")
    @patch('web.exams.validate_exam_date', return_value=[])
    @patch('web.exams.validate_exam', return_value=[])
    @patch('web.exams.render')
    def test_exam_publish_success(self, render, mock_validate_exam, mock_validate_date, mock_save_draft, mock_publish_exam):
        """Test case for a successful exam publication (Expects 200 and calls publish_exam)."""
        
        _, status_code = post_publish_exam(body=VALID_FORM_BODY)

        self.assertEqual(status_code, 200, "Should return 200 OK on successful publish")
        
        # Check the two main service calls
        mock_save_draft.assert_called_once()
        mock_publish_exam.assert_called_once_with('test_exam_103') 

        # Check that the publish success page is rendered
        render.assert_called_once_with('exam_published.html', ANY)
        
        rendered_context = render.call_args[0][1]
        self.assertEqual(rendered_context['exam_id'], 'test_exam_103')


if __name__ == '__main__':
    unittest.main()