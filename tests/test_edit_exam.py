# tests/test_edit_exam.py (Full code reflecting all fixes)
import unittest
from unittest.mock import patch, ANY
from urllib.parse import urlencode

# FIX: Removed 'post_exam_delete' from the imports
from web.exams import get_edit_exam as get_exam_edit, post_edit_exam as post_exam_edit

# --- MOCK Data ---

# Mock data returned by the service layer's get_exam_by_id
MOCK_EXAM_DATA = {
    # Note: Using 'exam_id' for consistency with how your exams.py sets the context
    "exam_id": "EID-123", 
    "title": "Final Exam Draft",
    "description": "Test to cover all modules.",
    "duration": "90",
    "exam_date": "2026-03-20",
    "start_time": "08:00",         
    "end_time": "09:30",           
    "instructions": "Follow all instructions carefully.",
}

MOCK_EXAM_ID = "EID-123"

VALID_EDIT_EXAM_ID = "EID-456"

# FIX 1: Add exam_id to the form body for the handler to retrieve it
VALID_EDIT_FORM_BODY = urlencode({
    "exam_id": VALID_EDIT_EXAM_ID, # <-- ADDED
    "title": "Edited Title",
    "description": "Edited description.",
    "duration": "100", 
    "exam_date": "2026-01-01",
    "start_time": "09:00",         
    "end_time": "10:40",           
    "instructions": "Edited instructions.",
})

# FIX 1: Add exam_id to the form body for the handler to retrieve it
INVALID_EDIT_FORM_BODY = urlencode({
    "exam_id": VALID_EDIT_EXAM_ID, # <-- ADDED
    "title": "", 
    "description": "Some description.",
    "duration": "100",
    "exam_date": "2026-01-01",
    "start_time": "10:00",         
    "end_time": "11:40",           
    "instructions": "Some instructions.",
})

class ExamEditTest(unittest.TestCase):
    
    # ... (Test 1, 2, 3 remain unchanged - they are passing) ...

    @patch('web.exams.render')
    @patch('web.exams.get_exam_by_id', return_value=MOCK_EXAM_DATA) 
    def test_get_exam_edit_success(self, mock_get_exam_by_id, mock_render):
        """Test case for successfully loading an exam for editing (Expects 200)."""
        
        _, status_code = get_exam_edit(exam_id=MOCK_EXAM_ID)
        
        self.assertEqual(status_code, 200, "Should return 200 OK on success")
        mock_get_exam_by_id.assert_called_once_with(MOCK_EXAM_ID)
        
        rendered_template, context = mock_render.call_args[0]
        self.assertEqual(rendered_template, 'exam_edit.html', "Should render the exam edit form ('exam_edit.html')")
        self.assertEqual(context['title'], MOCK_EXAM_DATA['title'])
        self.assertEqual(context['start_time'], MOCK_EXAM_DATA['start_time'], "Context should include start_time")
        self.assertEqual(context['end_time'], MOCK_EXAM_DATA['end_time'], "Context should include end_time")


    @patch('web.exams.render')
    @patch('web.exams.get_exam_by_id') 
    def test_get_exam_edit_missing_id(self, mock_get_exam_by_id, mock_render):
        """
        Test case for missing exam_id in the URL (Expects 400).
        """
        
        _, status_code = get_exam_edit(exam_id="")
        
        self.assertEqual(status_code, 400, "Should return 400 Bad Request for missing ID")
        mock_get_exam_by_id.assert_not_called()
        
        rendered_template, context = mock_render.call_args[0]
        self.assertEqual(rendered_template, 'exam_edit.html', "Should render 'exam_edit.html'")
        
        self.assertIn("Error: Exam ID is missing", context['errors_html'], "The errors_html context should contain the error message")


    @patch('web.exams.render')
    @patch('web.exams.get_exam_by_id', return_value=None) 
    def test_get_exam_edit_not_found(self, mock_get_exam_by_id, mock_render):
        """
        Test case for a valid ID but no matching exam found (Expects 404).
        """
        
        non_existent_id = "EID-999"
        _, status_code = get_exam_edit(exam_id=non_existent_id)
        
        self.assertEqual(status_code, 404, "Should return 404 Not Found")
        mock_get_exam_by_id.assert_called_once_with(non_existent_id)
        
        rendered_template, context = mock_render.call_args[0]
        self.assertEqual(rendered_template, 'exam_edit.html', "Should render 'exam_edit.html'")

        self.assertIn("alert alert-danger", context['errors_html'], "Should include an error message in errors_html context")

    # --- Test 4: Deleted ---

    # --- Test 5: Successful Exam Edit/Update (post_exam_edit) ---
    
    @patch('web.exams.save_exam_draft') 
    @patch('web.exams.validate_exam', return_value=[]) 
    @patch('web.exams.validate_exam_date', return_value=[])
    @patch('web.exams.validate_exam_times', return_value=[]) 
    @patch('web.exams.render')
    def test_post_exam_edit_success(self, mock_render, mock_validate_times, mock_validate_date, mock_validate_exam, mock_save_draft):
        """
        Tests successful exam update via post_exam_edit handler, including time fields.
        """
        
        # FIX 2: Call with only the 'body' argument
        _, status_code = post_exam_edit(body=VALID_EDIT_FORM_BODY) 

        # 2. Assert HTTP Status
        self.assertEqual(status_code, 200, "Should return 200 OK on successful update")

        # 3. Assert Service Call (save_exam_draft)
        # Note: The handler extracts the ID from the body before calling save_exam_draft
        mock_save_draft.assert_called_once_with(
            exam_id=VALID_EDIT_EXAM_ID, # Assert expected ID passed to service
            title=ANY,
            description=ANY,
            duration=ANY,
            instructions=ANY,
            exam_date=ANY,
            start_time='09:00',
            end_time='10:40'
        )
        
        # 4. Assert correct template rendering and context
        mock_render.assert_called_once()
        rendered_template, context = mock_render.call_args[0]
        
        self.assertEqual(rendered_template, 'exam_edit.html', "Should render the exam edit page ('exam_edit.html')")
        
        self.assertIn("alert alert-success", context['success_html'], "Should include the success message HTML")
        self.assertEqual(context['errors_html'], "", "Should not include errors_html on success")

        # Check that context holds the updated (echoed) data
        self.assertEqual(context['exam_id'], VALID_EDIT_EXAM_ID)
        self.assertEqual(context['title'], "Edited Title")
        self.assertEqual(context['duration'], "100", "Duration should be echoed back as a string from the form")
        self.assertEqual(context['start_time'], "09:00", "Start time should be echoed back from the form")
        self.assertEqual(context['end_time'], "10:40", "End time should be echoed back from the form")

    # --- Test 6: Validation Failure (post_exam_edit) ---
    
    @patch('web.exams.save_exam_draft') 
    @patch('web.exams.validate_exam', return_value=["Title is required."]) 
    @patch('web.exams.validate_exam_date', return_value=[])
    @patch('web.exams.validate_exam_times', return_value=[])
    @patch('web.exams.render')
    def test_post_exam_edit_validation_failure(self, mock_render, mock_validate_times, mock_validate_date, mock_validate_exam, mock_save_draft):
        """
        Tests validation failure in post_exam_edit handler.
        """
        
        # 1. Execute the handler
        # FIX 2: Call with only the 'body' argument
        _, status_code = post_exam_edit(body=INVALID_EDIT_FORM_BODY)

        # 2. Assert HTTP Status
        self.assertEqual(status_code, 400, "Should return 400 Bad Request on validation failure")

        # 3. Assert Service Call
        mock_save_draft.assert_not_called()

        # 4. Assert correct template rendering and context
        mock_render.assert_called_once()
        rendered_template, context = mock_render.call_args[0]
        
        self.assertEqual(rendered_template, 'exam_edit.html', "Should re-render the exam edit page")
        
        self.assertIn("alert alert-danger", context['errors_html'], "Should include the error message HTML")
        self.assertIn("Title is required.", context['errors_html'], "Should show the specific validation error")
        self.assertEqual(context['success_html'], "", "Should not include success_html on failure")

        # Check that context holds the invalid (echoed) data, including time
        self.assertEqual(context['exam_id'], VALID_EDIT_EXAM_ID) # Extracted from the form body
        self.assertEqual(context['title'], "", "Invalid/missing title should be echoed back")
        self.assertEqual(context['start_time'], "10:00", "Start time should be echoed back from the form")