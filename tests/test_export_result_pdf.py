# tests/test_export_result_pdf.py
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import the function to be tested
from services.pdf_service import generate_result_pdf

# --- MOCK Data Setup ---

# Define a standard mock result structure for testing
MOCK_RESULT_DATA = {
    "exam": {
        "title": "Advanced Python Final",
        "exam_date": "2025-12-10",
    },
    "submitted_at": datetime(2025, 12, 11, 14, 30, 0),
    "overall_total": 100,
    "overall_obtained": 75.5,
    "overall_percentage": 75.5,
    "mcq_total": 40,
    "mcq_obtained": 35,
    "sa_total": 60,
    "sa_obtained": 40.5,
    "mcq_results": [
        {
            "question_no": 1,
            "question_text": "What is the GIL?",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "correct_answer": "A",
            "student_answer": "A",
            "is_correct": True,
            "marks": 5,
            "marks_obtained": 5,
        }
    ],
    "sa_results": [
        {
            "question_no": 2,
            "question_text": "Explain decorators.",
            "student_answer": "They wrap a function...",
            "sample_answer": "Uses @ syntax to modify a function without changing its source.",
            "max_marks": 10,
            "awarded_marks": 8,
            "feedback": "Needs more detail on syntactic sugar.",
        }
    ],
}


class PDFServiceTest(unittest.TestCase):

    # Patch the core ReportLab classes used by the function
    @patch("services.pdf_service.SimpleDocTemplate")
    @patch("services.pdf_service.Table")
    @patch("services.pdf_service.Paragraph")
    def test_generate_result_pdf_calls_reportlab_correctly(
        self, MockParagraph, MockTable, MockSimpleDocTemplate
    ):
        """
        Tests if generate_result_pdf correctly initializes the PDF structure,
        calls table/paragraph creation for each data section, and calls doc.build().
        """
        # --- Setup Mock Document Instance ---
        mock_doc_instance = MockSimpleDocTemplate.return_value
        mock_doc_instance.build = MagicMock()

        # --- Execute Function ---
        pdf_bytes = generate_result_pdf(MOCK_RESULT_DATA)

        # 1. Assert Doc Initialization
        MockSimpleDocTemplate.assert_called_once()
        # The first argument is the BytesIO buffer

        # 2. Assert Title/Summary Section Elements
        # Check if the Title Paragraph was created
        MockParagraph.assert_any_call(
            "Exam Result: Advanced Python Final", unittest.mock.ANY
        )

        # Check if the main Summary Table was created
        self.assertTrue(
            MockTable.called, "Table constructor should be called at least once."
        )

        # Check if the build method was called on the document instance
        mock_doc_instance.build.assert_called_once()

        # 3. Assert MCQ Section Elements (Check for Question 1)
        # Check for the MCQ heading
        MockParagraph.assert_any_call("Multiple Choice Questions", unittest.mock.ANY)
        # Check for the MCQ question text (Paragraph for Q1)
        MockParagraph.assert_any_call(
            MOCK_RESULT_DATA["mcq_results"][0]["question_text"], unittest.mock.ANY
        )

        # 4. Assert SA Section Elements (Check for Question 2)
        # Check for the SA heading
        MockParagraph.assert_any_call("Short Answer Questions", unittest.mock.ANY)
        # Check for the SA question text (Paragraph for Q2)
        MockParagraph.assert_any_call(
            MOCK_RESULT_DATA["sa_results"][0]["question_text"], unittest.mock.ANY
        )

        # Check for SA student answer text
        MockParagraph.assert_any_call(
            MOCK_RESULT_DATA["sa_results"][0]["student_answer"], unittest.mock.ANY
        )

        # 5. Assert Return Value
        self.assertIsInstance(
            pdf_bytes, bytes, "Function should return PDF content as bytes."
        )

    def test_generate_result_pdf_handles_empty_sections(self):
        """
        Tests if generate_result_pdf handles missing MCQ or SA sections gracefully.
        """
        data_no_mcq = MOCK_RESULT_DATA.copy()
        data_no_mcq["mcq_results"] = []

        data_no_sa = MOCK_RESULT_DATA.copy()
        data_no_sa["sa_results"] = []

        # Use a mock that just captures the call to build, no deep patching needed
        with patch("services.pdf_service.SimpleDocTemplate") as MockDocTemplate:
            mock_doc_instance = MockDocTemplate.return_value
            mock_doc_instance.build = MagicMock()

            # Test 1: No MCQ
            generate_result_pdf(data_no_mcq)
            # Check that build was called successfully
            mock_doc_instance.build.assert_called_once()

            # Reset and Test 2: No SA
            mock_doc_instance.build.reset_mock()
            generate_result_pdf(data_no_sa)
            # Check that build was called successfully
            mock_doc_instance.build.assert_called_once()


# Note: Since the output is mocked and we don't save a file, we can't test
# the visual correctness or precise styling, but we ensure the elements are
# prepared and the document is built.

if __name__ == "__main__":
    unittest.main()
