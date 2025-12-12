# tests/test_filter_student_exam_integration.py
"""
Integration tests for student filter system with actual workflow simulation
"""
import unittest
from unittest.mock import patch, MagicMock


class TestFilterCompleteWorkflows(unittest.TestCase):
    """Test complete user workflows involving filters"""

    @patch("services.student_filter_service.db")
    def test_lecturer_creates_exam_with_filters(self, mock_db):
        """Test: Lecturer creates exam and sets student filters"""
        from services.student_filter_service import save_exam_filters, get_exam_filters
        
        # Mock exam exists
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value.exists = True
        mock_doc_ref.get.return_value.to_dict.return_value = {
            "student_filters": {
                "years": ["1", "2"],
                "majors": ["Computer Science"],
                "semesters": ["1"],
            }
        }
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        # Lecturer sets filters
        filters = {
            "years": ["1", "2"],
            "majors": ["Computer Science"],
            "semesters": ["1"],
        }
        
        save_exam_filters("EID-001", filters)
        
        # Verify filters were saved
        retrieved = get_exam_filters("EID-001")
        self.assertEqual(retrieved["years"], ["1", "2"])
        self.assertEqual(retrieved["majors"], ["Computer Science"])

    @patch("services.student_filter_service.get_exam_filters")
    @patch("services.student_filter_service.db")
    def test_student_dashboard_shows_eligible_exams(self, mock_db, mock_get_filters):
        """Test: Student dashboard only shows exams they're eligible for"""
        from services.student_filter_service import is_student_eligible
        
        # Exam has filters
        mock_get_filters.return_value = {
            "years": ["1"],
            "majors": ["Computer Science"],
            "semesters": ["1"],
        }

        # Student matches filters
        mock_student = MagicMock()
        mock_student.to_dict.return_value = {
            "year": 1,
            "major": "Computer Science",
            "semester": 1,
        }
        
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [
            mock_student
        ]

        # Check eligibility
        is_eligible = is_student_eligible("S001", "EID-001")
        
        self.assertTrue(is_eligible)

    @patch("services.student_filter_service.db")
    def test_admin_views_exam_filter_summary(self, mock_db):
        """Test: Admin can view which students are targeted by exam"""
        from services.student_filter_service import get_filter_summary, get_exam_filters
        
        # Mock exam with filters
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "student_filters": {
                "years": ["1"],
                "majors": ["Computer Science"],
                "semesters": ["1", "2"],
            }
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        # Get filter summary
        filters = get_exam_filters("EID-001")
        summary = get_filter_summary(filters)
        
        self.assertIn("Year 1", summary)
        self.assertIn("Computer Science", summary)
        self.assertIn("Semester 1, 2", summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)