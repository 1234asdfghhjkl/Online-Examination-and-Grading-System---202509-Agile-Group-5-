# tests/test_set_result_release_date.py
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
import re

# Import handler functions from admin_routes
from web.admin_routes import get_set_result_release, post_set_result_release

# --- Mock Data and Helpers ---

MOCK_EXAM_ID = "EID-ABC-123"

MOCK_EXAM_DATA = {
    "exam_id": MOCK_EXAM_ID,
    "title": "Database Systems Midterm",
    "description": "Exam covering SQL and normalization.",
    "exam_date": "2025-12-10",
    "start_time": "10:00",
    "end_time": "11:30",
    "result_release_date": "2025-12-20",
    "result_release_time": "09:00",
}

# Form data simulating a successful POST submission
VALID_POST_BODY = urlencode(
    {
        "exam_id": MOCK_EXAM_ID,
        "release_date": "2025-12-25",
        "release_time": "14:30",
    }
)


# Mock Render function
def mock_render(template_name, context):
    """Mocks the render function, returning a simple string of the template name and success/error messages."""
    # Include title in the output so tests can verify it
    title = context.get("title", "")
    mock_content = f"Template: {template_name}, Title: {title}, Success: {context.get('success_html', '')}, Errors: {context.get('errors_html', '')}"
    return mock_content  # Return only string, not tuple


# Helper to remove unnecessary whitespace from multi-line EXPECTED strings
def normalize_string(s: str) -> str:
    """Removes leading/trailing whitespace and collapses multiple internal whitespace/newlines."""
    return re.sub(r"\s+", " ", s.strip())


# Helper to extract the HTML string from the route's return tuple
def get_html_content(response_tuple: tuple) -> str:
    """Safely extracts the HTML string (first element) from the route's return."""
    if isinstance(response_tuple, tuple):
        return response_tuple[0]
    return response_tuple


class SetResultReleaseTest(unittest.TestCase):

    # --- Test Cases for GET handler (get_set_result_release) ---

    @patch("web.admin_routes.render", side_effect=mock_render)
    @patch("web.admin_routes.get_exam_by_id", return_value=MOCK_EXAM_DATA)
    def test_get_success(self, mock_get_exam, mock_render_fn):
        """Test case for successful retrieval of the release setting page."""
        response_tuple = get_set_result_release(MOCK_EXAM_ID)
        response_html = get_html_content(response_tuple)
        status_code = response_tuple[1]

        self.assertEqual(status_code, 200)
        self.assertIn("Template: set_result_release.html", response_html)

        mock_get_exam.assert_called_once_with(MOCK_EXAM_ID)
        self.assertEqual(mock_render_fn.call_args[0][1]["release_date"], "2025-12-20")

    @patch("web.admin_routes.render", side_effect=mock_render)
    @patch("web.admin_routes.get_exam_by_id", return_value=None)
    def test_get_exam_not_found(self, mock_get_exam, mock_render_fn):
        """Test case for a non-existent exam ID (Expects 404)."""
        response_tuple = get_set_result_release(MOCK_EXAM_ID)
        response_html = get_html_content(response_tuple)
        status_code = response_tuple[1]

        self.assertEqual(status_code, 404)
        self.assertIn("Template: set_result_release.html", response_html)
        self.assertIn(f'Exam "{MOCK_EXAM_ID}" not found', response_html)

    @patch("web.admin_routes.render", side_effect=mock_render)
    def test_get_missing_id(self, mock_render_fn):
        """Test case for calling GET without an exam ID (Expects 400)."""
        response_tuple = get_set_result_release("")
        response_html = get_html_content(response_tuple)
        status_code = response_tuple[1]

        self.assertEqual(status_code, 400)
        self.assertIn("Template: set_result_release.html", response_html)
        self.assertIn("Exam ID is missing", response_html)

    # --- Test Cases for POST handler (post_set_result_release) ---

    @patch("web.admin_routes.render", side_effect=mock_render)
    @patch("web.admin_routes.set_result_release_date")
    @patch("web.admin_routes.get_exam_by_id", return_value=MOCK_EXAM_DATA)
    @patch("web.admin_routes.validate_result_release_date", return_value=[])
    def test_post_success(
        self, mock_validate, mock_get_exam, mock_set_release_date, mock_render_fn
    ):
        """Test case for successful setting of the release date (Expects 200)."""
        response_tuple = post_set_result_release(VALID_POST_BODY)
        response_html = get_html_content(response_tuple)
        status_code = response_tuple[1]

        self.assertEqual(status_code, 200)

        expected_success_message = """
        <div class="alert alert-success mb-3">
            <strong>Success!</strong> Result release date has been set.
            <a href="/admin/exam-list" class="alert-link">Return to exam list</a>
        </div>
        """
        self.assertIn(
            normalize_string(expected_success_message), normalize_string(response_html)
        )

        mock_set_release_date.assert_called_once_with(
            exam_id=MOCK_EXAM_ID,
            release_date="2025-12-25",
            release_time="14:30",
        )
        mock_validate.assert_called_once()

    @patch("web.admin_routes.render", side_effect=mock_render)
    @patch("web.admin_routes.set_result_release_date")
    @patch("web.admin_routes.get_exam_by_id", return_value=MOCK_EXAM_DATA)
    @patch(
        "web.admin_routes.validate_result_release_date",
        return_value=["Release date must be after exam date."],
    )
    def test_post_validation_failure(
        self, mock_validate, mock_get_exam, mock_set_release_date, mock_render_fn
    ):
        """Test case for validation errors (e.g., date before exam date, Expects 400)."""
        response_tuple = post_set_result_release(VALID_POST_BODY)
        response_html = get_html_content(response_tuple)
        status_code = response_tuple[1]

        self.assertEqual(status_code, 400)

        expected_error_message = """
        <div class="alert alert-danger mb-3">
            <strong>Please fix the following:</strong>
            <ul class="mb-0"><li>Release date must be after exam date.</li></ul>
        </div>
        """
        self.assertIn(
            normalize_string(expected_error_message), normalize_string(response_html)
        )
        self.assertIn("Database Systems Midterm", response_html)

        mock_set_release_date.assert_not_called()
        mock_validate.assert_called_once()

    @patch("web.admin_routes.render", side_effect=mock_render)
    @patch("web.admin_routes.get_exam_by_id", return_value=None)
    def test_post_exam_not_found_failure(self, mock_get_exam, mock_render_fn):
        """Test case where exam ID is posted but not found (Expects 404)."""
        response_tuple = post_set_result_release(VALID_POST_BODY)
        response_html = get_html_content(response_tuple)
        status_code = response_tuple[1]

        self.assertEqual(status_code, 404)
        self.assertIn("Template: set_result_release.html", response_html)
        self.assertIn(f'Exam "{MOCK_EXAM_ID}" not found', response_html)

    @patch("web.admin_routes.render", side_effect=mock_render)
    @patch("web.admin_routes.get_exam_by_id", return_value=MOCK_EXAM_DATA)
    @patch(
        "web.admin_routes.set_result_release_date",
        side_effect=ValueError("Database connection failed"),
    )
    @patch("web.admin_routes.validate_result_release_date", return_value=[])
    def test_post_service_value_error(
        self, mock_validate, mock_set_release_date, mock_get_exam, mock_render_fn
    ):
        """Test case for a failure in the underlying service layer (Expects 500)."""
        response_tuple = post_set_result_release(VALID_POST_BODY)
        response_html = get_html_content(response_tuple)
        status_code = response_tuple[1]

        self.assertEqual(status_code, 500)

        expected_error_message = """
        <div class="alert alert-danger mb-3">
            <strong>Error:</strong> Database connection failed
        </div>
        """
        self.assertIn(
            normalize_string(expected_error_message), normalize_string(response_html)
        )
        self.assertIn("Template: set_result_release.html", response_html)
        self.assertIn("Database Systems Midterm", response_html)


if __name__ == "__main__":
    unittest.main()
