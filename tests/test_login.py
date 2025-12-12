# tests/test_login.py
import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import urlencode

# Import the functions to test
from web.auth_routes import get_login_page, post_login
from services.auth_service import authenticate_user, get_redirect_url


class TestGetLoginPage(unittest.TestCase):
    """Test cases for GET login page"""

    def test_get_login_page_returns_200(self):
        """Test that login page returns successfully with status 200"""
        html, status = get_login_page()
        
        self.assertEqual(status, 200)
        self.assertIsNotNone(html)
        self.assertIn("login", html.lower())

    def test_get_login_page_contains_form_fields(self):
        """Test that login page contains required form fields"""
        html, status = get_login_page()
        
        self.assertIn('name="user_id"', html)
        self.assertIn('name="password"', html)
        self.assertIn('name="role"', html)

    def test_get_login_page_contains_role_buttons(self):
        """Test that login page contains role selection buttons"""
        html, status = get_login_page()
        
        self.assertIn('student', html.lower())
        self.assertIn('lecturer', html.lower())
        self.assertIn('admin', html.lower())


class TestAuthenticateUser(unittest.TestCase):
    """Test cases for authenticate_user function"""

    # ==================== POSITIVE TEST CASES ====================

    @patch("services.auth_service.requests.post")
    @patch("services.auth_service.db")
    def test_authenticate_student_success(self, mock_db, mock_requests):
        """Test successful student authentication with correct credentials"""
        # Mock Firestore response
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "student@example.com",
            "role": "student",
            "name": "John Doe",
            "student_id": "S001",
            "ic": "990101010101"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        # Mock Firebase Auth REST API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "localId": "firebase_uid_123",
            "email": "student@example.com"
        }
        mock_requests.return_value = mock_response

        # Test authentication
        result = authenticate_user("S001", "990101010101", "student")

        self.assertEqual(result["user_id"], "S001")
        self.assertEqual(result["role"], "student")
        self.assertEqual(result["name"], "John Doe")
        self.assertEqual(result["student_id"], "S001")

    @patch("services.auth_service.requests.post")
    @patch("services.auth_service.db")
    def test_authenticate_lecturer_success(self, mock_db, mock_requests):
        """Test successful lecturer authentication with correct credentials"""
        # Mock Firestore response
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "lecturer@example.com",
            "role": "lecturer",
            "name": "Dr. Smith",
            "lecturer_id": "L001",
            "ic": "800101010101",
            "faculty": "Engineering"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        # Mock Firebase Auth REST API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "localId": "firebase_uid_456",
            "email": "lecturer@example.com"
        }
        mock_requests.return_value = mock_response

        # Test authentication
        result = authenticate_user("L001", "800101010101", "lecturer")

        self.assertEqual(result["user_id"], "L001")
        self.assertEqual(result["role"], "lecturer")
        self.assertEqual(result["name"], "Dr. Smith")
        self.assertEqual(result["lecturer_id"], "L001")

    def test_authenticate_admin_hardcoded_success(self):
        """Test successful admin authentication with hardcoded credentials"""
        # Admin uses hardcoded login, no Firebase call needed
        result = authenticate_user("A001", "010101070101", "admin")

        self.assertEqual(result["uid"], "admin")
        self.assertEqual(result["user_id"], "admin")
        self.assertEqual(result["role"], "admin")
        self.assertEqual(result["name"], "System Administrator")

    @patch("services.auth_service.requests.post")
    @patch("services.auth_service.db")
    def test_authenticate_with_changed_password(self, mock_db, mock_requests):
        """Test authentication with changed password (not IC)"""
        # Mock Firestore response
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "student@example.com",
            "role": "student",
            "name": "John Doe",
            "student_id": "S001",
            "ic": "990101010101"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        # Mock Firebase Auth REST API response with custom password
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "localId": "firebase_uid_123",
            "email": "student@example.com"
        }
        mock_requests.return_value = mock_response

        # Test authentication with custom password
        result = authenticate_user("S001", "MyNewPassword123", "student")

        self.assertEqual(result["user_id"], "S001")
        self.assertEqual(result["role"], "student")

    # ==================== NEGATIVE TEST CASES ====================

    @patch("services.auth_service.db")
    def test_authenticate_user_not_found(self, mock_db):
        """Test authentication fails when user ID doesn't exist"""
        # Mock Firestore response - user not found
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with self.assertRaises(ValueError) as context:
            authenticate_user("S999", "990101010101", "student")

        self.assertIn("User ID not found", str(context.exception))

    @patch("services.auth_service.requests.post")
    @patch("services.auth_service.db")
    def test_authenticate_invalid_password(self, mock_db, mock_requests):
        """Test authentication fails with invalid password"""
        # Mock Firestore response
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "student@example.com",
            "role": "student",
            "name": "John Doe",
            "student_id": "S001",
            "ic": "990101010101"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        # Mock Firebase Auth REST API response - invalid password
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "message": "INVALID_PASSWORD"
            }
        }
        mock_requests.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            authenticate_user("S001", "wrongpassword", "student")

        self.assertIn("Invalid password", str(context.exception))

    @patch("services.auth_service.requests.post")
    @patch("services.auth_service.db")
    def test_authenticate_wrong_role(self, mock_db, mock_requests):
        """Test authentication fails when wrong role is selected"""
        # Mock Firestore response - user is a student
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "student@example.com",
            "role": "student",
            "name": "John Doe",
            "student_id": "S001",
            "ic": "990101010101"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        # User tries to login as lecturer but account is student
        with self.assertRaises(ValueError) as context:
            authenticate_user("S001", "990101010101", "lecturer")

        self.assertIn("Access denied", str(context.exception))
        self.assertIn("student", str(context.exception))

    @patch("services.auth_service.requests.post")
    @patch("services.auth_service.db")
    def test_authenticate_account_disabled(self, mock_db, mock_requests):
        """Test authentication fails when account is disabled"""
        # Mock Firestore response
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "student@example.com",
            "role": "student",
            "name": "John Doe",
            "student_id": "S001",
            "ic": "990101010101"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        # Mock Firebase Auth REST API response - account disabled
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "message": "USER_DISABLED"
            }
        }
        mock_requests.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            authenticate_user("S001", "990101010101", "student")

        self.assertIn("Account disabled", str(context.exception))

    @patch("services.auth_service.requests.post")
    @patch("services.auth_service.db")
    def test_authenticate_email_not_found(self, mock_db, mock_requests):
        """Test authentication fails when email not found in Firebase"""
        # Mock Firestore response
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "student@example.com",
            "role": "student",
            "name": "John Doe",
            "student_id": "S001",
            "ic": "990101010101"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        # Mock Firebase Auth REST API response - email not found
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "message": "EMAIL_NOT_FOUND"
            }
        }
        mock_requests.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            authenticate_user("S001", "990101010101", "student")

        self.assertIn("Account not found", str(context.exception))

    def test_authenticate_admin_wrong_password(self):
        """Test admin authentication fails with wrong password"""
        with self.assertRaises(ValueError):
            authenticate_user("A001", "wrongpassword", "admin")


class TestGetRedirectUrl(unittest.TestCase):
    """Test cases for get_redirect_url function"""

    def test_get_redirect_url_admin(self):
        """Test redirect URL for admin role"""
        user_data = {"user_id": "admin", "role": "admin"}
        url = get_redirect_url("admin", user_data)
        
        self.assertEqual(url, "/admin/exam-list")

    def test_get_redirect_url_lecturer(self):
        """Test redirect URL for lecturer role"""
        user_data = {"lecturer_id": "L001", "role": "lecturer"}
        url = get_redirect_url("lecturer", user_data)
        
        self.assertEqual(url, "/exam-list?lecturer_id=L001")

    def test_get_redirect_url_student(self):
        """Test redirect URL for student role"""
        user_data = {"student_id": "S001", "role": "student"}
        url = get_redirect_url("student", user_data)
        
        self.assertEqual(url, "/student-dashboard?student_id=S001")

    def test_get_redirect_url_unknown_role(self):
        """Test redirect URL for unknown role defaults to home"""
        user_data = {"user_id": "unknown"}
        url = get_redirect_url("unknown", user_data)
        
        self.assertEqual(url, "/")


class TestPostLogin(unittest.TestCase):
    """Test cases for POST login endpoint"""

    # ==================== POSITIVE TEST CASES ====================

    @patch("web.auth_routes.authenticate_user")
    def test_post_login_student_success(self, mock_authenticate):
        """Test successful student login via POST"""
        # Mock successful authentication
        mock_authenticate.return_value = {
            "uid": "firebase_uid_123",
            "user_id": "S001",
            "role": "student",
            "name": "John Doe",
            "student_id": "S001"
        }

        # Create form data
        form_data = urlencode({
            "user_id": "S001",
            "password": "990101010101",
            "role": "student"
        })

        # Test login
        html, status, redirect = post_login(form_data)

        self.assertIsNone(html)
        self.assertEqual(status, 302)
        self.assertEqual(redirect, "/student-dashboard?student_id=S001")

    @patch("web.auth_routes.authenticate_user")
    def test_post_login_lecturer_success(self, mock_authenticate):
        """Test successful lecturer login via POST"""
        # Mock successful authentication
        mock_authenticate.return_value = {
            "uid": "firebase_uid_456",
            "user_id": "L001",
            "role": "lecturer",
            "name": "Dr. Smith",
            "lecturer_id": "L001"
        }

        # Create form data
        form_data = urlencode({
            "user_id": "L001",
            "password": "800101010101",
            "role": "lecturer"
        })

        # Test login
        html, status, redirect = post_login(form_data)

        self.assertIsNone(html)
        self.assertEqual(status, 302)
        self.assertEqual(redirect, "/exam-list?lecturer_id=L001")

    @patch("web.auth_routes.authenticate_user")
    def test_post_login_admin_success(self, mock_authenticate):
        """Test successful admin login via POST"""
        # Mock successful authentication
        mock_authenticate.return_value = {
            "uid": "admin",
            "user_id": "admin",
            "role": "admin",
            "name": "System Administrator"
        }

        # Create form data
        form_data = urlencode({
            "user_id": "A001",
            "password": "010101070101",
            "role": "admin"
        })

        # Test login
        html, status, redirect = post_login(form_data)

        self.assertIsNone(html)
        self.assertEqual(status, 302)
        self.assertEqual(redirect, "/admin/exam-list")

    # ==================== NEGATIVE TEST CASES ====================

    def test_post_login_missing_user_id(self):
        """Test login fails when user_id is missing"""
        form_data = urlencode({
            "user_id": "",
            "password": "990101010101",
            "role": "student"
        })

        html, status, redirect = post_login(form_data)

        self.assertIsNone(redirect)
        self.assertEqual(status, 400)
        self.assertIn("Please enter both User ID and Password", html)

    def test_post_login_missing_password(self):
        """Test login fails when password is missing"""
        form_data = urlencode({
            "user_id": "S001",
            "password": "",
            "role": "student"
        })

        html, status, redirect = post_login(form_data)

        self.assertIsNone(redirect)
        self.assertEqual(status, 400)
        self.assertIn("Please enter both User ID and Password", html)

    def test_post_login_missing_both_fields(self):
        """Test login fails when both fields are missing"""
        form_data = urlencode({
            "user_id": "",
            "password": "",
            "role": "student"
        })

        html, status, redirect = post_login(form_data)

        self.assertIsNone(redirect)
        self.assertEqual(status, 400)
        self.assertIn("Please enter both User ID and Password", html)

    @patch("web.auth_routes.authenticate_user")
    def test_post_login_invalid_credentials(self, mock_authenticate):
        """Test login fails with invalid credentials"""
        # Mock authentication failure
        mock_authenticate.side_effect = ValueError("Invalid password.")

        form_data = urlencode({
            "user_id": "S001",
            "password": "wrongpassword",
            "role": "student"
        })

        html, status, redirect = post_login(form_data)

        self.assertIsNone(redirect)
        self.assertEqual(status, 401)
        self.assertIn("Login Failed", html)
        self.assertIn("Invalid password", html)

    @patch("web.auth_routes.authenticate_user")
    def test_post_login_user_not_found(self, mock_authenticate):
        """Test login fails when user not found"""
        # Mock authentication failure
        mock_authenticate.side_effect = ValueError("User ID not found.")

        form_data = urlencode({
            "user_id": "S999",
            "password": "990101010101",
            "role": "student"
        })

        html, status, redirect = post_login(form_data)

        self.assertIsNone(redirect)
        self.assertEqual(status, 401)
        self.assertIn("Login Failed", html)
        self.assertIn("User ID not found", html)

    @patch("web.auth_routes.authenticate_user")
    def test_post_login_wrong_role(self, mock_authenticate):
        """Test login fails when wrong role is selected"""
        # Mock authentication failure
        mock_authenticate.side_effect = ValueError("Access denied. Please login as student")

        form_data = urlencode({
            "user_id": "S001",
            "password": "990101010101",
            "role": "lecturer"
        })

        html, status, redirect = post_login(form_data)

        self.assertIsNone(redirect)
        self.assertEqual(status, 401)
        self.assertIn("Login Failed", html)
        self.assertIn("Access denied", html)

    @patch("web.auth_routes.authenticate_user")
    def test_post_login_account_disabled(self, mock_authenticate):
        """Test login fails when account is disabled"""
        # Mock authentication failure
        mock_authenticate.side_effect = ValueError("Account disabled.")

        form_data = urlencode({
            "user_id": "S001",
            "password": "990101010101",
            "role": "student"
        })

        html, status, redirect = post_login(form_data)

        self.assertIsNone(redirect)
        self.assertEqual(status, 401)
        self.assertIn("Login Failed", html)
        self.assertIn("Account disabled", html)

    @patch("web.auth_routes.authenticate_user")
    def test_post_login_system_error(self, mock_authenticate):
        """Test login handles unexpected system errors"""
        # Mock unexpected error
        mock_authenticate.side_effect = Exception("Database connection error")

        form_data = urlencode({
            "user_id": "S001",
            "password": "990101010101",
            "role": "student"
        })

        html, status, redirect = post_login(form_data)

        self.assertIsNone(redirect)
        self.assertEqual(status, 500)
        self.assertIn("System Error", html)

    def test_post_login_preserves_user_id_on_error(self):
        """Test that user_id is preserved in form when login fails"""
        form_data = urlencode({
            "user_id": "S001",
            "password": "",
            "role": "student"
        })

        html, status, redirect = post_login(form_data)

        self.assertIn("S001", html)
        self.assertIn('value="S001"', html)


class TestLoginIntegration(unittest.TestCase):
    """Integration tests for complete login flow"""

    @patch("services.auth_service.requests.post")
    @patch("services.auth_service.db")
    def test_complete_student_login_flow(self, mock_db, mock_requests):
        """Test complete student login flow from form submission to redirect"""
        # Mock Firestore
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "student@example.com",
            "role": "student",
            "name": "John Doe",
            "student_id": "S001",
            "ic": "990101010101"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        # Mock Firebase Auth
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "localId": "firebase_uid_123",
            "email": "student@example.com"
        }
        mock_requests.return_value = mock_response

        # Submit login form
        form_data = urlencode({
            "user_id": "S001",
            "password": "990101010101",
            "role": "student"
        })

        html, status, redirect = post_login(form_data)

        # Verify successful login
        self.assertEqual(status, 302)
        self.assertIsNone(html)
        self.assertEqual(redirect, "/student-dashboard?student_id=S001")

    @patch("services.auth_service.requests.post")
    @patch("services.auth_service.db")
    def test_complete_lecturer_login_flow(self, mock_db, mock_requests):
        """Test complete lecturer login flow from form submission to redirect"""
        # Mock Firestore
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "lecturer@example.com",
            "role": "lecturer",
            "name": "Dr. Smith",
            "lecturer_id": "L001",
            "ic": "800101010101"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        # Mock Firebase Auth
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "localId": "firebase_uid_456",
            "email": "lecturer@example.com"
        }
        mock_requests.return_value = mock_response

        # Submit login form
        form_data = urlencode({
            "user_id": "L001",
            "password": "800101010101",
            "role": "lecturer"
        })

        html, status, redirect = post_login(form_data)

        # Verify successful login
        self.assertEqual(status, 302)
        self.assertIsNone(html)
        self.assertEqual(redirect, "/exam-list?lecturer_id=L001")

    def test_complete_admin_login_flow(self):
        """Test complete admin login flow (hardcoded credentials)"""
        # Submit login form
        form_data = urlencode({
            "user_id": "A001",
            "password": "010101070101",
            "role": "admin"
        })

        html, status, redirect = post_login(form_data)

        # Verify successful login
        self.assertEqual(status, 302)
        self.assertIsNone(html)
        self.assertEqual(redirect, "/admin/exam-list")


if __name__ == "__main__":
    unittest.main()