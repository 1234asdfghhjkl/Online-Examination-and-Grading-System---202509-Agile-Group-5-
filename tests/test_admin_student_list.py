import unittest
from unittest.mock import patch, MagicMock
from web.admin_routes import get_admin_student_list


class AdminStudentListTest(unittest.TestCase):

    @patch("web.admin_routes.render")
    @patch("web.admin_routes.db.collection")
    def test_get_student_list_success(self, mock_collection, mock_render):
        """Positive Test: Admin views list with multiple students populated."""

        # 1. Mock the Firestore data
        mock_student_1 = MagicMock()
        mock_student_1.to_dict.return_value = {
            "student_id": "S101",
            "name": "Alice",
            "email": "alice@test.com",
            "major": "CS",
            "year": 1,
            "semester": 1,
            "ic": "001",
        }

        mock_student_2 = MagicMock()
        mock_student_2.to_dict.return_value = {
            "student_id": "S102",
            "name": "Bob",
            "email": "bob@test.com",
            "major": "IT",
            "year": 2,
            "semester": 2,
            "ic": "002",
        }

        # 2. Setup the chain: db.collection().where().stream()
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_student_1, mock_student_2]

        mock_where = MagicMock()
        mock_where.where.return_value = mock_query

        mock_collection.return_value = mock_where

        # 3. Call the function
        html_str, status_code = get_admin_student_list()

        # 4. Assertions
        self.assertEqual(status_code, 200)

        # Verify render context
        args, _ = mock_render.call_args
        template, context = args

        self.assertEqual(template, "admin_student_list.html")
        self.assertEqual(context["total_count"], 2)

        # Check if student data is present in HTML
        self.assertIn("S101", context["student_rows_html"])
        self.assertIn("Alice", context["student_rows_html"])
        self.assertIn("Bob", context["student_rows_html"])

    @patch("web.admin_routes.render")
    @patch("web.admin_routes.db.collection")
    def test_get_student_list_empty(self, mock_collection, mock_render):
        """Positive Test: Admin views list but database has no students."""

        # Mock empty stream
        mock_query = MagicMock()
        mock_query.stream.return_value = []  # Empty list

        mock_where = MagicMock()
        mock_where.where.return_value = mock_query
        mock_collection.return_value = mock_where

        _, status_code = get_admin_student_list()

        self.assertEqual(status_code, 200)

        args, _ = mock_render.call_args
        _, context = args

        self.assertEqual(context["total_count"], 0)
        self.assertIn("No students found", context["student_rows_html"])

    @patch("web.admin_routes.db.collection")
    def test_get_student_list_db_error(self, mock_collection):
        """Negative Test: Database connection fails (Exception handling)."""

        # Simulate an exception when accessing DB
        mock_collection.side_effect = Exception("Firebase unreachable")

        response, status_code = get_admin_student_list()

        self.assertEqual(status_code, 500)
        self.assertIn("Error Fetching Students", response)
        self.assertIn("Firebase unreachable", response)


if __name__ == "__main__":
    unittest.main()
