from http.server import HTTPServer, BaseHTTPRequestHandler
import os

from web.template_engine import STATIC_DIR
from web import exams, mcq, short_answer, student_exam
from urllib.parse import urlparse, parse_qs

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

    # ---------- GET ----------

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Admin routes
        if path in ("/", "/create-exam"):
            html_str, status = exams.get_create_exam()
            self._send_html(html_str, status)
        elif path.startswith("/exam-edit"):
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = exams.get_edit_exam(exam_id)
            self._send_html(html_str, status)
        elif path == "/exam-list":
            html_str, status = exams.get_exam_list()
            self._send_html(html_str, status)
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

        # Student routes
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

        # API routes
        elif path == "/api/check-exam-status":
            exam_id = query.get("exam_id", [""])[0]
            student_id = query.get("student_id", [""])[0]
            json_str, status = student_exam.api_check_exam_status(exam_id, student_id)
            self._send_json(json_str, status)

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

        # Static files
        elif path.startswith("/static/"):
            self._serve_static(path[len("/static/") :])
        else:
            self.send_error(404, "Not Found")

    # ---------- POST ----------

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Admin routes
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

        # API routes
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

        # Add more content-types
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
        httpd = HTTPServer((HOST, PORT), Handler)
        print(f"Serving at http://{HOST}:{PORT}")
        print(f"\nAdmin: http://{HOST}:{PORT}/create-exam")
        print(
            f"\nStudent: http://{HOST}:{PORT}/student-dashboard?student_id=test_student_01"
        )
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
        httpd.server_close()
