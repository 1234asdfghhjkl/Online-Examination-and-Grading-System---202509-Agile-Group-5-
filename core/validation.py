from datetime import datetime


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
            start_h, start_m = map(int, start_time.split(':'))
            end_h, end_m = map(int, end_time.split(':'))
            
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            
            # Handle next day scenario
            if end_minutes <= start_minutes:
                end_minutes += 24 * 60
            
            calculated_duration = end_minutes - start_minutes
            provided_duration = int(duration)
            
            # Allow small discrepancy (1 minute) due to rounding
            if abs(calculated_duration - provided_duration) > 1:
                errors.append(f"Time mismatch: Start time and end time don't match the duration.")
                
        except (ValueError, AttributeError):
            errors.append("Invalid time format.")
    
    return errors