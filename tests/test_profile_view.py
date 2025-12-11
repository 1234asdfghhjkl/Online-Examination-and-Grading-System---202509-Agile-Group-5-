import unittest
from unittest.mock import patch

# Assuming this exists based on your 'profile.html' and 'server.py' references
from web.profile_routes import get_profile_page


class ProfileViewTest(unittest.TestCase):

    @patch("web.profile_routes.render")
    @patch("services.user_service.get_user_profile")
    def test_get_student_profile_success(self, mock_get_profile, mock_render):
        """Positive Test: Student views their own profile successfully."""
        user_id = "112233"

        # Mock DB response for a student
        mock_get_profile.return_value = {
            "name": "John Doe",
            "email": "john@student.com",
            "role": "student",
            "student_id": "112233",
            "major": "Computer Science",
            "year": 2,
            "semester": 1,
        }

        _, status_code = get_profile_page(user_id)

        self.assertEqual(status_code, 200)

        # Verify HTML Context
        args, _ = mock_render.call_args
        template, context = args

        self.assertEqual(template, "profile.html")
        self.assertEqual(context["user_role"], "Student")
        self.assertIn("John Doe", context["profile_data_html"])
        self.assertIn(
            "Computer Science", context["profile_data_html"]
        )  # Specific student field

    @patch("web.profile_routes.render")
    @patch("services.user_service.get_user_profile")
    def test_get_lecturer_profile_success(self, mock_get_profile, mock_render):
        """Positive Test: Lecturer views their own profile successfully."""
        user_id = "L999"

        # Mock DB response for a lecturer
        mock_get_profile.return_value = {
            "name": "Dr. Smith",
            "email": "smith@uni.com",
            "role": "lecturer",
            "lecturer_id": "L999",
            "faculty": "Engineering",
        }

        _, status_code = get_profile_page(user_id)

        self.assertEqual(status_code, 200)

        args, _ = mock_render.call_args
        _, context = args

        self.assertEqual(context["user_role"], "Lecturer")
        self.assertIn("Dr. Smith", context["profile_data_html"])
        self.assertIn(
            "Engineering", context["profile_data_html"]
        )  # Specific lecturer field

    @patch("web.profile_routes.render")
    @patch("services.user_service.get_user_profile")
    def test_get_profile_user_not_found(self, mock_get_profile, mock_render):
        """Negative Test: User ID does not exist in database."""
        user_id = "ghost_user"
        mock_get_profile.return_value = None  # Simulate not found

        _, status_code = get_profile_page(user_id)

        # Should typically return 404 or show error on page
        self.assertEqual(status_code, 404)

        args, _ = mock_render.call_args
        _, context = args
        self.assertIn("User not found", context["error_message"])

    @patch("web.profile_routes.render")
    def test_get_profile_missing_param(self, mock_render):
        """Negative Test: URL called without user_id."""
        _, status_code = get_profile_page("")  # Empty string

        self.assertEqual(status_code, 400)

        args, _ = mock_render.call_args
        _, context = args
        self.assertIn("Missing user ID", context["error_message"])


if __name__ == "__main__":
    unittest.main()
