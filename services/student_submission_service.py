"""
Student Submission Service
Handles retrieval of student submissions and result status
"""

from typing import List, Dict
from datetime import datetime

from core.firebase_db import db
from services.exam_service import get_exam_by_id
from services.student_result_service import check_results_released


def get_student_submissions(student_id: str) -> List[Dict]:
    """
    Get all submissions for a specific student with exam details and result status.
    Logic updated to hide scores if results are not yet released.
    """
    if not student_id:
        return []

    # Query all submissions for this student
    query = db.collection("submissions").where("student_id", "==", student_id).stream()

    submissions = []
    for doc in query:
        data = doc.to_dict()
        data["submission_id"] = doc.id

        # Get exam details
        exam_id = data.get("exam_id")
        exam = get_exam_by_id(exam_id)

        if exam:
            data["exam_title"] = exam.get("title", "Unknown Exam")
            data["exam_date"] = exam.get("exam_date", "N/A")

            # Check if results are released
            is_released, release_date, release_time = check_results_released(exam_id)
            data["results_released"] = is_released
            data["release_date"] = release_date
            data["release_time"] = release_time

            # --- LOGIC UPDATE: Handle Release Status ---
            if is_released:
                # Case 1: Results are public. Show actual scores.
                data["mcq_score"] = data.get("mcq_score", 0)
                data["mcq_total"] = data.get("mcq_total", 0)
                data["overall_percentage"] = data.get("overall_percentage", 0)

                # Flags for the template
                data["show_score"] = True
                data["status_label"] = "Graded"
                data["action_label"] = "View Report"
                data["is_actionable"] = True  # Button should be clickable

            else:
                # Case 2: Results are hidden. Mask scores to prevent "0%" confusion.
                data["mcq_score"] = "-"
                data["mcq_total"] = data.get("mcq_total", 0)
                # Set to None so templates can distinguish between "Failed (0%)" and "Hidden (None)"
                data["overall_percentage"] = None

                # Flags for the template
                data["show_score"] = False
                data["is_actionable"] = False  # Button should be disabled

                # meaningful status message
                if release_date:
                    data["status_label"] = f"Results: {release_date} {release_time}"
                    data["action_label"] = "Pending Release"
                else:
                    data["status_label"] = "Awaiting Release"
                    data["action_label"] = "Not Released"

            submissions.append(data)

    # Sort by submission date (most recent first)
    submissions.sort(key=lambda x: x.get("submitted_at", datetime.min), reverse=True)

    return submissions


def get_student_performance_stats(student_id: str) -> Dict:
    """
    Calculates performance statistics.
    LOGIC UPDATE: Shows 'Exams Taken' count even if results are not released yet.
    """
    submissions = get_student_submissions(student_id)

    # 1. Count ALL submissions (Released + Unreleased)
    total_exams_taken = len(submissions)

    # If no exams taken AT ALL, hide the box
    if total_exams_taken == 0:
        return {
            "has_data": False,
            "average": 0,
            "total_exams": 0,
            "highest": 0,
            "lowest": 0,
        }

    # 2. Filter only RELEASED exams for score calculations
    graded_subs = [s for s in submissions if s.get("results_released", False)]

    if graded_subs:
        scores = [s.get("overall_percentage", 0) for s in graded_subs]
        # Calculate actual stats
        average = round(sum(scores) / len(scores), 2)
        highest = max(scores)
        lowest = min(scores)
    else:
        # Student has taken exams, but NONE are released yet
        average = "-"
        highest = "-"
        lowest = "-"

    return {
        "has_data": True,  # Show the box because they have taken exams
        "average": average,
        "total_exams": total_exams_taken,  # This will now show "1" or more
        "highest": highest,
        "lowest": lowest,
    }
