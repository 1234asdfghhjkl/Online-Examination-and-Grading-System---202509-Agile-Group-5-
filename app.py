from flask import Flask
from flask import session
from dotenv import load_dotenv
import os
# Import and register blueprint
from routes.exam_routes import exam_bp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")


@app.route("/")
def index():
    return '<h1>Online Exam System (For Homepage)</h1><p><a href="/create-exam">Go to Create Exam</a></p>'


@app.before_request
def clear_session_on_restart():
    if not session.get("initialized"):
        session.clear()
        session["initialized"] = True




app.register_blueprint(exam_bp)

if __name__ == "__main__":
    app.run(debug=True)
