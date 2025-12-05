"""
Student Result Service
Handles student result viewing with release date validation
"""

from typing import Optional, Dict
from datetime import datetime

from services.exam_service import get_exam_by_id
from services.grading_service import get_student_submission


def check_results_released(exam_id: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Check if results are released for an exam

    Returns:
        tuple: (is_released, release_date, release_time)
    """
    exam = get_exam_by_id(exam_id)
    if not exam:
        return False, None, None

    release_date = exam.get("result_release_date")
    release_time = exam.get("result_release_time", "00:00")

    if not release_date:
        return False, None, None

    try:
        release_datetime_str = f"{release_date} {release_time}"
        release_dt = datetime.strptime(release_datetime_str, "%Y-%m-%d %H:%M")
        now = datetime.now()

        is_released = now >= release_dt
        return is_released, release_date, release_time
    except ValueError:
        return False, release_date, release_time


def get_student_result(exam_id: str, student_id: str) -> Optional[Dict]:
    """
    Get complete result for a student including all questions and answers
    """
    from services.question_service import (
        get_mcq_questions_by_exam,
        get_short_answer_questions_by_exam,
    )

    # Get submission
    submission = get_student_submission(exam_id, student_id)
    if not submission:
        return None

    # Get exam details
    exam = get_exam_by_id(exam_id)
    if not exam:
        return None

    # Get all questions
    mcq_questions = get_mcq_questions_by_exam(exam_id)
    sa_questions = get_short_answer_questions_by_exam(exam_id)

    # Get student answers
    answers = submission.get("answers", {})

    # Process MCQ results
    mcq_results = []
    grading_result = submission.get("grading_result", {})
    question_results = grading_result.get("question_results", [])

    for q in mcq_questions:
        q_no = q.get("question_no")
        answer_key = f"mcq_{q_no}"
        student_answer = answers.get(answer_key, "Not answered")

        # Find result for this question
        q_result = next(
            (r for r in question_results if r.get("question_no") == q_no), {}
        )

        mcq_results.append(
            {
                "question_no": q_no,
                "question_text": q.get("question_text", ""),
                "option_a": q.get("option_a", ""),
                "option_b": q.get("option_b", ""),
                "option_c": q.get("option_c", ""),
                "option_d": q.get("option_d", ""),
                "correct_answer": q.get("correct_option", ""),
                "student_answer": student_answer,
                "is_correct": q_result.get("is_correct", False),
                "marks": q.get("marks", 0),
                "marks_obtained": q_result.get("marks_obtained", 0),
            }
        )

    # Process Short Answer results
    sa_results = []
    sa_grades = submission.get("short_answer_grades", {})

    for q in sa_questions:
        q_no = q.get("question_no")
        answer_key = f"sa_{q_no}"
        student_answer = answers.get(answer_key, "Not answered")

        # Get grading info
        grade_info = sa_grades.get(str(q_no), {})

        sa_results.append(
            {
                "question_no": q_no,
                "question_text": q.get("question_text", ""),
                "sample_answer": q.get("sample_answer", ""),
                "student_answer": student_answer,
                "max_marks": grade_info.get("max_marks", q.get("marks", 0)),
                "awarded_marks": grade_info.get("marks", 0),
                "feedback": grade_info.get("feedback", ""),
            }
        )

    # Calculate totals
    mcq_total = submission.get("mcq_total", 0)
    mcq_obtained = submission.get("mcq_score", 0)
    sa_total = submission.get("sa_total_marks", 0)
    sa_obtained = submission.get("sa_obtained_marks", 0)

    overall_total = mcq_total + sa_total
    overall_obtained = mcq_obtained + sa_obtained
    overall_percentage = submission.get("overall_percentage", 0)

    return {
        "exam": exam,
        "submission": submission,
        "mcq_results": mcq_results,
        "sa_results": sa_results,
        "mcq_total": mcq_total,
        "mcq_obtained": mcq_obtained,
        "sa_total": sa_total,
        "sa_obtained": sa_obtained,
        "overall_total": overall_total,
        "overall_obtained": overall_obtained,
        "overall_percentage": overall_percentage,
        "submitted_at": submission.get("submitted_at"),
    }
