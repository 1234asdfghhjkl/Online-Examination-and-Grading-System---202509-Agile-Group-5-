# tests/test_admin_report.py
import unittest
from unittest.mock import patch

# Import the function to test
from web.admin_performance_routes import get_performance_report

# Mock data for successful report generation
MOCK_SUCCESSFUL_REPORT = {
    "exam": {
        "title": "Midterm Exam 2024",
        "exam_date": "2024-03-15",
        "id": "test_exam_123"
    },
    "total_students": 25,
    "submissions_count": 25,
    "overall_stats": {
        "average_percentage": 75.5,
        "average_marks": 75.5,
        "total_possible_marks": 100,
        "highest_score": 95.0,
        "lowest_score": 45.0,
        "median_score": 76.0,
        "standard_deviation": 12.3,
        "passed_count": 20,
        "failed_count": 5,
        "pass_rate": 80.0
    },
    "mcq_stats": {
        "average_score": 38.5,
        "average_percentage": 77.0,
        "highest_score": 48,
        "lowest_score": 25,
        "total_marks": 50
    },
    "sa_stats": {
        "has_short_answers": True,
        "average_score": 37.0,
        "average_percentage": 74.0,
        "highest_score": 48,
        "lowest_score": 20,
        "total_marks": 50
    },
    "grade_distribution": {
        "A": {"count": 5, "range": "80-100%", "students": ["S001", "S002"]},
        "B": {"count": 8, "range": "70-79%", "students": ["S003", "S004"]},
        "C": {"count": 7, "range": "60-69%", "students": ["S005", "S006"]},
        "D": {"count": 3, "range": "50-59%", "students": ["S007"]},
        "F": {"count": 2, "range": "0-49%", "students": ["S008"]}
    },
    "top_performers": [
        {
            "student_id": "S001",
            "percentage": 95.0,
            "total_marks": 95,
            "mcq_score": 48,
            "sa_score": 47
        },
        {
            "student_id": "S002",
            "percentage": 92.0,
            "total_marks": 92,
            "mcq_score": 46,
            "sa_score": 46
        }
    ],
    "students_at_risk": [
        {
            "student_id": "S008",
            "percentage": 45.0,
            "total_marks": 45,
            "areas_of_concern": ["MCQ: 40.0%", "Short Answers: 42.0%"]
        }
    ]
}

# Mock data for no submissions case
MOCK_NO_SUBMISSIONS_REPORT = {
    "exam": {
        "title": "Final Exam 2024",
        "exam_date": "2024-06-20",
        "id": "test_exam_456"
    },
    "total_students": 0,
    "submissions_count": 0,
    "error": "No submissions found for this exam"
}


class AdminPerformanceReportTest(unittest.TestCase):

    # --- Test 1: Success Case ---
    
    @patch("web.admin_performance_routes.render")
    @patch("web.admin_performance_routes.get_exam_performance_report", return_value=MOCK_SUCCESSFUL_REPORT)
    def test_performance_report_success(self, mock_get_report, mock_render):
        """Test successful generation of performance report with submissions."""
        
        mock_render.return_value = "<html>Performance Report</html>"
        
        response_html, status_code = get_performance_report(exam_id="test_exam_123")
        
        self.assertEqual(status_code, 200, "Should return 200 OK on success")
        mock_get_report.assert_called_once_with("test_exam_123")
        mock_render.assert_called_once()
        
        # Verify context passed to render contains expected keys
        render_context = mock_render.call_args[0][1]
        self.assertEqual(render_context["exam_id"], "test_exam_123")
        self.assertEqual(render_context["exam_title"], "Midterm Exam 2024")
        self.assertEqual(render_context["total_students"], 25)
        self.assertEqual(render_context["avg_percentage"], 75.5)
        self.assertEqual(render_context["pass_rate"], 80.0)
        self.assertEqual(render_context["passed_count"], 20)
        self.assertEqual(render_context["failed_count"], 5)

    # --- Test 2: Missing Exam ID ---
    
    @patch("web.admin_performance_routes.get_exam_performance_report")
    def test_performance_report_missing_exam_id(self, mock_get_report):
        """Test handling of missing exam_id parameter."""
        
        response_html, status_code = get_performance_report(exam_id=None)
        
        self.assertEqual(status_code, 400, "Should return 400 Bad Request for missing exam_id")
        mock_get_report.assert_not_called()
        self.assertIn("Missing exam ID", response_html)
        self.assertIn("alert-danger", response_html)

    # --- Test 3: Empty Exam ID ---
    
    @patch("web.admin_performance_routes.get_exam_performance_report")
    def test_performance_report_empty_exam_id(self, mock_get_report):
        """Test handling of empty string exam_id."""
        
        response_html, status_code = get_performance_report(exam_id="")
        
        self.assertEqual(status_code, 400, "Should return 400 Bad Request for empty exam_id")
        mock_get_report.assert_not_called()
        self.assertIn("Missing exam ID", response_html)

    # --- Test 4: Exam Not Found ---
    
    @patch("web.admin_performance_routes.get_exam_performance_report", return_value=None)
    def test_performance_report_exam_not_found(self, mock_get_report):
        """Test handling when exam is not found."""
        
        response_html, status_code = get_performance_report(exam_id="nonexistent_exam")
        
        self.assertEqual(status_code, 404, "Should return 404 Not Found when exam doesn't exist")
        mock_get_report.assert_called_once_with("nonexistent_exam")
        self.assertIn("Could not generate performance report", response_html)
        self.assertIn("alert-danger", response_html)

    # --- Test 5: No Submissions Case ---
    
    @patch("web.admin_performance_routes.get_exam_performance_report", return_value=MOCK_NO_SUBMISSIONS_REPORT)
    def test_performance_report_no_submissions(self, mock_get_report):
        """Test handling when exam exists but has no submissions."""
        
        response_html, status_code = get_performance_report(exam_id="test_exam_456")
        
        self.assertEqual(status_code, 200, "Should return 200 OK even with no submissions")
        mock_get_report.assert_called_once_with("test_exam_456")
        
        # Verify special no-submissions UI is rendered
        self.assertIn("No Submissions Yet", response_html)
        self.assertIn("Final Exam 2024", response_html)
        self.assertIn("2024-06-20", response_html)
        self.assertIn("alert-info", response_html)

    # --- Test 6: Chart Data JSON Format ---
    
    @patch("web.admin_performance_routes.render")
    @patch("web.admin_performance_routes.get_exam_performance_report", return_value=MOCK_SUCCESSFUL_REPORT)
    def test_performance_report_chart_data_format(self, mock_get_report, mock_render):
        """Test that chart data is properly formatted as JSON strings."""
        
        mock_render.return_value = "<html>Chart Data</html>"
        
        response_html, status_code = get_performance_report(exam_id="test_exam_123")
        
        render_context = mock_render.call_args[0][1]
        
        # Verify JSON fields exist
        self.assertIn("grade_labels_json", render_context)
        self.assertIn("grade_counts_json", render_context)
        self.assertIn("grade_colors_json", render_context)
        
        # Verify they are strings (JSON format)
        self.assertIsInstance(render_context["grade_labels_json"], str)
        self.assertIsInstance(render_context["grade_counts_json"], str)
        self.assertIsInstance(render_context["grade_colors_json"], str)

    # --- Test 7: Top Performers HTML Generation ---
    
    @patch("web.admin_performance_routes.render")
    @patch("web.admin_performance_routes.get_exam_performance_report", return_value=MOCK_SUCCESSFUL_REPORT)
    def test_performance_report_top_performers_html(self, mock_get_report, mock_render):
        """Test that top performers HTML is generated correctly."""
        
        mock_render.return_value = "<html>Top Performers</html>"
        
        response_html, status_code = get_performance_report(exam_id="test_exam_123")
        
        render_context = mock_render.call_args[0][1]
        
        # Verify top performers HTML exists and contains expected data
        self.assertIn("top_performers_html", render_context)
        top_performers_html = render_context["top_performers_html"]
        
        self.assertIn("S001", top_performers_html)
        self.assertIn("95.0%", top_performers_html)
        self.assertIn("🥇", top_performers_html)  # Gold medal for first place

    # --- Test 8: At-Risk Students HTML Generation ---
    
    @patch("web.admin_performance_routes.render")
    @patch("web.admin_performance_routes.get_exam_performance_report", return_value=MOCK_SUCCESSFUL_REPORT)
    def test_performance_report_at_risk_html(self, mock_get_report, mock_render):
        """Test that at-risk students HTML is generated correctly."""
        
        mock_render.return_value = "<html>At Risk Students</html>"
        
        response_html, status_code = get_performance_report(exam_id="test_exam_123")
        
        render_context = mock_render.call_args[0][1]
        
        # Verify at-risk HTML exists and contains expected data
        self.assertIn("at_risk_html", render_context)
        at_risk_html = render_context["at_risk_html"]
        
        self.assertIn("S008", at_risk_html)
        self.assertIn("45.0%", at_risk_html)
        self.assertIn("bg-danger", at_risk_html)  # Bootstrap 5 class name

    # --- Test 9: MCQ and SA Stats Display ---
    
    @patch("web.admin_performance_routes.render")
    @patch("web.admin_performance_routes.get_exam_performance_report", return_value=MOCK_SUCCESSFUL_REPORT)
    def test_performance_report_mcq_sa_stats(self, mock_get_report, mock_render):
        """Test that MCQ and Short Answer statistics are correctly passed to template."""
        
        mock_render.return_value = "<html>Stats</html>"
        
        response_html, status_code = get_performance_report(exam_id="test_exam_123")
        
        render_context = mock_render.call_args[0][1]
        
        # MCQ stats
        self.assertEqual(render_context["mcq_avg_score"], 38.5)
        self.assertEqual(render_context["mcq_avg_percentage"], 77.0)
        self.assertEqual(render_context["mcq_total"], 50)
        
        # SA stats
        self.assertEqual(render_context["sa_avg_score"], 37.0)
        self.assertEqual(render_context["sa_avg_percentage"], 74.0)
        self.assertEqual(render_context["sa_total"], 50)

    # --- Test 10: No Short Answers Case ---
    
    @patch("web.admin_performance_routes.render")
    @patch("web.admin_performance_routes.get_exam_performance_report")
    def test_performance_report_no_short_answers(self, mock_get_report, mock_render):
        """Test handling when exam has no short answer questions."""
        
        # Create a report with no short answers
        report_no_sa = MOCK_SUCCESSFUL_REPORT.copy()
        report_no_sa["sa_stats"] = {
            "has_short_answers": False,
            "average_score": 0,
            "average_percentage": 0
        }
        mock_get_report.return_value = report_no_sa
        mock_render.return_value = "<html>No SA</html>"
        
        response_html, status_code = get_performance_report(exam_id="test_exam_123")
        
        render_context = mock_render.call_args[0][1]
        
        # Verify SA stats show N/A
        self.assertEqual(render_context["sa_avg_score"], "N/A")
        self.assertEqual(render_context["sa_avg_percentage"], "N/A")
        self.assertEqual(render_context["sa_total"], "N/A")


if __name__ == "__main__":
    unittest.main()