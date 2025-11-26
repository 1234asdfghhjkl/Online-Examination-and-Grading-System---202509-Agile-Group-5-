"""
Exam Timing Service
Handles exam scheduling, time validation, and access control
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from core.firebase_db import db

MALAYSIA_TZ = timezone(timedelta(hours=8))


def get_server_time() -> datetime:
    """
    Returns the current server time in Malaysia timezone (UTC+8)
    """
    return datetime.now(MALAYSIA_TZ)


def parse_exam_datetime(exam_date: str, start_time: str = "00:00") -> datetime:
    """
    Combines exam date and time into a datetime object in Malaysia timezone

    Args:
        exam_date: Date string in format YYYY-MM-DD
        exam_time: Time string in format HH:MM (24-hour format)

    Returns:
        datetime object in Malaysia timezone (UTC+8)
    """
    try:
        date_part = datetime.strptime(exam_date, "%Y-%m-%d").date()
        time_part = datetime.strptime(start_time, "%H:%M").time()
        naive_dt = datetime.combine(date_part, time_part)
        # Make it timezone-aware with Malaysia timezone
        return naive_dt.replace(tzinfo=MALAYSIA_TZ)
    except ValueError:
        raise ValueError("Invalid date or time format")


def calculate_exam_window(
    exam_start: datetime, duration_minutes: int, buffer_minutes: int = 5
) -> Tuple[datetime, datetime]:
    """
    Calculate the valid exam window

    Args:
        exam_start: Exam start datetime
        duration_minutes: Exam duration in minutes
        buffer_minutes: Extra time buffer after official end (default: 5 min)

    Returns:
        Tuple of (start_time, end_time)
    """
    end_time = exam_start + timedelta(minutes=duration_minutes + buffer_minutes)
    return exam_start, end_time


def check_exam_access(exam_id: str) -> Dict:
    """
    Check if student can access the exam based on current time
    ...
    """
    if not exam_id:
        return {
            "can_access": False,
            "status": "not_found",
            "message": "Invalid exam ID",
            "server_time": get_server_time(),
        }

    # Fetch exam from database
    doc_ref = db.collection("exams").document(exam_id)
    snap = doc_ref.get()

    if not snap.exists:
        return {
            "can_access": False,
            "status": "not_found",
            "message": "Exam not found",
            "server_time": get_server_time(),
        }

    exam = snap.to_dict()

    # Check if exam is published
    if exam.get("status") != "published":
        return {
            "can_access": False,
            "status": "not_published",
            "message": "Exam is not yet published",
            "server_time": get_server_time(),
        }

    # Get exam timing details
    exam_date = exam.get("exam_date", "")
    start_time = exam.get(
        "start_time", exam.get("exam_time", "00:00")
    )  # Migration fallback
    duration = exam.get("duration", 0)

    try:
        exam_start = parse_exam_datetime(exam_date, start_time)
        exam_start_time, hard_end = calculate_exam_window(
            exam_start, duration
        )  # ← Fixed
        server_time = get_server_time()

        # Calculate time differences
        time_until_start = (exam_start - server_time).total_seconds()
        time_remaining = (hard_end - server_time).total_seconds()

        # Determine access status
        if server_time < exam_start:
            return {
                "can_access": False,
                "status": "before_start",
                "message": f"Exam will start in {int(time_until_start // 60)} minutes",
                "server_time": server_time,
                "exam_start": exam_start,
                "exam_end": hard_end,
                "time_until_start": int(time_until_start),
                "time_remaining": None,
            }
        elif server_time <= hard_end:
            return {
                "can_access": True,
                "status": "active",
                "message": "Exam is active",
                "server_time": server_time,
                "exam_start": exam_start,
                "exam_end": hard_end,
                "time_until_start": 0,
                "time_remaining": int(time_remaining),
            }
        else:
            return {
                "can_access": False,
                "status": "ended",
                "message": "Exam has ended",
                "server_time": server_time,
                "exam_start": exam_start,
                "exam_end": hard_end,
                "time_until_start": None,
                "time_remaining": 0,
            }

    except ValueError as e:
        return {
            "can_access": False,
            "status": "error",
            "message": f"Invalid exam timing configuration: {str(e)}",
            "server_time": get_server_time(),
        }


def check_student_submission_status(exam_id: str, student_id: str) -> Dict:
    """
    Check if student has already submitted the exam

    Returns:
        Dict with submission status
    """
    if not exam_id or not student_id:
        return {
            "has_submitted": False,
            "submission_time": None,
        }

    # Query submissions collection
    query = (
        db.collection("submissions")
        .where("exam_id", "==", exam_id)
        .where("student_id", "==", student_id)
        .limit(1)
    )

    for doc in query.stream():
        data = doc.to_dict()
        return {
            "has_submitted": True,
            "submission_time": data.get("submitted_at"),
            "submission_id": doc.id,
        }

    return {
        "has_submitted": False,
        "submission_time": None,
    }


def can_start_exam(exam_id: str, student_id: str) -> Tuple[bool, str]:
    """
    Comprehensive check if student can start the exam

    Returns:
        Tuple of (can_start: bool, reason: str)
    """
    # Check timing
    access_info = check_exam_access(exam_id)

    if not access_info["can_access"]:
        return False, access_info["message"]

    # Check if already submitted
    submission_info = check_student_submission_status(exam_id, student_id)

    if submission_info["has_submitted"]:
        return False, "You have already submitted this exam"

    return True, "You can start the exam"


def auto_submit_exam(exam_id: str, student_id: str, answers: Dict) -> Optional[str]:
    """
    Auto-submit exam when time expires

    Returns:
        Submission ID if successful, None otherwise
    """
    submission_data = {
        "exam_id": exam_id,
        "student_id": student_id,
        "answers": answers,
        "submitted_at": get_server_time(),
        "auto_submitted": True,
        "status": "completed",
    }

    doc_ref = db.collection("submissions").document()
    doc_ref.set(submission_data)

    return doc_ref.id
