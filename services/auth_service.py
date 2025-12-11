# services/auth_service.py
import requests
from firebase_admin import auth
from core.firebase_db import db
from typing import Dict, Any

# ==========================================================
# 🔑 CONFIGURATION REQUIRED
# ==========================================================
# PASTE YOUR WEB API KEY HERE
FIREBASE_WEB_API_KEY = "AIzaSyBFW2Pzvp3l3BNBtBE5Wx2zEdK4xvhu3IY"
# ==========================================================


def authenticate_user(user_id: str, password: str, role: str) -> Dict[str, Any]:
    """
    Authenticate a user using Firebase Auth (REST API).
    This supports both the default password (IC) and changed passwords.
    """

    # 1. SPECIAL CASE: Admin Hardcoded Login (Keep existing backdoor)
    if role == "admin":
        if user_id == "A001" and password == "010101070101":
            return {
                "uid": "admin",
                "user_id": "admin",
                "role": "admin",
                "name": "System Administrator",
            }

    # 2. Get User Email from Firestore using user_id
    # We need the email to login via Firebase Auth REST API.
    try:
        user_doc = db.collection("users").document(user_id).get()
        if not user_doc.exists:
            raise ValueError("User ID not found.")

        user_data = user_doc.to_dict()
        email = user_data.get("email")

        # Verify role matches
        if user_data.get("role") != role:
            raise ValueError(f"Access denied. Please login as {user_data.get('role')}")

    except Exception as e:
        raise ValueError(f"Account lookup failed: {str(e)}")

    # 3. Verify Password using Firebase Auth REST API
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"

    payload = {"email": email, "password": password, "returnSecureToken": True}

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        # Login Successful
        auth_response = response.json()
        firebase_uid = auth_response.get("localId")

        return {
            "uid": firebase_uid,
            "user_id": user_id,
            "email": email,
            "role": user_data.get("role"),
            "name": user_data.get("name", "Unknown"),
            "student_id": user_data.get("student_id"),
            "lecturer_id": user_data.get("lecturer_id"),
            "ic": user_data.get("ic"),  # Keep for reference
        }

    elif response.status_code == 400:
        error_data = response.json()
        message = error_data.get("error", {}).get("message", "")

        if "INVALID_PASSWORD" in message:
            raise ValueError("Invalid password.")
        elif "EMAIL_NOT_FOUND" in message:
            raise ValueError("Account not found.")
        elif "USER_DISABLED" in message:
            raise ValueError("Account disabled.")
        else:
            raise ValueError("Authentication failed.")
    else:
        raise ValueError("System authentication error.")


def get_redirect_url(role: str, user_data: Dict[str, Any]) -> str:
    """Get the redirect URL based on user role"""
    if role == "admin":
        return "/admin/exam-list"

    elif role == "lecturer":
        # FIX: Get the ID and append it to the URL
        lecturer_id = user_data.get("lecturer_id", user_data.get("user_id", ""))
        return f"/exam-list?lecturer_id={lecturer_id}"

    elif role == "student":
        student_id = user_data.get("student_id", user_data.get("uid", "guest"))
        return f"/student-dashboard?student_id={student_id}"
    else:
        return "/"


def create_admin_account():
    """Helper to ensure admin exists (run on startup)"""
    ADMIN_IC = "010101070101"
    try:
        try:
            auth.get_user_by_email("admin@system.com")
            print("Admin account already exists")
            return
        except auth.UserNotFoundError:
            pass

        auth.create_user(
            uid="admin",
            email="admin@system.com",
            password="admin123",
            display_name="System Administrator",
        )
        db.collection("users").document("admin").set(
            {
                "uid": "admin",
                "email": "admin@system.com",
                "name": "System Administrator",
                "role": "admin",
                "ic": ADMIN_IC,
                "created_at": "2024-01-01",
            }
        )
        print("Admin account created successfully")
    except Exception as e:
        print(f"Error creating admin: {e}")
