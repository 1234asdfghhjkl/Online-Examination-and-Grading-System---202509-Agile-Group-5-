"""
Created on 2025-11/27
By Liyi
Grading Service
Handles automatic grading of MCQ questions
"""

from typing import Dict, List, Optional
from datetime import datetime

from core.firebase_db import db
from services.question_service import get_mcq_questions_by_exam


def grade_mcq_submission(exam_id: str, student_id: str, answers: Dict) -> Dict:
    """
    Auto-grade MCQ answers for a submission
    
    Args:
        exam_id: The exam identifier
        student_id: The student identifier
        answers: Dictionary of student answers (e.g., {"mcq_1": "A", "mcq_2": "B"})
    
    Returns:
        Dictionary containing grading results
    """
    # Get all MCQ questions for this exam
    mcq_questions = get_mcq_questions_by_exam(exam_id)
    
    if not mcq_questions:
        return {
            "total_marks": 0,
            "obtained_marks": 0,
            "percentage": 0,
            "total_questions": 0,
            "correct_answers": 0,
            "incorrect_answers": 0,
            "unanswered": 0,
            "question_results": []
        }
    
    total_marks = 0
    obtained_marks = 0
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0
    question_results = []
    
    for question in mcq_questions:
        q_no = question.get("question_no")
        correct_option = question.get("correct_option")
        marks = question.get("marks", 0)
        
        # Build the answer key (e.g., "mcq_1")
        answer_key = f"mcq_{q_no}"
        student_answer = answers.get(answer_key, "").strip().upper()
        
        total_marks += marks
        
        # Check if answered
        if not student_answer:
            unanswered_count += 1
            is_correct = False
            marks_obtained = 0
        elif student_answer == correct_option:
            correct_count += 1
            is_correct = True
            marks_obtained = marks
            obtained_marks += marks
        else:
            incorrect_count += 1
            is_correct = False
            marks_obtained = 0
        
        question_results.append({
            "question_no": q_no,
            "question_text": question.get("question_text", ""),
            "student_answer": student_answer or "Not answered",
            "correct_answer": correct_option,
            "is_correct": is_correct,
            "marks": marks,
            "marks_obtained": marks_obtained
        })
    
    # Calculate percentage
    percentage = (obtained_marks / total_marks * 100) if total_marks > 0 else 0
    
    grading_result = {
        "total_marks": total_marks,
        "obtained_marks": obtained_marks,
        "percentage": round(percentage, 2),
        "total_questions": len(mcq_questions),
        "correct_answers": correct_count,
        "incorrect_answers": incorrect_count,
        "unanswered": unanswered_count,
        "question_results": question_results,
        "graded_at": datetime.utcnow()
    }
    
    return grading_result


def save_grading_result(submission_id: str, grading_result: Dict) -> None:
    """
    Save grading results to the submission document
    """
    if not submission_id:
        return
    
    doc_ref = db.collection("submissions").document(submission_id)
    doc_ref.update({
        "grading_result": grading_result,
        "mcq_score": grading_result["obtained_marks"],
        "mcq_total": grading_result["total_marks"],
        "mcq_percentage": grading_result["percentage"],
        "graded_at": datetime.utcnow()
    })


def get_submission_result(submission_id: str) -> Optional[Dict]:
    """
    Retrieve grading results for a submission
    """
    if not submission_id:
        return None
    
    doc_ref = db.collection("submissions").document(submission_id)
    snap = doc_ref.get()
    
    if not snap.exists:
        return None
    
    return snap.to_dict()


def get_student_submission(exam_id: str, student_id: str) -> Optional[Dict]:
    """
    Get a student's submission for an exam
    """
    query = (
        db.collection("submissions")
        .where("exam_id", "==", exam_id)
        .where("student_id", "==", student_id)
        .limit(1)
    )
    
    for doc in query.stream():
        data = doc.to_dict()
        data["submission_id"] = doc.id
        return data
    
    return None