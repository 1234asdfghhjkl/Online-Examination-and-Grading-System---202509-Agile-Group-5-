# tests/test_admin_view_examlist.py
import unittest
from unittest.mock import patch
from datetime import datetime
import re

# Import the handler function
from web.admin_routes import get_admin_exam_list

# Mock Current Time for testing deadlines (Nov 28, 2025, 10:00 AM)
MOCK_NOW = datetime(2025, 11, 28, 10, 0, 0)


# --- FIXED MOCK RENDER FUNCTION ---
def mock_render(template_name, context):
    """
    Mocks the render function.
    Returns ONLY a string, matching the behavior of the real template_engine.render
    """
    return f"Template: {template_name}\nContent: {context.get('exam_list_html')}"


# --- Helper Function for String Normalization ---
def normalize_html(html_string):
    """Removes leading/trailing whitespace and collapses multiple internal whitespace/newlines."""
    # Find the content inside the 'Content: ' part of the mock response
    match = re.search(r"Content:\s*(.*)", html_string, re.DOTALL)
    if not match:
        content = html_string
    else:
        content = match.group(1)

    # Replace multiple spaces/newlines/tabs with a single space
    content = re.sub(r"\s+", " ", content)
    # Strip leading/trailing space
    return content.strip()


# --- MOCK Data Setup ---

MOCK_EXAMS_DATA = [
    {
        "exam_id": "EID-101",
        "title": "Open Grading, Scheduled Release (1d Left)",
        "description": "Standard exam.",
        "duration": 90,
        "exam_date": "2025-11-28",
        "start_time": "09:00",
        "end_time": "10:30",
        "grading_deadline_date": "2025-11-29",
        "grading_deadline_time": "14:00",
        "result_release_date": "2025-12-10",
        "result_release_time": "00:00",
        "results_finalized": False,
        "created_at": datetime(2025, 11, 20),
    },
    {
        "exam_id": "EID-102",
        "title": "Closed Grading, Results Released",
        "description": "Exam past all deadlines.",
        "duration": 60,
        "exam_date": "2025-11-26",
        "start_time": "10:00",
        "end_time": "11:00",
        "grading_deadline_date": "2025-11-27",
        "grading_deadline_time": "10:00",
        "result_release_date": "2025-11-27",
        "result_release_time": "09:00",
        "results_finalized": False,
        "created_at": datetime(2025, 11, 21),
    },
    {
        "exam_id": "EID-103",
        "title": "Urgent Grading (<24h Left)",
        "description": "Deadline approaching.",
        "duration": 120,
        "exam_date": "2025-11-28",
        "start_time": "14:00",
        "end_time": "16:00",
        "grading_deadline_date": "2025-11-28",
        "grading_deadline_time": "18:00",
        "result_release_date": "2025-12-01",
        "result_release_time": "00:00",
        "results_finalized": False,
        "created_at": datetime(2025, 11, 22),
    },
    {
        "exam_id": "EID-104",
        "title": "Legacy Exam (No Deadline)",
        "description": "Always open for grading.",
        "duration": 30,
        "exam_date": "2025-11-01",
        "start_time": "08:00",
        "end_time": "08:30",
        "results_finalized": False,
        "result_release_date": "2025-11-27",
        "result_release_time": "09:00",
        "created_at": datetime(2025, 11, 23),
    },
    {
        "exam_id": "EID-105",
        "title": "Finalized Exam",
        "description": "Locked results.",
        "duration": 60,
        "exam_date": "2025-11-25",
        "start_time": "10:00",
        "end_time": "11:00",
        "grading_deadline_date": "2025-11-29",
        "grading_deadline_time": "14:00",
        "result_release_date": "2025-12-10",
        "result_release_time": "00:00",
        "results_finalized": True,
        "finalized_at": datetime(2025, 11, 27, 15, 0, 0),
        "created_at": datetime(2025, 11, 24),
    },
]


class AdminExamListViewTest(unittest.TestCase):

    def setUp(self):
        # 1. Patch 'render' in web.admin_routes
        self.render_patcher = patch("web.admin_routes.render", side_effect=mock_render)
        self.mock_render = self.render_patcher.start()

        # 2. Patch 'datetime' in web.admin_routes
        self.datetime_patcher = patch("web.admin_routes.datetime")
        self.mock_datetime = self.datetime_patcher.start()

        # 3. Configure the mock datetime to return our fixed MOCK_NOW
        self.mock_datetime.now.return_value = MOCK_NOW
        
        # IMPORTANT: Pass through strptime/min so logic doesn't break
        self.mock_datetime.strptime = datetime.strptime
        self.mock_datetime.min = datetime.min

        # 4. Ensure patches are stopped cleanly after tests
        self.addCleanup(self.render_patcher.stop)
        self.addCleanup(self.datetime_patcher.stop)

    # --- Test 1: Empty List ---
    @patch("web.admin_routes.get_all_published_exams_for_admin", return_value=[])
    def test_empty_exam_list(self, mock_get_exams):
        """Test case when no published exams are available."""
        response_html, status_code = get_admin_exam_list()
        self.assertEqual(status_code, 200)
        self.assertIn("No published exams found", response_html)
        mock_get_exams.assert_called_once()

    # --- Test 2: Status Checking and Conditional Buttons ---
    @patch(
        "web.admin_routes.get_all_published_exams_for_admin",
        return_value=MOCK_EXAMS_DATA,
    )
    def test_full_exam_list_status_and_buttons(self, mock_get_exams):
        """Tests if grading status badges and action buttons are rendered correctly."""
        response_html, status_code = get_admin_exam_list()
        self.assertEqual(status_code, 200)

        normalized_content = normalize_html(response_html)

        # --- EID-101: Open Grading (1d Left) ---
        # Current Time: Nov 28, 10:00. Deadline: Nov 29, 14:00
        # Diff is 28 hours (1 day, 4 hours).
        # Logic: if days < 2: show Warning badge.
        self.assertIn("Open Grading, Scheduled Release (1d Left)", normalized_content)
        self.assertIn("badge bg-warning text-dark ms-2", normalized_content)  # FIXED: Expect Warning, not Info
        self.assertIn("1d Left", normalized_content)
        
        # Check Buttons
        self.assertIn('href="/grade-submissions?exam_id=EID-101"', normalized_content)
        # Finalize button should NOT be present
        self.assertNotIn("Finalize Results", normalized_content)

        # --- EID-102: Closed Grading ---
        self.assertIn("Closed Grading, Results Released", normalized_content)
        self.assertIn("Grading Closed", normalized_content)
        self.assertIn("badge bg-danger ms-2", normalized_content)
        self.assertNotIn('href="/grade-submissions?exam_id=EID-102"', normalized_content)

        # --- EID-103: Urgent Grading (<24h Left) ---
        self.assertIn("Urgent Grading (&lt;24h Left)", normalized_content)
        self.assertIn("8h Left", normalized_content)
        self.assertIn("badge bg-danger ms-2", normalized_content)
        self.assertIn('href="/grade-submissions?exam_id=EID-103"', normalized_content)

        # --- EID-104: Legacy Exam (No Deadline) ---
        self.assertIn("Legacy Exam (No Deadline)", normalized_content)
        self.assertIn("No Deadline", normalized_content)
        self.assertIn('href="/grade-submissions?exam_id=EID-104"', normalized_content)

        # --- EID-105: Finalized Exam ---
        self.assertIn("Finalized Exam", normalized_content)
        self.assertIn("Finalized on 2025-11-27 15:00", normalized_content)
        # NOTE: Deadline is still in future (Nov 29), so badge shows "1d Left", NOT "Grading Closed"
        # However, button is removed because is_grading_closed=True
        self.assertNotIn('href="/grade-submissions?exam_id=EID-105"', normalized_content)


if __name__ == "__main__":
    unittest.main()