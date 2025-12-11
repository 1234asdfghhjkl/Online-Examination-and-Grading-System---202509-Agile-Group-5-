import unittest
from unittest.mock import patch
from web.exams import get_exam_list


class LecturerAccessTest(unittest.TestCase):

    # --- Test 1: Positive - Lecturer sees THEIR OWN exams ---
    @patch("web.exams.render")
    @patch("web.exams.get_exams_by_lecturer")
    def test_lecturer_sees_own_exams(self, mock_get_by_lec, mock_render):
        """
        Scenario: Lecturer L001 logs in.
        Expected: System calls get_exams_by_lecturer('L001') and displays the result.
        """
        # Mock Data: L001 has created one exam
        mock_get_by_lec.return_value = [
            {
                "exam_id": "E1",
                "title": "L001's Python Exam",
                "created_by": "L001",
                "status": "published",
                "exam_date": "2025-12-01",
                "start_time": "10:00",
                "end_time": "11:00",
                "duration": 60,
            }
        ]

        # Action: Call get_exam_list as "L001"
        get_exam_list(lecturer_id="L001")

        # Assertion 1: Verify we asked the database SPECIFICALLY for L001's exams
        mock_get_by_lec.assert_called_once_with("L001")

        # Assertion 2: Verify the exam title appears in the rendered HTML
        context = mock_render.call_args[0][1]
        # Note: ' becomes &#x27; in HTML (security escaping)
        self.assertIn("L001&#x27;s Python Exam", context["exam_list_html"])
        # Verify the "Grade" button is present
        self.assertIn("Grade", context["exam_list_html"])

    # --- Test 2: Negative - Lecturer CANNOT see other people's exams ---
    @patch("web.exams.render")
    @patch("web.exams.get_exams_by_lecturer")
    def test_lecturer_cannot_see_other_exams(self, mock_get_by_lec, mock_render):
        """
        Scenario: Lecturer L001 logs in.
        There exists an exam by 'L002' in the system, but the database query
        for 'L001' should return empty.
        Expected: The HTML should NOT contain the other lecturer's exam.
        """
        # Mock Data: Querying for L001 returns nothing (even if L002 exists elsewhere)
        mock_get_by_lec.return_value = []

        # Action: Call get_exam_list as "L001"
        get_exam_list(lecturer_id="L001")

        # Assertion: The list should be empty
        context = mock_render.call_args[0][1]

        # Verify "No exams found" message is shown
        self.assertIn("No exams found", context["exam_list_html"])

        # Verify that an exam title belonging to someone else is DEFINITELY NOT there
        self.assertNotIn("L002&#x27;s Secret Exam", context["exam_list_html"])

    # --- Test 3: Admin sees EVERYTHING (No ID passed) ---
    @patch("web.exams.render")
    @patch("web.exams.get_all_exams")
    @patch("web.exams.get_exams_by_lecturer")
    def test_admin_view_unfiltered(self, mock_get_by_lec, mock_get_all, mock_render):
        """
        Scenario: Admin visits page (lecturer_id is None).
        Expected: System calls get_all_exams() instead of the filter function.
        """
        # Action: Call without an ID
        get_exam_list(lecturer_id=None)

        # Assertion: Should NOT try to filter by lecturer
        mock_get_by_lec.assert_not_called()

        # Assertion: Should call the "Get All" function
        mock_get_all.assert_called_once()
