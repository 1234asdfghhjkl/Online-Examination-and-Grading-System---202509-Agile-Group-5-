# tests/test_short.py
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

# Import the function you want to test
from web.short_answer import post_short_builder

# Define a valid form submission body
VALID_FORM_BODY = urlencode(
    {
        "exam_id": "test_exam_102",
        "question_text": "Describe the main components of a short-answer question.",
        "sample_answer": "It includes the question text, a sample answer, and allocated marks.",
        "marks": "5",
    }
)

# Mock return value for get_short_answer_questions_by_exam
# (simulates a successful save leading to a preview list)
MOCK_QUESTION_LIST = [
    {"id": "sa1", "question_text": "Sample Q", "sample_answer": "Sample A", "marks": 5}
]


class ShortAnswerBuilderTest(unittest.TestCase):

    # --- Test 1: Success Case ---

    # 4. Outermost Patch (mock_create_short_answer)
    @patch("web.short_answer.create_short_answer_question")
    # 3. New Patch: get_short_answer_questions_by_exam (Required for rebuilding the preview HTML)
    @patch(
        "web.short_answer.get_short_answer_questions_by_exam",
        return_value=MOCK_QUESTION_LIST,
    )
    # 2. Middle Patch (exam_exists)
    @patch("web.short_answer.exam_exists", return_value=True)
    # 1. Innermost Patch (render)
    @patch("web.short_answer.render")
    def test_short_answer_creation_success(
        self, render, exam_exists, mock_get_questions, mock_create_short_answer
    ):
        """Test case for a successful short-answer question creation (Expects 200)."""

        # NOTE: Arguments order: render, exam_exists, mock_get_questions, mock_create_short_answer

        response_html, status_code = post_short_builder(
            exam_id="test_exam_102", body=VALID_FORM_BODY
        )

        self.assertEqual(status_code, 200, "Should return 200 OK on success")
        mock_create_short_answer.assert_called_once()
        mock_get_questions.assert_called_once()

        rendered_context = render.call_args[0][1]
        self.assertIn("successfully", rendered_context["success_html"])

    # --- Test 2: Missing Question Text Failure ---

    @patch("web.short_answer.create_short_answer_question")
    @patch(
        "web.short_answer.get_short_answer_questions_by_exam",
        return_value=MOCK_QUESTION_LIST,
    )
    @patch("web.short_answer.exam_exists", return_value=True)
    @patch("web.short_answer.render")
    def test_short_answer_creation_missing_question_text(
        self, render, exam_exists, mock_get_questions, mock_create_short_answer
    ):
        """Test case for a failed creation due to missing question text."""

        invalid_body = urlencode(
            {
                "exam_id": "test_exam_102",
                "question_text": "",  # Missing value
                "sample_answer": "A sample answer.",
                "marks": "5",
            }
        )

        response_html, status_code = post_short_builder(
            exam_id="test_exam_102", body=invalid_body
        )

        self.assertEqual(
            status_code, 400, "Should return 400 Bad Request on validation error"
        )
        mock_create_short_answer.assert_not_called()

        rendered_context = render.call_args[0][1]
        self.assertIn("Question text is required.", rendered_context["errors_html"])

    # --- Test 3: Invalid Marks Failure (Non-Positive) ---

    @patch("web.short_answer.create_short_answer_question")
    @patch(
        "web.short_answer.get_short_answer_questions_by_exam",
        return_value=MOCK_QUESTION_LIST,
    )
    @patch("web.short_answer.exam_exists", return_value=True)
    @patch("web.short_answer.render")
    def test_short_answer_creation_invalid_marks(
        self, render, exam_exists, mock_get_questions, mock_create_short_answer
    ):
        """
        Test case for a failed creation due to invalid marks (e.g., zero or non-digit).
        """
        invalid_body = urlencode(
            {
                "exam_id": "test_exam_102",
                "question_text": "A valid question.",
                "sample_answer": "A sample answer.",
                "marks": "0",  # Invalid value (must be positive integer)
            }
        )

        response_html, status_code = post_short_builder(
            exam_id="test_exam_102", body=invalid_body
        )

        self.assertEqual(
            status_code, 400, "Should return 400 Bad Request on validation error"
        )
        mock_create_short_answer.assert_not_called()

        rendered_context = render.call_args[0][1]
        self.assertIn(
            "Marks must be a positive integer.", rendered_context["errors_html"]
        )


if __name__ == "__main__":
    unittest.main()
