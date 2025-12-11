# web/profile_routes.py

from typing import Tuple
from web.template_engine import render
# FIX 1: Import module instead of function so patching works
import services.user_service as user_service


# Helper function to infer the user role from the ID structure
def infer_user_role(user_id: str) -> str:
    """Infers role based on ID convention (L for Lecturer, A for Admin, else Student)."""
    if not user_id: 
        return "Student"
    if user_id.upper().startswith("L"):
        return "Lecturer"
    elif user_id.upper().startswith("A"):
        return "Admin"
    else:
        return "Student"


def get_profile_page(user_id: str) -> Tuple[str, int]:
    """
    Handles the GET request for the /profile page, fetching data and rendering the view.
    """
    # FIX 2: Return 400 if user_id is missing (Required by tests)
    if not user_id:
        context = {
            "page_title": "Profile Error",
            "user_id": "",
            "user_role": "Unknown",
            "profile_data_html": "",
            "error_message": "Error: Missing user ID",
            "error_display_style": "block",
            "dashboard_url": "/login",
        }
        return render("profile.html", context), 400

    # FIX 1: Use module path for function call
    profile_data = user_service.get_user_profile(user_id)
    user_role = infer_user_role(user_id)

    # Determine the correct dashboard URL based on role
    if user_role == "Student":
        dashboard_url = f"/student-dashboard?student_id={user_id}"
    elif user_role == "Lecturer":
        dashboard_url = "/exam-list"
    elif user_role == "Admin":
        dashboard_url = "/admin/exam-list"
    else:
        dashboard_url = "/login"

    context = {
        "page_title": f"{user_role} Profile",
        "user_id": user_id,
        "user_role": user_role,
        "profile_data_html": "",  
        "error_message": "",
        "error_display_style": "none",
        "dashboard_url": dashboard_url,
    }

    if not profile_data:
        context["error_message"] = (
            f"User not found: {user_id}"
        )
        context["error_display_style"] = "block"
        return render("profile.html", context), 404

    # 1. Define fields based on role
    fields = []

    if user_role == "Student":
        fields = [
            ("Student ID", profile_data.get("student_id", user_id)),
            ("Name", profile_data.get("name")),
            ("Course / Major", profile_data.get("major")),
            ("Year", profile_data.get("year")),
            ("Semester", profile_data.get("semester")),
            ("Email", profile_data.get("email")),
            ("IC Number", profile_data.get("ic")),
        ]

    elif user_role == "Lecturer":
        fields = [
            ("Lecturer ID", profile_data.get("lecturer_id", user_id)),
            ("Name", profile_data.get("name")),
            ("Faculty", profile_data.get("faculty")),
            ("Email", profile_data.get("email")),
            ("Contact", profile_data.get("email")), # Assuming contact is same as email or separate field
            ("IC Number", profile_data.get("ic")),
        ]

    elif user_role == "Admin":
        fields = [
            ("Admin ID", profile_data.get("admin_id", user_id)),
            ("Name", profile_data.get("name")),
            ("Email", profile_data.get("email")),
            ("Role", "System Administrator"),
        ]

    # 2. Build the read-only HTML fields
    profile_html = ""
    for label, value in fields:
        # Handle None or empty strings gracefully
        display_val = str(value) if value is not None and str(value).strip() != "" else "N/A"
        
        profile_html += f"""
        <div class="row mb-3 border-bottom pb-2">
            <div class="col-sm-4 text-muted">{label}</div>
            <div class="col-sm-8 fw-bold">{display_val}</div>
        </div>
        """

    context["profile_data_html"] = profile_html

    return render("profile.html", context), 200