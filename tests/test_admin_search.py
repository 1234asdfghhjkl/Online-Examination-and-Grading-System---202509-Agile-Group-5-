import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add web folder to path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
)

# Import your handler
from admin_routes import get_admin_lecturer_list


class TestAdminLecturerSearch(unittest.TestCase):

    @patch("admin_routes.db")  # Mock Firestore db in admin_routes
    def test_lecturer_list_with_data(self, mock_db):
        # Mock Firestore documents
        mock_docs = [
            MagicMock(
                to_dict=MagicMock(
                    return_value={
                        "lecturer_id": "L001",
                        "name": "Alice Smith",
                        "email": "alice@example.com",
                        "faculty": "Science",
                        "ic": "123456",
                    }
                )
            ),
            MagicMock(
                to_dict=MagicMock(
                    return_value={
                        "lecturer_id": "L002",
                        "name": "Bob Johnson",
                        "email": "bob@example.com",
                        "faculty": "Engineering",
                        "ic": "789012",
                    }
                )
            ),
        ]
        mock_db.collection.return_value.where.return_value.stream.return_value = (
            mock_docs
        )

        response, status = get_admin_lecturer_list()

        self.assertEqual(status, 200)
        self.assertIn("Alice Smith", response)
        self.assertIn("Bob Johnson", response)
        self.assertIn("Deactivate", response)  # Check deactivate button exists

    @patch("admin_routes.db")
    def test_lecturer_list_empty(self, mock_db):
        mock_db.collection.return_value.where.return_value.stream.return_value = []

        response, status = get_admin_lecturer_list()

        self.assertEqual(status, 200)
        self.assertIn("No lecturers found", response)

    @patch("admin_routes.db")
    def test_lecturer_list_sorted_by_id(self, mock_db):
        mock_docs = [
            MagicMock(
                to_dict=MagicMock(
                    return_value={
                        "lecturer_id": "L002",
                        "name": "Bob",
                        "email": "",
                        "faculty": "",
                        "ic": "",
                    }
                )
            ),
            MagicMock(
                to_dict=MagicMock(
                    return_value={
                        "lecturer_id": "L001",
                        "name": "Alice",
                        "email": "",
                        "faculty": "",
                        "ic": "",
                    }
                )
            ),
        ]
        mock_db.collection.return_value.where.return_value.stream.return_value = (
            mock_docs
        )

        response, status = get_admin_lecturer_list()

        self.assertEqual(status, 200)
        # Check L001 comes before L002 in HTML
        first_index = response.find("L001")
        second_index = response.find("L002")
        self.assertLess(first_index, second_index)


if __name__ == "__main__":
    unittest.main()
