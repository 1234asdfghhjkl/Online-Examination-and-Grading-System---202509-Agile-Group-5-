import unittest
from unittest.mock import patch
from urllib.parse import urlencode

# Assuming these functions exist in web/password_routes.py based on your requirements
# If the file is named differently, please adjust the import.
from web.password_routes import get_change_password_page, post_change_password


class ChangePasswordTest(unittest.TestCase):

    # --- GET: View Page ---

    @patch("web.password_routes.render")
    def test_get_change_password_page_success(self, mock_render):
        """Test rendering the change password page with valid user_id."""
        user_id = "123456"
        _, status_code = get_change_password_page(user_id)

        self.assertEqual(status_code, 200)

        # Verify render call
        args, _ = mock_render.call_args
        template_name, context = args
        self.assertEqual(template_name, "change_password.html")
        self.assertEqual(context["user_id"], user_id)

    @patch("web.password_routes.render")
    def test_get_change_password_missing_id(self, mock_render):
        """Test rendering page when user_id is missing (Should error or handle gracefully)."""
        _, status_code = get_change_password_page("")

        # Depending on implementation, might return 400 or render error
        self.assertEqual(status_code, 400)
        args, _ = mock_render.call_args
        _, context = args
        self.assertIn("Error", context["message"])

    # --- POST: Change Password Logic ---

    @patch("web.password_routes.auth.update_user")  # Mock Firebase Auth update
    @patch("web.password_routes.authenticate_user")  # Mock old password verification
    @patch("web.password_routes.render")
    def test_post_change_password_success(
        self, mock_render, mock_auth, mock_update_firebase
    ):
        """Positive Test: Successfully change password."""
        user_id = "student123"
        body = urlencode(
            {
                "old_password": "oldPassword123",
                "new_password": "newPassword123",
                "confirm_password": "newPassword123",
            }
        )

        # Mock successful authentication of old password
        mock_auth.return_value = {"uid": "firebase_uid_123"}

        _, status_code, redirect_url = post_change_password(user_id, body)

        # Check success behavior (usually redirect to login or dashboard)
        self.assertEqual(status_code, 302)
        self.assertEqual(
            redirect_url, "/login"
        )  # Requirement says "Logout user on success"

        # Verify Firebase was updated
        mock_update_firebase.assert_called_once_with(
            uid="firebase_uid_123", password="newPassword123"
        )

    @patch("web.password_routes.render")
    def test_post_change_password_mismatch(self, mock_render):
        """Negative Test: New password and Confirm password do not match."""
        user_id = "student123"
        body = urlencode(
            {
                "old_password": "old",
                "new_password": "newPassword123",
                "confirm_password": "differentPassword",
            }
        )

        _, status_code, _ = post_change_password(user_id, body)

        self.assertEqual(status_code, 400)

        args, _ = mock_render.call_args
        _, context = args
        self.assertIn("Passwords do not match", context["message"])

    @patch("web.password_routes.render")
    def test_post_change_password_too_short(self, mock_render):
        """Negative Test: New password is too short (< 6 chars)."""
        user_id = "student123"
        body = urlencode(
            {"old_password": "old", "new_password": "123", "confirm_password": "123"}
        )

        _, status_code, _ = post_change_password(user_id, body)

        self.assertEqual(status_code, 400)

        args, _ = mock_render.call_args
        _, context = args
        self.assertIn("at least 6 characters", context["message"])

    @patch("web.password_routes.authenticate_user")
    @patch("web.password_routes.render")
    def test_post_change_password_wrong_old_password(self, mock_render, mock_auth):
        """Negative Test: Old password verification fails."""
        user_id = "student123"
        body = urlencode(
            {
                "old_password": "wrongPassword",
                "new_password": "newPassword123",
                "confirm_password": "newPassword123",
            }
        )

        # Mock authentication failure
        mock_auth.side_effect = ValueError("Invalid password.")

        _, status_code, _ = post_change_password(user_id, body)

        self.assertEqual(status_code, 401)  # Unauthorized

        args, _ = mock_render.call_args
        _, context = args
        self.assertIn("Invalid password", context["message"])


if __name__ == "__main__":
    unittest.main()
