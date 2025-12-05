from datetime import datetime, timedelta
from typing import List


def validate_exam(title: str, description: str, duration: str, instructions: str):
    """
    Validate exam fields. Returns a list of error messages (empty if valid).
    """
    errors = []

    title = (title or "").strip()
    description = (description or "").strip()
    duration = (duration or "").strip()
    instructions = (instructions or "").strip()

    if not title:
        errors.append("Title is required.")
    if not description:
        errors.append("Description is required.")
    if not duration:
        errors.append("Duration is required.")
    elif not duration.isdigit() or int(duration) <= 0:
        errors.append("Duration must be a positive number.")
    if not instructions:
        errors.append("Instructions are required.")

    return errors


def validate_exam_date(exam_date: str):
    errors = []

    if not exam_date:
        errors.append("Exam date is required.")
        return errors

    try:
        selected_date = datetime.strptime(exam_date, "%Y-%m-%d").date()
        today = datetime.today().date()
        if selected_date < today:
            errors.append("Exam date cannot be in the past.")
    except ValueError:
        errors.append("Invalid exam date format.")

    return errors


def validate_exam_times(start_time: str, end_time: str, duration: str):
    """
    Validate start time, end time, and duration consistency
    """
    errors = []

    if not start_time:
        errors.append("Start time is required.")
    if not end_time:
        errors.append("End time is required.")

    if start_time and end_time and duration:
        try:
            # Parse times
            start_h, start_m = map(int, start_time.split(":"))
            end_h, end_m = map(int, end_time.split(":"))

            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m

            # Handle next day scenario
            if end_minutes <= start_minutes:
                end_minutes += 24 * 60

            calculated_duration = end_minutes - start_minutes
            provided_duration = int(duration)

            # Allow small discrepancy (1 minute) due to rounding
            if abs(calculated_duration - provided_duration) > 1:
                errors.append(
                    "Time mismatch: Start time and end time don't match the duration."
                )

        except (ValueError, AttributeError):
            errors.append("Invalid time format.")

    return errors


def validate_result_release_date(release_date: str, exam_date: str = None):
    """
    Validate result release date
    Optionally check if it's after the exam date
    """
    errors = []

    if not release_date:
        errors.append("Result release date is required.")
        return errors

    try:
        selected_date = datetime.strptime(release_date, "%Y-%m-%d").date()
        today = datetime.today().date()
        
        # Allow past dates for exams that have already occurred
        # but warn if it's too far in the past
        if selected_date < today - timedelta(days=365):
            errors.append("Result release date seems too far in the past.")
        
        # If exam_date is provided, ensure release date is on or after exam date
        if exam_date:
            try:
                exam_dt = datetime.strptime(exam_date, "%Y-%m-%d").date()
                if selected_date < exam_dt:
                    errors.append("Result release date cannot be before the exam date.")
            except ValueError:
                pass  # If exam_date is invalid, skip this check
                
    except ValueError:
        errors.append("Invalid result release date format.")

    return errors

def validate_grading_periods(
    exam_date: str,
    exam_end_time: str,
    grading_deadline_date: str,
    grading_deadline_time: str,
    release_date: str,
    release_time: str
) -> List[str]:
    """
    Validate all date/time relationships for grading and result release
    
    Timeline must be: Exam End → Grading Deadline → Result Release
    
    Args:
        exam_date: Date of the exam (YYYY-MM-DD)
        exam_end_time: End time of exam (HH:MM)
        grading_deadline_date: Deadline for lecturers to finish grading
        grading_deadline_time: Time for grading deadline
        release_date: When results are released to students
        release_time: Time for result release
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Check for required fields
    if not exam_date:
        errors.append("Exam date is required")
        return errors
    
    if not exam_end_time:
        errors.append("Exam end time is required")
        return errors
    
    if not grading_deadline_date:
        errors.append("Grading deadline date is required")
    
    if not grading_deadline_time:
        errors.append("Grading deadline time is required")
    
    if not release_date:
        errors.append("Result release date is required")
    
    if not release_time:
        errors.append("Result release time is required")
    
    if errors:
        return errors
    
    # Parse all datetime values
    try:
        exam_end_str = f"{exam_date} {exam_end_time}"
        exam_end_dt = datetime.strptime(exam_end_str, "%Y-%m-%d %H:%M")
    except ValueError as e:
        errors.append(f"Invalid exam date/time format: {e}")
        return errors
    
    try:
        grading_deadline_str = f"{grading_deadline_date} {grading_deadline_time}"
        grading_deadline_dt = datetime.strptime(grading_deadline_str, "%Y-%m-%d %H:%M")
    except ValueError as e:
        errors.append(f"Invalid grading deadline format: {e}")
        return errors
    
    try:
        release_str = f"{release_date} {release_time}"
        release_dt = datetime.strptime(release_str, "%Y-%m-%d %H:%M")
    except ValueError as e:
        errors.append(f"Invalid result release format: {e}")
        return errors
    
    # Get current time for validation
    now = datetime.now()
    
    # ============================================
    # RULE 1: Grading deadline must be AFTER exam end
    # ============================================
    if grading_deadline_dt <= exam_end_dt:
        errors.append(
            f"⚠️ Grading deadline must be AFTER the exam ends. "
            f"Exam ends at {exam_end_str}, but grading deadline is {grading_deadline_str}"
        )
    
    # ============================================
    # RULE 2: Minimum grading time (at least 24 hours)
    # ============================================
    min_grading_time = timedelta(hours=24)
    time_gap = grading_deadline_dt - exam_end_dt
    
    if time_gap < min_grading_time:
        hours_available = time_gap.total_seconds() / 3600
        errors.append(
            f"⏰ Grading period too short. Lecturers need at least 24 hours to grade. "
            f"Current gap: {hours_available:.1f} hours"
        )
    
    # ============================================
    # RULE 3: Result release must be AFTER grading deadline
    # ============================================
    if release_dt <= grading_deadline_dt:
        errors.append(
            f"⚠️ Result release must be AFTER grading deadline. "
            f"Grading deadline: {grading_deadline_str}, Release: {release_str}"
        )
    
    # ============================================
    # RULE 4: Minimum verification time (at least 1 hour)
    # ============================================
    min_verification_time = timedelta(hours=1)
    verification_gap = release_dt - grading_deadline_dt
    
    if verification_gap < min_verification_time:
        errors.append(
            f"⏱️ Need at least 1 hour between grading deadline and result release "
            f"for verification and quality checks"
        )
    
    # ============================================
    # RULE 5: No dates in the past (with 1-hour grace period)
    # ============================================
    grace_period = timedelta(hours=1)
    
    if grading_deadline_dt < (now - grace_period):
        errors.append(
            f"📅 Grading deadline cannot be in the past "
            f"(Deadline: {grading_deadline_str}, Current: {now.strftime('%Y-%m-%d %H:%M')})"
        )
    
    if release_dt < (now - grace_period):
        errors.append(
            f"📅 Result release date cannot be in the past "
            f"(Release: {release_str}, Current: {now.strftime('%Y-%m-%d %H:%M')})"
        )
    
    # ============================================
    # RULE 6: Maximum reasonable gap (30 days)
    # ============================================
    max_gap = timedelta(days=30)
    total_gap = release_dt - exam_end_dt
    
    if total_gap > max_gap:
        errors.append(
            f"⏳ Result release is too far in the future. "
            f"Maximum 30 days after exam, but scheduled for {total_gap.days} days later"
        )
    
    # ============================================
    # RULE 7: Reasonable grading period (max 14 days)
    # ============================================
    max_grading_period = timedelta(days=14)
    
    if time_gap > max_grading_period:
        errors.append(
            f"⚠️ Grading period is unusually long ({time_gap.days} days). "
            f"Consider setting an earlier deadline to release results faster"
        )
    
    return errors


def validate_result_release_date(release_date: str, exam_date: str) -> List[str]:
    """
    Validate result release date (simplified version)
    Used by the legacy set_result_release endpoint
    
    Args:
        release_date: Result release date (YYYY-MM-DD)
        exam_date: Exam date (YYYY-MM-DD)
    
    Returns:
        List of error messages
    """
    errors = []
    
    if not release_date:
        errors.append("Result release date is required")
        return errors
    
    if not exam_date:
        errors.append("Exam date is required")
        return errors
    
    try:
        release_dt = datetime.strptime(release_date, "%Y-%m-%d")
        exam_dt = datetime.strptime(exam_date, "%Y-%m-%d")
    except ValueError as e:
        errors.append(f"Invalid date format: {e}")
        return errors
    
    # Release date must be after exam date
    if release_dt <= exam_dt:
        errors.append(
            f"Result release date must be AFTER exam date. "
            f"Exam: {exam_date}, Release: {release_date}"
        )
    
    # Not too far in the past
    now = datetime.now()
    if release_dt < now.replace(hour=0, minute=0, second=0, microsecond=0):
        errors.append("Result release date cannot be in the past")
    
    return errors


def validate_grade_submission(
    question_grades: dict,
    questions: list
) -> List[str]:
    """
    Validate individual grade submissions for short answer questions
    
    Args:
        question_grades: Dict of grades {q_no: {marks, feedback, max_marks}}
        questions: List of question dictionaries
    
    Returns:
        List of error messages
    """
    errors = []
    
    for q in questions:
        q_no = str(q.get("question_no"))
        max_marks = q.get("marks", 0)
        
        # Check if grade exists
        if q_no not in question_grades:
            errors.append(f"Missing grade for Question {q_no}")
            continue
        
        grade_info = question_grades[q_no]
        awarded = grade_info.get("marks", 0)
        
        # Validate marks are numeric
        try:
            awarded = float(awarded)
        except (ValueError, TypeError):
            errors.append(f"Q{q_no}: Invalid marks value (must be a number)")
            continue
        
        # Check marks range
        if awarded < 0:
            errors.append(f"Q{q_no}: Marks cannot be negative (got {awarded})")
        
        if awarded > max_marks:
            errors.append(
                f"Q{q_no}: Awarded marks ({awarded}) exceed maximum ({max_marks})"
            )
        
        # Check for decimal precision (max 1 decimal place)
        if awarded * 10 % 1 != 0:
            errors.append(
                f"Q{q_no}: Marks can only have 1 decimal place (got {awarded})"
            )
    
    return errors


def validate_exam_finalization(exam_id: str, submissions: list) -> List[str]:
    """
    Validate that an exam is ready to be finalized
    
    Args:
        exam_id: Exam identifier
        submissions: List of submission dictionaries
    
    Returns:
        List of error messages preventing finalization
    """
    errors = []
    
    if not submissions:
        errors.append("No submissions found for this exam")
        return errors
    
    # Check if all submissions are fully graded
    ungraded_students = []
    
    for sub in submissions:
        student_id = sub.get("student_id", "Unknown")
        mcq_graded = sub.get("mcq_graded", False)
        sa_graded = sub.get("sa_graded", False)
        
        if not mcq_graded:
            ungraded_students.append(f"{student_id} (MCQ pending)")
        elif not sa_graded:
            ungraded_students.append(f"{student_id} (Short answers pending)")
    
    if ungraded_students:
        errors.append(
            f"Cannot finalize: {len(ungraded_students)} student(s) still need grading:"
        )
        for student in ungraded_students[:5]:  # Show first 5
            errors.append(f"  • {student}")
        
        if len(ungraded_students) > 5:
            errors.append(f"  ... and {len(ungraded_students) - 5} more")
    
    return errors