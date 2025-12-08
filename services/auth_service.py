# services/auth_service.py
from firebase_admin import auth, firestore
from core.firebase_db import db
from typing import Dict, Any


def authenticate_user(user_id: str, ic: str, role: str) -> Dict[str, Any]:
    """
    Authenticate a user with user ID, IC number, and role
    
    Args:
        user_id: User's ID (student_id or lecturer_id)
        ic: User's IC number
        role: User's role (student, lecturer, admin)
    
    Returns:
        Dict containing user data if successful
        
    Raises:
        ValueError: If authentication fails
    """
    
    # For admin, use hardcoded credentials (keep existing)
    if role == "admin":
        # UPDATED: Admin can log in with User ID 'A001' and IC '010101070101'
        if (user_id == "A001" and ic == "010101070101") :
            return {
                "uid": "admin",
                "user_id": "admin",
                "role": "admin",
                "name": "System Administrator"
            }
        else:
            raise ValueError("Invalid admin credentials")
    
    try:
        # Get user profile from Firestore by user_id
        user_doc = db.collection('users').document(user_id).get()
        
        if not user_doc.exists:
            raise ValueError("User ID not found in system")
        
        user_data = user_doc.to_dict()
        
        # Verify role matches
        if user_data.get('role') != role:
            raise ValueError(f"Access denied. Please login as {user_data.get('role', 'the correct role')}")
        
        # Verify IC number matches (use stored ic field)
        if user_data.get('ic') != ic:
            raise ValueError("Invalid IC number")
        
        # Get email from user_data
        email = user_data.get('email', '')
        
        return {
            "uid": user_data.get('uid', user_id),
            "user_id": user_id,
            "email": email,
            "role": user_data.get('role'),
            "name": user_data.get('name', 'Unknown'),
            "student_id": user_data.get('student_id'),
            "lecturer_id": user_data.get('lecturer_id'),
            "ic": user_data.get('ic'),
        }
        
    except Exception as e:
        raise ValueError(f"Authentication failed: {str(e)}")


def get_redirect_url(role: str, user_data: Dict[str, Any]) -> str:
    """
    Get the redirect URL based on user role
    
    Args:
        role: User's role
        user_data: User data dictionary
    
    Returns:
        URL to redirect to after login
    """
    
    if role == "admin":
        return "/admin/exam-list"
    elif role == "lecturer":
        return "/exam-list"
    elif role == "student":
        student_id = user_data.get('student_id', user_data.get('uid', 'guest'))
        return f"/student-dashboard?student_id={student_id}"
    else:
        return "/"


def create_admin_account():
    """
    Create a default admin account if it doesn't exist
    This should be run once during system setup
    """
    # Define the admin IC number
    ADMIN_IC = "010101070101"
    
    try:
        # Try to get admin user
        try:
            auth.get_user_by_email("admin@system.com")
            print("Admin account already exists")
            return
        except auth.UserNotFoundError:
            pass
        
        # Create admin user in Firebase Auth
        auth.create_user( # Removed assignment to unused variable 'admin_user'
            uid="admin",
            email="admin@system.com",
            password="admin123", # Password for Firebase Auth
            display_name="System Administrator"
        )
        
        # Create admin profile in Firestore
        db.collection('users').document("admin").set({
            'uid': 'admin',
            'email': 'admin@system.com',
            'name': 'System Administrator',
            'role': 'admin',
            'ic': ADMIN_IC, # Store the IC number in Firestore
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        print("Admin account created successfully")
        print("User ID: admin")
        print(f"IC Number: {ADMIN_IC} (Used for ID/IC login)")
        print("Email: admin@system.com")
        print("Password: admin123 (Used for Email/Password login)")
        
    except Exception as e:
        print(f"Error creating admin account: {e}")