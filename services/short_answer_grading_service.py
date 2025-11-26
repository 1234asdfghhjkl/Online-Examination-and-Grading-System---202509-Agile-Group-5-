"""
Crated on 2025-11-27
By Liyi
Short Answer Grading Service
Handles manual grading of short answer questions by teachers
"""

from typing import Dict, List, Optional
from datetime import datetime

from core.firebase_db import db


def get_submissions_for_grading(exam_id: str) -> List[Dict]:
    """
    Get all submissions for an exam that need grading
    """
    query = db.collection("submissions").where("exam_id", "==", exam_id).stream()

    submissions = []
    for doc in query.stream():
        data = doc.to_dict()
        data["submission_id"] = doc.id
        submissions.append(data)

    return submissions


def get_submission_with_questions(submission_id: str) -> Optional[Dict]:
    """
    Get submission with short answer questions and student answers
    """
    from services.question_service import get_short_answer_questions_by_exam

    doc_ref = db.collection("submissions").document(submission_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    submission = snap.to_dict()
    submission["submission_id"] = submission_id

    exam_id = submission.get("exam_id")
    if not exam_id:
        return submission

    # Get short answer questions
    sa_questions = get_short_answer_questions_by_exam(exam_id)

    # Match with student answers
    answers = submission.get("answers", {})

    graded_questions = []
    for q in sa_questions:
        q_no = q.get("question_no")
        answer_key = f"sa_{q_no}"
        student_answer = answers.get(answer_key, "")

        graded_questions.append(
            {
                "question_no": q_no,
                "question_text": q.get("question_text", ""),
                "sample_answer": q.get("sample_answer", ""),
                "max_marks": q.get("marks", 0),
                "student_answer": student_answer,
                "awarded_marks": 0,  # Default, will be updated
                "feedback": "",
            }
        )

    submission["short_answer_questions"] = graded_questions

    return submission


def save_short_answer_grades(submission_id: str, grades: Dict) -> None:
    """
    Save short answer grades

    Args:
        submission_id: The submission document ID
        grades: Dictionary with question_no as keys and grade info as values
               e.g., {"1": {"marks": 5, "feedback": "Good answer"}}
    """
    doc_ref = db.collection("submissions").document(submission_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise ValueError("Submission not found")

    # Calculate total short answer marks
    total_sa_marks = 0
    obtained_sa_marks = 0

    graded_questions = []
    for q_no, grade_info in grades.items():
        marks = grade_info.get("marks", 0)
        max_marks = grade_info.get("max_marks", 0)
        feedback = grade_info.get("feedback", "")

        total_sa_marks += max_marks
        obtained_sa_marks += marks

        graded_questions.append(
            {
                "question_no": q_no,
                "awarded_marks": marks,
                "max_marks": max_marks,
                "feedback": feedback,
            }
        )

    # Update submission
    update_data = {
        "short_answer_grades": grades,
        "short_answer_graded_questions": graded_questions,
        "sa_total_marks": total_sa_marks,
        "sa_obtained_marks": obtained_sa_marks,
        "sa_graded_at": datetime.utcnow(),
        "sa_grading_complete": True,
    }

    # Calculate overall score (MCQ + SA)
    submission_data = snap.to_dict()
    mcq_obtained = submission_data.get("mcq_score", 0)
    mcq_total = submission_data.get("mcq_total", 0)

    overall_total = mcq_total + total_sa_marks
    overall_obtained = mcq_obtained + obtained_sa_marks
    overall_percentage = (
        (overall_obtained / overall_total * 100) if overall_total > 0 else 0
    )

    update_data.update(
        {
            "overall_total_marks": overall_total,
            "overall_obtained_marks": overall_obtained,
            "overall_percentage": round(overall_percentage, 2),
        }
    )

    doc_ref.update(update_data)


def get_all_submissions_for_exam(exam_id: str) -> List[Dict]:
    """
    Get all submissions for an exam with grading status
    """
    query = db.collection("submissions").where("exam_id", "==", exam_id).stream()

    submissions = []
    for doc in query:
        data = doc.to_dict()
        data["submission_id"] = doc.id

        # Check grading status
        mcq_graded = data.get("grading_result") is not None
        sa_graded = data.get("sa_grading_complete", False)

        data["mcq_graded"] = mcq_graded
        data["sa_graded"] = sa_graded
        data["fully_graded"] = mcq_graded and (sa_graded or not has_short_answers(data))

        submissions.append(data)

    return submissions


def has_short_answers(submission: Dict) -> bool:
    """
    Check if submission has short answer questions
    """
    answers = submission.get("answers", {})
    for key in answers.keys():
        if key.startswith("sa_"):
            return True
    return False
