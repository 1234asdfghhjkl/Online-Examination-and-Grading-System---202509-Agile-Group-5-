from http.server import HTTPServer, BaseHTTPRequestHandler
import os

from web.template_engine import STATIC_DIR
from web import exams, mcq, short_answer
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

    # ---------- GET ----------

    def do_GET(self):
        if self.path in ("/", "/create-exam"):
            html_str, status = exams.get_create_exam()
            self._send_html(html_str, status)
        elif self.path.startswith("/mcq-builder"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = mcq.get_mcq_builder(exam_id)
            self._send_html(html_str, status)
        elif self.path.startswith("/exam-review"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = exams.get_exam_review(exam_id)
            self._send_html(html_str, status)
        elif self.path.startswith("/exam-publish"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = exams.get_exam_published(exam_id)
            self._send_html(html_str, status)
        elif self.path.startswith("/short-builder"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = short_answer.get_short_builder(exam_id)
            self._send_html(html_str, status)

        elif self.path.startswith("/static/"):
            self._serve_static(self.path[len("/static/") :])
        else:
            self.send_error(404, "Not Found")

    # ---------- POST ----------

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")

        if self.path == "/submit-exam":
            html_str, status = exams.post_submit_exam(body)
            self._send_html(html_str, status)
        elif self.path == "/edit-exam":
            html_str, status = exams.post_edit_exam(body)
            self._send_html(html_str, status)
        elif self.path == "/publish-exam":
            html_str, status = exams.post_publish_exam(body)
            self._send_html(html_str, status)
        elif self.path.startswith("/mcq-builder"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = mcq.post_mcq_builder(exam_id, body)
            self._send_html(html_str, status)
        elif self.path.startswith("/mcq-delete"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = mcq.post_delete_mcq(exam_id, body)
            self._send_html(html_str, status)
        elif self.path.startswith("/mcq-done"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = mcq.post_mcq_done(exam_id, body)
            self._send_html(html_str, status)
        elif self.path.startswith("/short-builder"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = short_answer.post_short_builder(exam_id, body)
            self._send_html(html_str, status)

        elif self.path.startswith("/short-done"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = short_answer.post_short_done(exam_id, body)
            self._send_html(html_str, status)
        elif self.path.startswith("/short-delete"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            exam_id = query.get("exam_id", [""])[0]
            html_str, status = short_answer.post_short_delete(exam_id, body)
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
            self.send_header("Content-Type", "text/css; charset=utf-8")
        else:
            self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    httpd = HTTPServer((HOST, PORT), Handler)
    print(f"Serving at http://{HOST}:{PORT}")
    httpd.serve_forever()
