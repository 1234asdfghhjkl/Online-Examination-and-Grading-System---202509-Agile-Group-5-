# tests/test_view_grading.py
import unittest
from unittest.mock import patch
from datetime import datetime
from urllib.parse import urlencode

# Import functions to test
from web.grading import (
    get_grade_submissions,
    get_grade_short_answers,
    post_save_short_answer_grades,
    get_view_submission_result,
)

# Mock exam data
MOCK_EXAM = {
    "exam_id": "exam_123",
    "title": "Midterm Exam 2024",
    "exam_date": "2024-03-15",
    "grading_deadline_date": "2024-03-20",
    "grading_deadline_time": "23:59",
}

# Mock exam with expired deadline (for locked tests)
MOCK_EXAM_LOCKED = {
    "exam_id": "exam_locked",
    "title": "Past Exam",
    "exam_date": "2024-01-15",
    "grading_deadline_date": "2024-01-20",
    "grading_deadline_time": "23:59",
}

# Mock submissions list
MOCK_SUBMISSIONS = [
    {
        "submission_id": "sub_001",
        "student_id": "S001",
        "exam_id": "exam_123",
        "submitted_at": datetime(2024, 3, 15, 10, 30, 0),
        "mcq_score": 40,
        "mcq_total": 50,
        "sa_obtained_marks": 0,
        "sa_total_marks": 50,
        "mcq_graded": True,
        "sa_graded": False,
        "fully_graded": False,
    },
    {
        "submission_id": "sub_002",
        "student_id": "S002",
        "exam_id": "exam_123",
        "submitted_at": datetime(2024, 3, 15, 11, 0, 0),
        "mcq_score": 45,
        "mcq_total": 50,
        "sa_obtained_marks": 40,
        "sa_total_marks": 50,
        "mcq_graded": True,
        "sa_graded": True,
        "fully_graded": True,
    },
]

# Mock submission with questions
MOCK_SUBMISSION_WITH_QUESTIONS = {
    "submission_id": "sub_001",
    "student_id": "S001",
    "exam_id": "exam_123",
    "submitted_at": datetime(2024, 3, 15, 10, 30, 0),
    "mcq_score": 40,
    "mcq_total": 50,
    "sa_obtained_marks": 0,
    "sa_total_marks": 50,
    "short_answer_questions": [
        {
            "question_no": 1,
            "question_text": "Explain the concept of inheritance in OOP",
            "sample_answer": "Inheritance allows a class to inherit properties...",
            "student_answer": "Inheritance is when a class uses another class...",
            "max_marks": 10,
        },
        {
            "question_no": 2,
            "question_text": "What is polymorphism?",
            "sample_answer": "Polymorphism means many forms...",
            "student_answer": "Polymorphism allows objects to take different forms",
            "max_marks": 10,
        },
    ],
    "short_answer_grades": {
        "1": {"marks": 8, "feedback": "Good understanding", "max_marks": 10},
        "2": {"marks": 9, "feedback": "Excellent", "max_marks": 10},
    },
    "grading_result": {
        "question_results": [
            {
                "question_no": 1,
                "question_text": "What is 2+2?",
                "student_answer": "4",
                "correct_answer": "4",
                "is_correct": True,
                "marks": 5,
                "marks_obtained": 5,
            }
        ]
    },
}

# Form data for saving grades
VALID_GRADE_FORM = urlencode({
    "submission_id": "sub_001",
    "marks_1": "8",
    "feedback_1": "Good understanding",
    "max_marks_1": "10",
    "marks_2": "9",
    "feedback_2": "Excellent",
    "max_marks_2": "10",
})


class GradingRoutesTest(unittest.TestCase):

    # ========================================
    # TEST 1: Get Grade Submissions - Success
    # ========================================
    
    @patch("web.grading.render")
    @patch("web.grading.get_all_submissions_for_exam", return_value=MOCK_SUBMISSIONS)
    @patch("web.grading.check_grading_locked", return_value=(False, "Open", None))
    @patch("web.grading.get_exam_by_id", return_value=MOCK_EXAM)
    def test_get_grade_submissions_success(
        self, mock_get_exam, mock_check_locked, mock_get_subs, mock_render
    ):
        """Test successful retrieval of submissions list for grading."""
        
        mock_render.return_value = "<html>Submissions List</html>"
        
        response_html, status_code = get_grade_submissions(exam_id="exam_123")
        
        self.assertEqual(status_code, 200, "Should return 200 OK")
        mock_get_exam.assert_called_once_with("exam_123")
        mock_get_subs.assert_called_once_with("exam_123")
        mock_check_locked.assert_called_once_with("exam_123")
        
        # Verify render was called with correct context
        render_context = mock_render.call_args[0][1]
        self.assertEqual(render_context["exam_id"], "exam_123")
        self.assertEqual(render_context["exam_title"], "Midterm Exam 2024")
        self.assertIn("submissions_list_html", render_context)

    # ========================================
    # TEST 2: Get Grade Submissions - Missing Exam ID
    # ========================================
    
    @patch("web.grading.render")
    @patch("web.grading.get_exam_by_id")
    def test_get_grade_submissions_missing_exam_id(self, mock_get_exam, mock_render):
        """Test handling when exam_id is missing."""
        
        mock_render.return_value = "<html>Error</html>"
        
        response_html, status_code = get_grade_submissions(exam_id=None)
        
        self.assertEqual(status_code, 400, "Should return 400 Bad Request")
        mock_get_exam.assert_not_called()
        
        render_context = mock_render.call_args[0][1]
        self.assertIn("Missing exam ID", render_context["message_html"])

    # ========================================
    # TEST 3: Get Grade Submissions - Exam Not Found
    # ========================================
    
    @patch("web.grading.render")
    @patch("web.grading.get_exam_by_id", return_value=None)
    def test_get_grade_submissions_exam_not_found(self, mock_get_exam, mock_render):
        """Test handling when exam doesn't exist."""
        
        mock_render.return_value = "<html>Error</html>"
        
        response_html, status_code = get_grade_submissions(exam_id="nonexistent")
        
        self.assertEqual(status_code, 404, "Should return 404 Not Found")
        mock_get_exam.assert_called_once_with("nonexistent")
        
        render_context = mock_render.call_args[0][1]
        self.assertIn("not found", render_context["message_html"])

    # ========================================
    # TEST 4: Get Grade Submissions - No Submissions
    # ========================================
    
    @patch("web.grading.render")
    @patch("web.grading.get_all_submissions_for_exam", return_value=[])
    @patch("web.grading.check_grading_locked", return_value=(False, "Open", None))
    @patch("web.grading.get_exam_by_id", return_value=MOCK_EXAM)
    def test_get_grade_submissions_no_submissions(
        self, mock_get_exam, mock_check_locked, mock_get_subs, mock_render
    ):
        """Test display when exam has no submissions yet."""
        
        mock_render.return_value = "<html>No Submissions</html>"
        
        response_html, status_code = get_grade_submissions(exam_id="exam_123")
        
        self.assertEqual(status_code, 200, "Should return 200 OK")
        
        render_context = mock_render.call_args[0][1]
        self.assertIn("No submissions yet", render_context["submissions_list_html"])

    # ========================================
    # TEST 5: Get Grade Submissions - Locked Deadline
    # ========================================
    
    @patch("web.grading.render")
    @patch("web.grading.get_all_submissions_for_exam", return_value=MOCK_SUBMISSIONS)
    @patch("web.grading.check_grading_locked", return_value=(True, "Grading closed", None))
    @patch("web.grading.get_exam_by_id", return_value=MOCK_EXAM_LOCKED)
    def test_get_grade_submissions_locked(
        self, mock_get_exam, mock_check_locked, mock_get_subs, mock_render
    ):
        """Test that locked exams show read-only mode."""
        
        mock_render.return_value = "<html>Locked View</html>"
        
        response_html, status_code = get_grade_submissions(exam_id="exam_locked")
        
        self.assertEqual(status_code, 200, "Should return 200 OK even when locked")
        
        render_context = mock_render.call_args[0][1]
        # Should show lock alert
        self.assertIn("Grading closed", render_context["message_html"])

        self.assertIn("Grading closed", render_context["message_html"])

    # ========================================
    # TEST 6: Get Grade Short Answers - Success
    # ========================================
    
    @patch("web.grading.render")
    @patch("web.grading.check_grading_locked", return_value=(False, "Open", None))
    @patch("web.grading.get_exam_by_id", return_value=MOCK_EXAM)
    @patch("web.grading.get_submission_with_questions", return_value=MOCK_SUBMISSION_WITH_QUESTIONS)
    def test_get_grade_short_answers_success(
        self, mock_get_sub, mock_get_exam, mock_check_locked, mock_render
    ):
        """Test successful display of grading interface."""
        
        mock_render.return_value = "<html>Grading Interface</html>"
        
        response_html, status_code = get_grade_short_answers(submission_id="sub_001")
        
        self.assertEqual(status_code, 200, "Should return 200 OK")
        mock_get_sub.assert_called_once_with("sub_001")
        
        render_context = mock_render.call_args[0][1]
        self.assertEqual(render_context["submission_id"], "sub_001")
        self.assertEqual(render_context["student_id"], "S001")
        self.assertIn("questions_html", render_context)

    # ========================================
    # TEST 7: Get Grade Short Answers - Missing Submission ID
    # ========================================
    
    @patch("web.grading.get_submission_with_questions")
    def test_get_grade_short_answers_missing_id(self, mock_get_sub):
        """Test handling when submission_id is missing."""
        
        response_html, status_code = get_grade_short_answers(submission_id=None)
        
        self.assertEqual(status_code, 400, "Should return 400 Bad Request")
        mock_get_sub.assert_not_called()
        self.assertIn("Missing submission ID", response_html)

    # ========================================
    # TEST 8: Get Grade Short Answers - Submission Not Found
    # ========================================
    
    @patch("web.grading.get_submission_with_questions", return_value=None)
    def test_get_grade_short_answers_not_found(self, mock_get_sub):
        """Test handling when submission doesn't exist."""
        
        response_html, status_code = get_grade_short_answers(submission_id="nonexistent")
        
        self.assertEqual(status_code, 404, "Should return 404 Not Found")
        mock_get_sub.assert_called_once_with("nonexistent")
        self.assertIn("Submission not found", response_html)


    # ========================================
    # TEST 10: Post Save Grades - Success
    # ========================================
    
    @patch("web.grading.save_short_answer_grades")
    @patch("web.grading.check_grading_locked", return_value=(False, "Open", None))
    @patch("web.grading.get_exam_by_id", return_value=MOCK_EXAM)
    @patch("web.grading.get_submission_with_questions", return_value=MOCK_SUBMISSION_WITH_QUESTIONS)
    def test_post_save_grades_success(
        self, mock_get_sub, mock_get_exam, mock_check_locked, mock_save_grades
    ):
        """Test successful saving of short answer grades."""
        
        response_html, status_code = post_save_short_answer_grades(body=VALID_GRADE_FORM)
        
        self.assertEqual(status_code, 200, "Should return 200 OK")
        mock_get_sub.assert_called()
        mock_save_grades.assert_called_once()
        
        # Verify redirect HTML
        self.assertIn("Grades saved successfully", response_html)
        self.assertIn("Redirecting", response_html)

    # ========================================
    # TEST 11: Post Save Grades - Missing Submission ID
    # ========================================
    
    @patch("web.grading.get_submission_with_questions")
    def test_post_save_grades_missing_id(self, mock_get_sub):
        """Test handling when submission_id is missing from form."""
        
        invalid_form = urlencode({"marks_1": "8"})  # No submission_id
        
        response_html, status_code = post_save_short_answer_grades(body=invalid_form)
        
        self.assertEqual(status_code, 400, "Should return 400 Bad Request")
        mock_get_sub.assert_not_called()
        self.assertIn("Missing submission ID", response_html)

    # ========================================
    # TEST 12: Post Save Grades - Submission Not Found
    # ========================================
    
    @patch("web.grading.get_submission_with_questions", return_value=None)
    def test_post_save_grades_not_found(self, mock_get_sub):
        """Test handling when submission doesn't exist."""
        
        response_html, status_code = post_save_short_answer_grades(body=VALID_GRADE_FORM)
        
        self.assertEqual(status_code, 404, "Should return 404 Not Found")
        mock_get_sub.assert_called_once_with("sub_001")
        self.assertIn("Submission not found", response_html)

    # ========================================
    # TEST 13: Post Save Grades - Locked (Security Check)
    # ========================================
    
    @patch("web.grading.save_short_answer_grades")
    @patch("web.grading.check_grading_locked", return_value=(True, "Deadline expired", None))
    @patch("web.grading.get_exam_by_id", return_value=MOCK_EXAM_LOCKED)
    @patch("web.grading.get_submission_with_questions", return_value=MOCK_SUBMISSION_WITH_QUESTIONS)
    def test_post_save_grades_locked_rejected(
        self, mock_get_sub, mock_get_exam, mock_check_locked, mock_save_grades
    ):
        """Test that saving grades is blocked when deadline has passed."""
        
        response_html, status_code = post_save_short_answer_grades(body=VALID_GRADE_FORM)
        
        self.assertEqual(status_code, 403, "Should return 403 Forbidden")
        mock_save_grades.assert_not_called()  # Should NOT save
        
        self.assertIn("Grading Rejected", response_html)
        self.assertIn("Deadline expired", response_html)

    # ========================================
    # TEST 14: Post Save Grades - Save Error
    # ========================================
    
    @patch("web.grading.save_short_answer_grades", side_effect=Exception("Database error"))
    @patch("web.grading.check_grading_locked", return_value=(False, "Open", None))
    @patch("web.grading.get_exam_by_id", return_value=MOCK_EXAM)
    @patch("web.grading.get_submission_with_questions", return_value=MOCK_SUBMISSION_WITH_QUESTIONS)
    def test_post_save_grades_error(
        self, mock_get_sub, mock_get_exam, mock_check_locked, mock_save_grades
    ):
        """Test error handling when saving grades fails."""
        
        response_html, status_code = post_save_short_answer_grades(body=VALID_GRADE_FORM)
        
        self.assertEqual(status_code, 500, "Should return 500 Internal Server Error")
        self.assertIn("Error saving grades", response_html)
        self.assertIn("Database error", response_html)

    # ========================================
    # TEST 15: Get View Submission Result - Success
    # ========================================
    
    @patch("web.grading.render")
    @patch("web.grading.get_exam_by_id", return_value=MOCK_EXAM)
    @patch("web.grading.get_submission_with_questions", return_value=MOCK_SUBMISSION_WITH_QUESTIONS)
    def test_get_view_submission_result_success(
        self, mock_get_sub, mock_get_exam, mock_render
    ):
        """Test successful viewing of graded submission results."""
        
        mock_render.return_value = "<html>Results View</html>"
        
        response_html, status_code = get_view_submission_result(submission_id="sub_001")
        
        self.assertEqual(status_code, 200, "Should return 200 OK")
        mock_get_sub.assert_called_once_with("sub_001")
        
        render_context = mock_render.call_args[0][1]
        self.assertEqual(render_context["submission_id"], "sub_001")
        self.assertEqual(render_context["student_id"], "S001")
        self.assertIn("scores_html", render_context)
        self.assertIn("mcq_results_html", render_context)
        self.assertIn("sa_results_html", render_context)

    # ========================================
    # TEST 16: Get View Submission Result - Missing ID
    # ========================================
    
    @patch("web.grading.render")
    @patch("web.grading.get_submission_with_questions")
    def test_get_view_submission_result_missing_id(self, mock_get_sub, mock_render):
        """Test handling when submission_id is missing."""
        
        mock_render.return_value = "<html>Error</html>"
        
        response_html, status_code = get_view_submission_result(submission_id=None)
        
        self.assertEqual(status_code, 400, "Should return 400 Bad Request")
        mock_get_sub.assert_not_called()
        
        render_context = mock_render.call_args[0][1]
        self.assertIn("Missing submission ID", render_context["message_html"])

    # ========================================
    # TEST 17: Get View Submission Result - Not Found
    # ========================================
    
    @patch("web.grading.render")
    @patch("web.grading.get_submission_with_questions", return_value=None)
    def test_get_view_submission_result_not_found(self, mock_get_sub, mock_render):
        """Test handling when submission doesn't exist."""
        
        mock_render.return_value = "<html>Error</html>"
        
        response_html, status_code = get_view_submission_result(submission_id="nonexistent")
        
        self.assertEqual(status_code, 404, "Should return 404 Not Found")
        mock_get_sub.assert_called_once_with("nonexistent")
        
        render_context = mock_render.call_args[0][1]
        self.assertIn("Submission not found", render_context["message_html"])

    # ========================================
    # TEST 18: Scores Display in Result View
    # ========================================
    
    @patch("web.grading.render")
    @patch("web.grading.get_exam_by_id", return_value=MOCK_EXAM)
    @patch("web.grading.get_submission_with_questions", return_value=MOCK_SUBMISSION_WITH_QUESTIONS)
    def test_view_result_scores_display(
        self, mock_get_sub, mock_get_exam, mock_render
    ):
        """Test that all score information is correctly displayed."""
        
        mock_render.return_value = "<html>Scores</html>"
        
        response_html, status_code = get_view_submission_result(submission_id="sub_001")
        
        render_context = mock_render.call_args[0][1]
        scores_html = render_context["scores_html"]
        
        # Verify MCQ scores are included
        self.assertIn("40", scores_html)  # mcq_score
        self.assertIn("50", scores_html)  # mcq_total


if __name__ == "__main__":
    unittest.main()