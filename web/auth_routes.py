# web/auth_routes.py
from urllib.parse import parse_qs
import html
from services.auth_service import authenticate_user, get_redirect_url
from .template_engine import render



def get_login_page():
    """
    GET handler for login page
    """
    ctx = {
        "errors_html": "",
        "user_id": "",  # Changed from "email"
    }
    html_str = render("login.html", ctx)
    return html_str, 200


def post_login(body: str):
    """
    POST handler for login authentication
    
    Args:
        body: Form data from POST request
    
    Returns:
        Tuple of (html_string, status_code, redirect_url)
    """
    # Parse form data
    data = parse_qs(body)
    
    user_id = data.get("user_id", [""])[0].strip()
    ic = data.get("ic", [""])[0].strip()
    role = data.get("role", ["student"])[0].strip()
    
    # Validation
    if not user_id or not ic:
        ctx = {
            "errors_html": """
            <div class="alert alert-danger" role="alert">
                <strong>Error:</strong> Please enter both User ID and IC number.
            </div>
            """,
            "user_id": html.escape(user_id),
        }
        html_str = render("login.html", ctx)
        return html_str, 400, None
    
    # Authenticate
    try:
        user_data = authenticate_user(user_id, ic, role)
        
        # Get redirect URL
        redirect_url = get_redirect_url(role, user_data)
        
        # Success - return redirect info
        return None, 302, redirect_url
        
    except ValueError as e:
        # Authentication failed
        error_message = str(e)
        
        ctx = {
            "errors_html": f"""
            <div class="alert alert-danger" role="alert">
                <strong>Login Failed:</strong> {html.escape(error_message)}
            </div>
            """,
            "user_id": html.escape(user_id),
        }
        html_str = render("login.html", ctx)
        return html_str, 401, None
    
    except Exception:
        # Unexpected error
        ctx = {
            "errors_html": """
            <div class="alert alert-danger" role="alert">
                <strong>System Error:</strong> An unexpected error occurred. Please try again.
            </div>
            """,
            "user_id": html.escape(user_id),
        }
        html_str = render("login.html", ctx)
        return html_str, 500, None