# web/profile_routes.py

from typing import Tuple
from web.template_engine import render
from services.user_service import get_user_profile


# Helper function to infer the user role from the ID structure
def infer_user_role(user_id: str) -> str:
    """Infers role based on ID convention (L for Lecturer, A for Admin, else Student)."""
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
    profile_data = get_user_profile(user_id)
    user_role = infer_user_role(user_id)

    # Determine the correct dashboard URL based on role
    if user_role == "Student":
        dashboard_url = f"/student-dashboard?student_id={user_id}"
    elif user_role == "Lecturer":
        # Lecturer dashboard is the exam list
        dashboard_url = "/exam-list"
    elif user_role == "Admin":
        dashboard_url = "/admin/exam-list"
    else:
        # Fallback
        dashboard_url = "/login"

    context = {
        "page_title": f"{user_role} Profile",
        "user_id": user_id,
        "user_role": user_role,
        "profile_data_html": "",  # Raw HTML content for fields
        "error_message": "",
        "error_display_style": "none",
        "dashboard_url": dashboard_url,  # Pass the dynamic URL to the template
    }

    if not profile_data:
        context["error_message"] = (
            f"Profile for {user_id} not found. Please ensure you are logged in correctly."
        )
        context["error_display_style"] = "block"
        return render("profile.html", context), 404

    # 1. Define fields based on role
    fields = []

    if user_role == "Student":
        fields = [
            ("Student ID", profile_data.get("student_id", user_id)),
            ("Name", profile_data.get("name", "N/A")),
            ("Course / Major", profile_data.get("major", "N/A")),
            ("Year", profile_data.get("year", "N/A")),
            ("Semester", profile_data.get("semester", "N/A")),
            ("Email", profile_data.get("email", "N/A")),
            ("IC Number", profile_data.get("ic", "N/A")),
        ]

    elif user_role == "Lecturer":
        fields = [
            ("Lecturer ID", profile_data.get("lecturer_id", user_id)),
            ("Name", profile_data.get("name", "N/A")),
            ("Faculty", profile_data.get("faculty", "N/A")),
            ("Email", profile_data.get("email", "N/A")),
            ("Contact", profile_data.get("email", "N/A")),
            ("IC Number", profile_data.get("ic", "N/A")),
        ]

    elif user_role == "Admin":
        fields = [
            ("Admin ID", profile_data.get("admin_id", user_id)),
            ("Name", profile_data.get("name", "N/A")),
            ("Email", profile_data.get("email", "N/A")),
            ("Role", "System Administrator"),
        ]

    # 2. Build the read-only HTML fields
    profile_html = ""
    for label, value in fields:
        profile_html += f"""
        <div class="row mb-3 border-bottom pb-2">
            <div class="col-sm-4 text-muted">{label}</div>
            <div class="col-sm-8 fw-bold">{value}</div>
        </div>
        """

    context["profile_data_html"] = profile_html

    return render("profile.html", context), 200
