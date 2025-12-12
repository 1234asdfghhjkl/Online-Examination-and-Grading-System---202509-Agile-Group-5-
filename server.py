from http.server import HTTPServer, BaseHTTPRequestHandler
import os

# Replaced 'cgi' with 'email' library for Python 3.13+ compatibility
from email.parser import BytesParser
from email import policy
from urllib.parse import urlparse, parse_qs
import json

# Import authentication routes
from web.auth_routes import get_login_page, post_login

from web.admin_routes import (
    get_admin_exam_list,
    get_set_result_release,
    post_set_result_release,
    get_grading_settings,
    post_grading_settings,
    get_account_import_page,
    post_import_accounts,
    get_admin_student_list,
)

from web.template_engine import STATIC_DIR
from web import exams, mcq, tc_reports, short_answer, student_exam, password_routes
from web.student_result_routes import get_student_result_view
from web.student_result_routes import get_student_result_pdf

# ADDED: Import for student_filter_service
from services.student_filter_service import (
    get_available_filters,
    get_students_by_filters,
)

# NEW: Import the profile routes module
from web import profile_routes

HOST = "localhost"
PORT = 8000


class Handler(BaseHTTPRequestHandler):
    def _send_html(self, html_str: str, status: int = 200):
        data = html_str.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, json_str: str, status: int = 200):
        data = json_str.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _parse_multipart_form(self) -> tuple[dict, bytes | None, str | None]:
        """
        Parses multipart/form-data using the modern 'email' library.
        (Fixes the Python 3.13 'cgi' module deprecation error).
        Returns (form_fields, file_content_bytes, file_name).
        """
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return {}, None, None

        # 1. Read the full request body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0

        body = self.rfile.read(content_length)

        # 2. Reconstruct the full HTTP message (Headers + Body) for the parser
        # The parser needs the Content-Type header to know the boundary
        headers_list = []
        for key, value in self.headers.items():
            headers_list.append(f"{key}: {value}")
        headers_str = "\r\n".join(headers_list)

        # Combine headers and body into a single bytes object
        full_msg_bytes = headers_str.encode("utf-8") + b"\r\n\r\n" + body

        # 3. Parse using BytesParser
        msg = BytesParser(policy=policy.HTTP).parsebytes(full_msg_bytes)

        form_fields = {}
        file_content = None
        file_name = None

        # 4. Extract parts
        if msg.is_multipart():
            for part in msg.iter_parts():
                # Extract 'name' (field name) and 'filename'
                part_name = part.get_param("name", header="Content-Disposition")
                part_filename = part.get_filename()

                # Get binary data
                part_data = part.get_payload(decode=True)

                if part_name == "excel_file":
                    if part_data:
                        file_content = part_data
                    if part_filename:
                        file_name = part_filename

                elif part_name == "excel_file_placeholder":
                    # This field sometimes carries the filename or overrides it
                    val = part_data.decode("utf-8") if part_data else None
                    form_fields[part_name] = val
                    if val:
                        file_name = val

                elif part_name:
                    # Regular form fields
                    if part_data:
                        form_fields[part_name] = part_data.decode("utf-8")
                    else:
                        form_fields[part_name] = ""

        return form_fields, file_content, file_name

    # ---------- GET ----------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # ========================================
        # LOGIN / ROOT ROUTE
        # ========================================
        if path == "/" or path == "/login":
            html_str, status = get_login_page()
            self._send_html(html_str, status)

    # ========================================
        # LOGOUT ROUTE (NEW)
        # ========================================
        elif path == "/logout":
            # Redirect to login page
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return
        # ========================================
        # PROFILE ROUTE (NEW)
        # ========================================
        elif path == "/profile":
            user_id = query.get("user_id", [""])[0]
            # If no ID provided, we could error or default to a test user
            # For this setup, if empty, the route handler will show an error.
            html_str, status = profile_routes.get_profile_page(user_id)
            self._send_html(html_str, status)

        # NEW: Change Password GET
        elif path == "/change-password":
            user_id = query.get("user_id", [""])[0]
            html_str, status = password_routes.get_change_password_page(user_id)
            self._send_html(html_str, status)

        # Admin/Lecturer routes
        elif path == "/create-exam":
            lecturer_id = query.get("lecturer_id", [""])[0]  # <--- Capture ID from URL
            html_str, status = exams.get_create_exam(lecturer_id)
            self._send_html(html_str, status)

        elif path.startswith("/exam-edit"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = exams.get_edit_exam(exam_id)
            self._send_html(html_str, status)

        elif path == "/exam-delete":
            exam_id = query.get("exam_id", [""])[0]
            method = query.get("method", ["hard"])[0]
            html_str, status = exams.get_exam_delete(exam_id, method)
            self._send_html(html_str, status)

        elif path == "/exam-report":
            html_str, status = tc_reports.get_exam_results_summary_report(query)
            self._send_html(html_str, status)

        elif path == "/exam-list":
            search = query.get("q", [""])[0]
            sort = query.get("sort", ["date"])[0]
            lecturer_id = query.get("lecturer_id", [""])[0]

            html_str, status = exams.get_exam_list(
                success_message="",
                search=search,
                sort=sort,
                lecturer_id=lecturer_id,
            )
            self._send_html(html_str, status)

        # ------------------------------
        # ADMIN ROUTES
        # ------------------------------
        elif path == "/admin/exam-list":
            html_str, status = get_admin_exam_list()
            self._send_html(html_str, status)

        elif path == "/admin/grading-settings":
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = get_grading_settings(exam_id)
            self._send_html(html_str, status)

        elif path.startswith("/admin/set-result-release"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = get_set_result_release(exam_id)
            self._send_html(html_str, status)

        elif path == "/admin/import-accounts":
            html_str, status = get_account_import_page()
            self._send_html(html_str, status)

        elif path == "/admin/performance-report":
            exam_id = query.get("exam_id", [""])[0]
            from web.admin_performance_routes import get_performance_report

            html_str, status = get_performance_report(exam_id)
            self._send_html(html_str, status)

        elif path == "/view-submission-result":
            submission_id = query.get("submission_id", [""])[0]
            from web import grading

            html_str, status = grading.get_view_submission_result(submission_id)
            self._send_html(html_str, status)

        elif path == "/admin/student-list":
            html_str, status = get_admin_student_list()
            self._send_html(html_str, status)

        # ------------------------------
        # EXAM BUILDER ROUTES
        # ------------------------------
        elif path.startswith("/mcq-builder"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = mcq.get_mcq_builder(exam_id)
            self._send_html(html_str, status)

        elif path.startswith("/exam-review"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = exams.get_exam_review(exam_id)
            self._send_html(html_str, status)

        elif path.startswith("/exam-publish"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = exams.get_exam_published(exam_id)
            self._send_html(html_str, status)

        elif path.startswith("/short-builder"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = short_answer.get_short_builder(exam_id)
            self._send_html(html_str, status)

        elif path == "/debug-time":
            from services.exam_timing import get_server_time

            server_time = get_server_time()
            html_str = (
                f"<h1>Server Time: {server_time.strftime('%Y-%m-%d %H:%M:%S %Z')}</h1>"
            )
            self._send_html(html_str, 200)

        # ------------------------------
        # STUDENT ROUTES
        # ------------------------------
        elif path == "/student-dashboard":
            sid = query.get("student_id", ["test_student_01"])[0]
            html_str, status = student_exam.get_student_dashboard(sid)
            self._send_html(html_str, status)

        elif path == "/student-exam":
            exam_id = query.get("exam_id", [""])[0]
            student_id = query.get("student_id", [""])[0]
            html_str, status = student_exam.get_student_exam(exam_id, student_id)
            self._send_html(html_str, status)

        elif path == "/exam-result":
            exam_id = query.get("exam_id", [""])[0]
            student_id = query.get("student_id", [""])[0]
            html_str, status = student_exam.get_exam_result(exam_id, student_id)
            self._send_html(html_str, status)

        elif path == "/student-result":
            exam_id = query.get("exam_id", [""])[0]
            student_id = query.get("student_id", [""])[0]
            html_str, status = get_student_result_view(exam_id, student_id)
            self._send_html(html_str, status)

        # PDF route
        elif path.startswith("/student-result-pdf"):
            exam_id = query.get("exam_id", [""])[0]
            student_id = query.get("student_id", [""])[0]
            pdf_bytes, status, headers = get_student_result_pdf(exam_id, student_id)

            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(pdf_bytes)
            return

        # ------------------------------
        # API ROUTES
        # ------------------------------
        elif path == "/api/check-exam-status":
            exam_id = query.get("exam_id", [""])[0]
            student_id = query.get("student_id", [""])[0]
            json_str, status = student_exam.api_check_exam_status(exam_id, student_id)
            self._send_json(json_str, status)

        # ADDED: New API route for student filter options
        elif path == "/api/get-filter-options":
            # Get current exam_id if provided in query
            exam_id = query.get("exam_id", [""])[0]

            available = get_available_filters()
            combinations = get_students_by_filters()

            response_data = {
                "majors": available.get("majors", []),
                "years": available.get("years", []),
                "semesters": available.get("semesters", []),
                "combinations": combinations,
            }

            # If exam_id is provided, also return current filters
            if exam_id:
                from services.student_filter_service import get_exam_filters

                current_filters = get_exam_filters(exam_id)
                response_data["current_filters"] = current_filters

            json_str = json.dumps(response_data)
            self._send_json(json_str, 200)

        elif path == "/grade-submissions":
            exam_id = query.get("exam_id", [""])[0]
            from web import grading

            html_str, status = grading.get_grade_submissions(exam_id)
            self._send_html(html_str, status)

        elif path == "/grade-short-answers":
            submission_id = query.get("submission_id", [""])[0]
            from web import grading

            html_str, status = grading.get_grade_short_answers(submission_id)
            self._send_html(html_str, status)

        # Static
        elif path.startswith("/static/"):
            self._serve_static(path[len("/static/") :])

        else:
            self.send_error(404, "Not Found")

    # ---------- POST ----------
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # ========================================
        # LOGIN ROUTE
        # ========================================
        if path == "/login":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")

            html_str, status, redirect_url = post_login(body)

            if redirect_url:
                # Redirect on successful login
                self.send_response(302)
                self.send_header("Location", redirect_url)
                self.end_headers()
            else:
                # Show error page
                self._send_html(html_str, status)
            return

        # -----------------------------------
        # FILE UPLOAD HANDLER
        # -----------------------------------
        if path == "/admin/import-accounts-upload":
            form_fields, file_content_bytes, file_name = self._parse_multipart_form()
            user_type = query.get("type", [""])[0]

            html_str, status = post_import_accounts(
                user_type=user_type,
                form_fields=form_fields,
                file_content=file_content_bytes,
                file_name=file_name,
            )
            self._send_html(html_str, status)
            return

        # -----------------------------------
        # STANDARD POST (for non-file forms)
        # -----------------------------------
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")

        # Lecturer routes
        if path == "/submit-exam":
            html_str, status = exams.post_submit_exam(body)
            self._send_html(html_str, status)

        elif path == "/publish-exam":
            html_str, status = exams.post_publish_exam(body)
            self._send_html(html_str, status)

        elif path.startswith("/mcq-builder"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = mcq.post_mcq_builder(exam_id, body)
            self._send_html(html_str, status)

        elif path.startswith("/mcq-delete"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = mcq.post_delete_mcq(exam_id, body)
            self._send_html(html_str, status)

        elif path.startswith("/mcq-done"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = mcq.post_mcq_done(exam_id, body)
            self._send_html(html_str, status)

        elif path.startswith("/short-builder"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = short_answer.post_short_builder(exam_id, body)
            self._send_html(html_str, status)

        elif path.startswith("/short-done"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = short_answer.post_short_done(exam_id, body)
            self._send_html(html_str, status)

        elif path.startswith("/short-delete"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = short_answer.post_short_delete(exam_id, body)
            self._send_html(html_str, status)

        elif path.startswith("/exam-edit"):
            html_str, status = exams.post_edit_exam(body)
            self._send_html(html_str, status)

        # Student routes
        elif path == "/submit-student-exam":
            html_str, status = student_exam.post_submit_student_exam(body)
            self._send_html(html_str, status)

        elif path == "/student-result":
            exam_id = query.get("exam_id", [""])[0]
            student_id = query.get("student_id", [""])[0]
            html_str, status = get_student_result_view(exam_id, student_id)
            self._send_html(html_str, status)

        # Change Password POST
        elif path == "/change-password":
            user_id = query.get("user_id", [""])[0]
            html_str, status, _ = password_routes.post_change_password(user_id, body)
            self._send_html(html_str, status)

        # API
        elif path == "/api/auto-submit-exam":
            json_str, status = student_exam.api_auto_submit_exam(body)
            self._send_json(json_str, status)

        elif path == "/api/save-draft":
            json_str, status = student_exam.api_save_draft(body)
            self._send_json(json_str, status)

        elif path == "/save-short-answer-grades":
            from web import grading

            html_str, status = grading.post_save_short_answer_grades(body)
            self._send_html(html_str, status)

        # -----------------------------------
        # ADMIN POST ROUTES
        # -----------------------------------
        elif path == "/admin/save-grading-settings":
            html_str, status = post_grading_settings(body)
            self._send_html(html_str, status)

        elif path == "/admin/set-result-release":
            html_str, status = post_set_result_release(body)
            self._send_html(html_str, status)

        else:
            self.send_error(404, "Not Found")

    # ---------- Static files ----------
    def _serve_static(self, filename: str):
        path = os.path.join(STATIC_DIR, filename)
        if not os.path.isfile(path):
            self.send_error(404, "Not Found")
            return

        with open(path, "rb") as f:
            data = f.read()

        self.send_response(200)

        if filename.endswith(".css"):
            self.send_header("Content-Type", "text/css")
        elif filename.endswith(".js"):
            self.send_header("Content-Type", "application/javascript")
        elif filename.endswith(".png"):
            self.send_header("Content-Type", "image/png")
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
            self.send_header("Content-Type", "image/jpeg")
        elif filename.endswith(".svg"):
            self.send_header("Content-Type", "image/svg+xml")
        else:
            self.send_header("Content-Type", "application/octet-stream")

        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    try:
        # Initialize admin account on startup
        from services.auth_service import create_admin_account

        create_admin_account()

        httpd = HTTPServer((HOST, PORT), Handler)
        print(f"Serving at http://{HOST}:{PORT}")
        print("\n=== LOGIN CREDENTIALS ===")
        print("Admin: Use Admin ID 'A001' + IC number '010101070101'")
        print("Lecturer: Use Lecturer ID + IC number (e.g., L001 / 950101011234)")
        print("Student: Use Student ID + IC number (e.g., 100456 / 031105010567)")
        print("\n=== ROUTES ===")
        print(f"Login: http://{HOST}:{PORT}/login")
        print(f"Profile: http://{HOST}:{PORT}/profile?user_id=100123")
        print(f"Lecturer: http://{HOST}:{PORT}/exam-list")
        print(
            f"Student: http://{HOST}:{PORT}/student-dashboard?student_id=test_student_01"
        )
        print(f"Admin: http://{HOST}:{PORT}/admin/exam-list")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
        httpd.server_close()
