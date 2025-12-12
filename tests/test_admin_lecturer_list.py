import unittest
from unittest.mock import patch, MagicMock
from web.admin_routes import get_admin_lecturer_list


class AdminLecturerListTest(unittest.TestCase):

    @patch("web.admin_routes.render")
    @patch("web.admin_routes.db.collection")
    def test_get_lecturer_list_success(self, mock_collection, mock_render):
        """Positive Test: Admin views list with multiple lecturers populated."""

        # 1. Mock the Firestore data
        mock_lecturer_1 = MagicMock()
        mock_lecturer_1.to_dict.return_value = {
            "lecturer_id": "L001",
            "name": "Alice Smith",
            "email": "alice@example.com",
            "faculty": "Science",
            "ic": "123456",
        }

        mock_lecturer_2 = MagicMock()
        mock_lecturer_2.to_dict.return_value = {
            "lecturer_id": "L002",
            "name": "Bob Johnson",
            "email": "bob@example.com",
            "faculty": "Engineering",
            "ic": "789012",
        }

        # 2. Setup the chain: db.collection().where().stream()
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_lecturer_1, mock_lecturer_2]

        mock_where = MagicMock()
        mock_where.where.return_value = mock_query
        mock_collection.return_value = mock_where

        # 3. Call the function
        html_str, status_code = get_admin_lecturer_list()

        # 4. Assertions
        self.assertEqual(status_code, 200)

        # Verify render context
        args, _ = mock_render.call_args
        template, context = args

        self.assertEqual(template, "admin_lecturer_list.html")
        self.assertEqual(context["total_count"], 2)

        # Check if lecturer data is present in HTML
        self.assertIn("L001", context["lecturer_rows_html"])
        self.assertIn("Alice Smith", context["lecturer_rows_html"])
        self.assertIn("L002", context["lecturer_rows_html"])
        self.assertIn("Bob Johnson", context["lecturer_rows_html"])

        # Check if Deactivate button exists
        self.assertIn("Deactivate", context["lecturer_rows_html"])

    @patch("web.admin_routes.render")
    @patch("web.admin_routes.db.collection")
    def test_get_lecturer_list_empty(self, mock_collection, mock_render):
        """Positive Test: Admin views list but database has no lecturers."""

        # Mock empty stream
        mock_query = MagicMock()
        mock_query.stream.return_value = []

        mock_where = MagicMock()
        mock_where.where.return_value = mock_query
        mock_collection.return_value = mock_where

        _, status_code = get_admin_lecturer_list()

        self.assertEqual(status_code, 200)

        args, _ = mock_render.call_args
        _, context = args

        self.assertEqual(context["total_count"], 0)
        self.assertIn("No lecturers found", context["lecturer_rows_html"])

    @patch("web.admin_routes.db.collection")
    def test_get_lecturer_list_db_error(self, mock_collection):
        """Negative Test: Database connection fails (Exception handling)."""

        # Simulate an exception when accessing DB
        mock_collection.side_effect = Exception("Firebase unreachable")

        response, status_code = get_admin_lecturer_list()

        self.assertEqual(status_code, 500)
        self.assertIn("Error Fetching Lecturers", response)
        self.assertIn("Firebase unreachable", response)


if __name__ == "__main__":
    unittest.main()
