# web/password_routes.py
from urllib.parse import parse_qs
from typing import Tuple
import html
from web.template_engine import render
from firebase_admin import auth, exceptions

# FIX: Import authentication service
from services.auth_service import authenticate_user


def get_change_password_page(user_id: str) -> Tuple[str, int]:
    """Renders the Change Password form."""

    # FIX: Return 400 if ID is missing (Required by tests)
    if not user_id:
        context = {
            "user_id": "",
            "message": "Error: Missing user ID",
            "msg_type": "danger",
            "msg_display": "block",
            "back_link": "/login",
            "old_password": "",
            "new_password": "",
            "confirm_password": "",
        }
        return render("change_password.html", context), 400

    # Determine back link based on user_id convention
    if user_id.upper().startswith("L"):
        back_link = "/exam-list"
    elif user_id.upper().startswith("A"):
        back_link = "/admin/exam-list"
    else:
        # Student dashboard needs the student_id query param
        back_link = f"/student-dashboard?student_id={user_id}"

    context = {
        "user_id": user_id,
        "message": "",
        "msg_type": "danger",
        "msg_display": "none",
        "back_link": back_link,
        "old_password": "",
        "new_password": "",
        "confirm_password": "",
    }
    return render("change_password.html", context), 200


def post_change_password(user_id: str, body: str) -> Tuple[str | None, int, str | None]:
    """
    Validates input and updates the password in Firebase Auth.
    """
    # Parse form data
    data = parse_qs(body)
    old_password = data.get("old_password", [""])[0].strip()
    new_password = data.get("new_password", [""])[0].strip()
    confirm_password = data.get("confirm_password", [""])[0].strip()

    # Determine back link
    if user_id.upper().startswith("L"):
        back_link = "/exam-list"
    elif user_id.upper().startswith("A"):
        back_link = "/admin/exam-list"
    else:
        back_link = f"/student-dashboard?student_id={user_id}"

    # Context for re-rendering form on error
    context = {
        "user_id": user_id,
        "message": "",
        "msg_type": "danger",
        "msg_display": "block",
        "back_link": back_link,
        "old_password": html.escape(old_password),
        "new_password": "",  # Clear passwords on re-render for security
        "confirm_password": "",
    }

    # 1. Validation
    if not new_password or not confirm_password:
        context["message"] = "Please fill in all new password fields."
        return render("change_password.html", context), 400, None

    if new_password != confirm_password:
        # Matches "Passwords do not match" check in tests
        context["message"] = "Passwords do not match."
        return render("change_password.html", context), 400, None

    if len(new_password) < 6:
        context["message"] = "Password must be at least 6 characters long."
        return render("change_password.html", context), 400, None

    # 2. Authenticate Old Password (Security Check)
    try:
        # Determine role for auth check
        role = "student"
        if user_id.upper().startswith("L"):
            role = "lecturer"
        if user_id.upper().startswith("A"):
            role = "admin"

        # Verify credentials
        user_data = authenticate_user(user_id, old_password, role)
        firebase_uid = user_data.get("uid")

        # 3. Update Firebase
        # Update the user's password in Firebase Auth
        auth.update_user(uid=firebase_uid, password=new_password)

        # 4. Success
        context["msg_type"] = "success"
        context["message"] = (
            "Password updated successfully! You must log in again. Redirecting..."
        )

        # Render a success page that redirects to login after 2 seconds
        success_html = render("change_password.html", context)
        success_html = success_html.replace(
            "</head>", '<meta http-equiv="refresh" content="2;url=/login"></head>'
        )

        return success_html, 302, "/login"

    except ValueError as e:
        # Invalid old password
        context["message"] = str(e)
        return render("change_password.html", context), 401, None

    except exceptions.FirebaseError as e:
        error_msg = str(e)
        if "USER_NOT_FOUND" in error_msg:
            context["message"] = "Error: User ID not found in the system."
        else:
            context["message"] = f"An unexpected error occurred: {error_msg}"

        return render("change_password.html", context), 500, None
