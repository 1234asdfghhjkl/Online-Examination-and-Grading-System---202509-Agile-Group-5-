import unittest
from unittest.mock import patch

from web.exams import get_exam_delete


class DeleteExamHandlerTest(unittest.TestCase):
    # --- Test 1: Hard delete success ---

    @patch("web.exams.get_exam_list", return_value=("<html>ok</html>", 200))
    @patch("web.exams.delete_exam_and_contents")
    @patch("web.exams.soft_delete_exam")
    def test_hard_delete_success(
        self,
        mock_soft_delete,
        mock_hard_delete,
        mock_get_exam_list,
    ):
        """Hard delete should call delete_exam_and_contents and reload exam list with success message."""

        html_str, status_code = get_exam_delete(exam_id="EID-12345", method="hard")

        self.assertEqual(status_code, 200, "Hard delete should return 200 OK")

        # hard delete is called, soft delete is not
        mock_hard_delete.assert_called_once_with("EID-12345")
        mock_soft_delete.assert_not_called()

        # exam list is re-rendered with the correct success message
        mock_get_exam_list.assert_called_once_with(
            success_message="Exam deleted successfully."
        )
        self.assertIn("html", html_str)  # sanity check that we got HTML back

    # --- Test 2: Soft delete success ---

    @patch("web.exams.get_exam_list", return_value=("<html>ok</html>", 200))
    @patch("web.exams.delete_exam_and_contents")
    @patch("web.exams.soft_delete_exam")
    def test_soft_delete_success(
        self,
        mock_soft_delete,
        mock_hard_delete,
        mock_get_exam_list,
    ):
        """Soft delete should mark exam as deleted but keep data, then reload exam list."""

        html_str, status_code = get_exam_delete(exam_id="EID-67890", method="soft")

        self.assertEqual(status_code, 200, "Soft delete should return 200 OK")

        # soft delete is called, hard delete is not
        mock_soft_delete.assert_called_once_with("EID-67890")
        mock_hard_delete.assert_not_called()

        # exam list is re-rendered with the correct success message
        mock_get_exam_list.assert_called_once_with(
            success_message="Exam removed from list."
        )
        self.assertIn("html", html_str)

    # --- Test 3: Missing exam_id ---

    @patch("web.exams.get_exam_list")
    @patch("web.exams.delete_exam_and_contents")
    @patch("web.exams.soft_delete_exam")
    def test_delete_missing_exam_id(
        self,
        mock_soft_delete,
        mock_hard_delete,
        mock_get_exam_list,
    ):
        """If exam_id is missing, handler should return 400 and not call any delete functions."""

        html_str, status_code = get_exam_delete(exam_id="", method="hard")

        self.assertEqual(
            status_code, 400, "Missing exam_id should return 400 Bad Request"
        )
        self.assertIn("Missing exam ID", html_str)

        mock_soft_delete.assert_not_called()
        mock_hard_delete.assert_not_called()
        mock_get_exam_list.assert_not_called()

    # --- Test 4: Delete error from service (ValueError) ---

    @patch("web.exams.get_exam_list")
    @patch(
        "web.exams.delete_exam_and_contents", side_effect=ValueError("Exam not found")
    )
    @patch("web.exams.soft_delete_exam")
    def test_hard_delete_service_error(
        self,
        mock_soft_delete,
        mock_hard_delete,
        mock_get_exam_list,
    ):
        """If the service raises ValueError, handler should return 404 with error message."""

        html_str, status_code = get_exam_delete(
            exam_id="EID-DOES-NOT-EXIST", method="hard"
        )

        self.assertEqual(status_code, 404, "Service error should return 404 Not Found")
        self.assertIn("Could not delete exam:", html_str)

        mock_soft_delete.assert_not_called()
        mock_get_exam_list.assert_not_called()  # no list reload on failure
        mock_hard_delete.assert_called_once_with("EID-DOES-NOT-EXIST")


if __name__ == "__main__":
    unittest.main()
