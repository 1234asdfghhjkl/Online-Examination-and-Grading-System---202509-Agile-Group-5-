import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add web folder to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web")))

from admin_routes import get_admin_lecturer_list, get_admin_student_list

class TestAdminLecturerSearch(unittest.TestCase):

    # --- LECTURER SEARCH TESTS ---

    @patch("admin_routes.db")
    def test_search_lecturer_by_name(self, mock_db):
        """Positive: Simulate searching for 'Alice' returns Dr. Alice Smith."""
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "lecturer_id": "L001", 
            "name": "Dr. Alice Smith", 
            "email": "alice.smith@university.edu", 
            "faculty": "Engineering"
        }
        # Simulate Firestore finding this lecturer by name
        mock_db.collection.return_value.where.return_value.stream.return_value = [mock_doc]

        response, status = get_admin_lecturer_list()

        self.assertEqual(status, 200)
        self.assertIn("Dr. Alice Smith", response)

    @patch("admin_routes.db")
    def test_search_lecturer_by_id(self, mock_db):
        """Positive: Simulate searching for 'L005' returns Ms. Lolo."""
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "lecturer_id": "L005", 
            "name": "Ms. Lolo", 
            "email": "lolo@university.edu", 
            "faculty": "Accounting"
        }
        # Simulate Firestore finding this lecturer by ID
        mock_db.collection.return_value.where.return_value.stream.return_value = [mock_doc]

        response, status = get_admin_lecturer_list()

        self.assertEqual(status, 200)
        self.assertIn("L005", response)
        self.assertIn("Ms. Lolo", response)

    # --- STUDENT SEARCH TESTS ---

    @patch("admin_routes.db")
    def test_search_student_by_name(self, mock_db):
        """Positive: Simulate searching for 'Chung' returns Chung Li Yi."""
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "student_id": "100000", 
            "name": "Chung Li Yi", 
            "email": "chungly@student.university.edu", 
            "major": "Business Administration"
        }
        # Simulate Firestore finding this student by name
        mock_db.collection.return_value.where.return_value.stream.return_value = [mock_doc]

        response, status = get_admin_student_list()

        self.assertEqual(status, 200)
        self.assertIn("Chung Li Yi", response)

    @patch("admin_routes.db")
    def test_search_student_by_id(self, mock_db):
        """Positive: Simulate searching for '100123' returns John Doe."""
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "student_id": "100123", 
            "name": "John Doe", 
            "email": "john.doe@student.university.edu", 
            "major": "Computer Science"
        }
        # Simulate Firestore finding this student by ID
        mock_db.collection.return_value.where.return_value.stream.return_value = [mock_doc]

        response, status = get_admin_student_list()

        self.assertEqual(status, 200)
        self.assertIn("100123", response)
        self.assertIn("John Doe", response)

if __name__ == "__main__":
    unittest.main()