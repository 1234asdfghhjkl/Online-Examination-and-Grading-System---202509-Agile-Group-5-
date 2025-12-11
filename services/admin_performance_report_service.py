"""
Student Performance Report Service
Generates comprehensive analytics and statistics for exam performance
"""

from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from core.firebase_db import db
from services.exam_service import get_exam_by_id


def get_exam_performance_report(exam_id: str) -> Optional[Dict]:
    """
    Generate comprehensive performance report for an exam

    Returns:
        Dictionary containing all performance metrics and analytics
    """
    exam = get_exam_by_id(exam_id)
    if not exam:
        return None

    # Get all submissions
    submissions_query = (
        db.collection("submissions").where("exam_id", "==", exam_id).stream()
    )
    submissions = [doc.to_dict() for doc in submissions_query]

    if not submissions:
        return {
            "exam": exam,
            "total_students": 0,
            "submissions_count": 0,
            "error": "No submissions found for this exam",
        }

    # Calculate comprehensive statistics
    report = {
        "exam": exam,
        "exam_id": exam_id,
        "exam_title": exam.get("title", ""),
        "exam_date": exam.get("exam_date", ""),
        "total_students": len(submissions),
        "submissions_count": len(submissions),
        # Overall statistics
        "overall_stats": calculate_overall_statistics(submissions),
        # MCQ statistics
        "mcq_stats": calculate_mcq_statistics(submissions),
        # Short answer statistics
        "sa_stats": calculate_short_answer_statistics(submissions),
        # Grade distribution
        "grade_distribution": calculate_grade_distribution(submissions),
        # Performance by question
        "question_performance": calculate_question_performance(exam_id, submissions),
        # Time analysis
        "time_analysis": calculate_time_analysis(submissions),
        # Top performers
        "top_performers": get_top_performers(submissions, limit=10),
        # Students needing support
        "students_at_risk": get_students_at_risk(submissions),
    }

    return report


def calculate_overall_statistics(submissions: List[Dict]) -> Dict:
    """Calculate overall exam statistics"""
    if not submissions:
        return {}

    percentages = [sub.get("overall_percentage", 0) for sub in submissions]
    total_marks = [sub.get("overall_total_marks", 0) for sub in submissions]
    obtained_marks = [sub.get("overall_obtained_marks", 0) for sub in submissions]

    avg_percentage = sum(percentages) / len(percentages)
    avg_obtained = sum(obtained_marks) / len(obtained_marks)
    avg_total = sum(total_marks) / len(total_marks) if total_marks else 0

    # Pass/Fail analysis (50% threshold)
    passed = len([p for p in percentages if p >= 50])
    failed = len(percentages) - passed
    pass_rate = (passed / len(percentages) * 100) if percentages else 0

    # Standard deviation
    mean = avg_percentage
    variance = sum((x - mean) ** 2 for x in percentages) / len(percentages)
    std_dev = variance**0.5

    return {
        "average_percentage": round(avg_percentage, 2),
        "average_marks": round(avg_obtained, 2),
        "total_possible_marks": round(avg_total, 2),
        "highest_score": round(max(percentages), 2),
        "lowest_score": round(min(percentages), 2),
        "median_score": round(sorted(percentages)[len(percentages) // 2], 2),
        "standard_deviation": round(std_dev, 2),
        "passed_count": passed,
        "failed_count": failed,
        "pass_rate": round(pass_rate, 2),
    }


def calculate_mcq_statistics(submissions: List[Dict]) -> Dict:
    """Calculate MCQ-specific statistics"""
    if not submissions:
        return {}

    mcq_scores = [sub.get("mcq_score", 0) for sub in submissions]
    mcq_totals = [sub.get("mcq_total", 0) for sub in submissions]
    mcq_percentages = [
        (score / total * 100) if total > 0 else 0
        for score, total in zip(mcq_scores, mcq_totals)
    ]

    return {
        "average_score": round(sum(mcq_scores) / len(mcq_scores), 2),
        "average_percentage": round(sum(mcq_percentages) / len(mcq_percentages), 2),
        "highest_score": max(mcq_scores),
        "lowest_score": min(mcq_scores),
        "total_marks": mcq_totals[0] if mcq_totals else 0,
    }


def calculate_short_answer_statistics(submissions: List[Dict]) -> Dict:
    """Calculate short answer statistics"""
    if not submissions:
        return {}

    sa_scores = [sub.get("sa_obtained_marks", 0) for sub in submissions]
    sa_totals = [sub.get("sa_total_marks", 0) for sub in submissions]
    sa_percentages = [
        (score / total * 100) if total > 0 else 0
        for score, total in zip(sa_scores, sa_totals)
    ]

    # Filter out submissions with no short answers
    valid_sa = [
        (s, t, p) for s, t, p in zip(sa_scores, sa_totals, sa_percentages) if t > 0
    ]

    if not valid_sa:
        return {
            "has_short_answers": False,
            "average_score": 0,
            "average_percentage": 0,
        }

    scores, totals, percentages = zip(*valid_sa)

    return {
        "has_short_answers": True,
        "average_score": round(sum(scores) / len(scores), 2),
        "average_percentage": round(sum(percentages) / len(percentages), 2),
        "highest_score": max(scores),
        "lowest_score": min(scores),
        "total_marks": totals[0] if totals else 0,
    }


def calculate_grade_distribution(submissions: List[Dict]) -> Dict:
    """Calculate grade distribution with percentage breakdown"""
    distribution = {
        "A": {"count": 0, "range": "80-100%", "students": []},
        "B": {"count": 0, "range": "70-79%", "students": []},
        "C": {"count": 0, "range": "60-69%", "students": []},
        "D": {"count": 0, "range": "50-59%", "students": []},
        "F": {"count": 0, "range": "0-49%", "students": []},
    }

    for sub in submissions:
        percentage = sub.get("overall_percentage", 0)
        student_id = sub.get("student_id", "Unknown")

        if percentage >= 80:
            distribution["A"]["count"] += 1
            distribution["A"]["students"].append(student_id)
        elif percentage >= 70:
            distribution["B"]["count"] += 1
            distribution["B"]["students"].append(student_id)
        elif percentage >= 60:
            distribution["C"]["count"] += 1
            distribution["C"]["students"].append(student_id)
        elif percentage >= 50:
            distribution["D"]["count"] += 1
            distribution["D"]["students"].append(student_id)
        else:
            distribution["F"]["count"] += 1
            distribution["F"]["students"].append(student_id)

    return distribution


def calculate_question_performance(exam_id: str, submissions: List[Dict]) -> Dict:
    """Analyze performance by individual question"""
    from services.question_service import get_mcq_questions_by_exam

    mcq_questions = get_mcq_questions_by_exam(exam_id)

    question_stats = {}

    for q in mcq_questions:
        q_no = q.get("question_no")
        q_text = q.get("question_text", "")
        max_marks = q.get("marks", 0)

        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0

        for sub in submissions:
            grading_result = sub.get("grading_result", {})
            question_results = grading_result.get("question_results", [])

            q_result = next(
                (r for r in question_results if r.get("question_no") == q_no), None
            )

            if q_result:
                if q_result.get("student_answer") in ["", "Not answered"]:
                    unanswered_count += 1
                elif q_result.get("is_correct"):
                    correct_count += 1
                else:
                    incorrect_count += 1

        total_responses = correct_count + incorrect_count + unanswered_count

        question_stats[f"Q{q_no}"] = {
            "question_text": q_text[:100] + "..." if len(q_text) > 100 else q_text,
            "correct": correct_count,
            "incorrect": incorrect_count,
            "unanswered": unanswered_count,
            "success_rate": round(
                (correct_count / total_responses * 100) if total_responses > 0 else 0, 2
            ),
            "max_marks": max_marks,
        }

    return question_stats


def calculate_time_analysis(submissions: List[Dict]) -> Dict:
    """Analyze submission timing patterns"""
    submission_times = []

    for sub in submissions:
        submitted_at = sub.get("submitted_at")
        if submitted_at and isinstance(submitted_at, datetime):
            submission_times.append(submitted_at)

    if not submission_times:
        return {"has_data": False}

    # Sort times
    submission_times.sort()

    # Calculate time distribution
    time_distribution = defaultdict(int)
    for dt in submission_times:
        hour = dt.hour
        time_distribution[hour] += 1

    return {
        "has_data": True,
        "earliest_submission": submission_times[0].strftime("%Y-%m-%d %H:%M:%S"),
        "latest_submission": submission_times[-1].strftime("%Y-%m-%d %H:%M:%S"),
        "time_distribution": dict(time_distribution),
    }


def get_top_performers(submissions: List[Dict], limit: int = 10) -> List[Dict]:
    """Get top performing students"""
    sorted_submissions = sorted(
        submissions, key=lambda x: x.get("overall_percentage", 0), reverse=True
    )

    top = []
    for sub in sorted_submissions[:limit]:
        top.append(
            {
                "student_id": sub.get("student_id", "Unknown"),
                "percentage": round(sub.get("overall_percentage", 0), 2),
                "total_marks": sub.get("overall_obtained_marks", 0),
                "mcq_score": sub.get("mcq_score", 0),
                "sa_score": sub.get("sa_obtained_marks", 0),
            }
        )

    return top


def get_students_at_risk(submissions: List[Dict], threshold: float = 50) -> List[Dict]:
    """Identify students who failed or are at risk"""
    at_risk = []

    for sub in submissions:
        percentage = sub.get("overall_percentage", 0)
        if percentage < threshold:
            at_risk.append(
                {
                    "student_id": sub.get("student_id", "Unknown"),
                    "percentage": round(percentage, 2),
                    "total_marks": sub.get("overall_obtained_marks", 0),
                    "areas_of_concern": identify_weak_areas(sub),
                }
            )

    return sorted(at_risk, key=lambda x: x["percentage"])


def identify_weak_areas(submission: Dict) -> List[str]:
    """Identify specific areas where student struggled"""
    concerns = []

    mcq_percentage = (
        (submission.get("mcq_score", 0) / submission.get("mcq_total", 1)) * 100
        if submission.get("mcq_total", 0) > 0
        else 0
    )

    sa_percentage = (
        (submission.get("sa_obtained_marks", 0) / submission.get("sa_total_marks", 1))
        * 100
        if submission.get("sa_total_marks", 0) > 0
        else 0
    )

    if mcq_percentage < 50:
        concerns.append(f"MCQ: {round(mcq_percentage, 1)}%")

    if sa_percentage < 50 and submission.get("sa_total_marks", 0) > 0:
        concerns.append(f"Short Answers: {round(sa_percentage, 1)}%")

    return concerns if concerns else ["Overall performance"]
