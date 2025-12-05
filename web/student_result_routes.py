"""
Student Result Routes
Handles student result viewing
"""

import html

from services.student_result_service import check_results_released, get_student_result
from services.exam_service import get_exam_by_id
from .template_engine import render


def get_student_result_view(exam_id: str, student_id: str):
    """
    GET handler for student result view
    """
    if not exam_id or not student_id:
        content_html = """
        <div class="alert alert-danger">
            <h4>Error</h4>
            <p>Missing exam ID or student ID.</p>
        </div>
        """
        html_str = render(
            "student_result.html",
            {"content_html": content_html, "student_id": student_id},
        )
        return html_str, 400

    # Check if results are released
    is_released, release_date, release_time = check_results_released(exam_id)

    if not is_released:
        exam = get_exam_by_id(exam_id)
        exam_title = exam.get("title", "Exam") if exam else "Exam"

        if release_date:
            release_display = f"{release_date} at {release_time}"
            content_html = f"""
            <div class="release-pending">
                <h2>⏰ Results Not Yet Released</h2>
                <p class="mb-3 fs-5">Results for <strong>{html.escape(exam_title)}</strong> will be available on:</p>
                <h3 class="mb-0">{release_display}</h3>
                <p class="mt-4 mb-0">
                    <a href="/student?student_id={html.escape(student_id)}" 
                       class="btn btn-light">Return to Dashboard</a>
                </p>
            </div>
            """
        else:
            content_html = f"""
            <div class="release-pending">
                <h2>⏰ Results Not Yet Released</h2>
                <p class="mb-3 fs-5">Results for <strong>{html.escape(exam_title)}</strong> have not been released yet.</p>
                <p class="text-white-50">The instructor has not set a release date yet. Please check back later.</p>
                <p class="mt-4 mb-0">
                    <a href="/student?student_id={html.escape(student_id)}" 
                       class="btn btn-light">Return to Dashboard</a>
                </p>
            </div>
            """

        html_str = render(
            "student_result.html",
            {"content_html": content_html, "student_id": student_id},
        )
        return html_str, 200

    # Get student result
    result_data = get_student_result(exam_id, student_id)

    if not result_data:
        content_html = """
        <div class="alert alert-warning">
            <h4>No Submission Found</h4>
            <p>You have not submitted this exam yet.</p>
        </div>
        """
        html_str = render(
            "student_result.html",
            {"content_html": content_html, "student_id": student_id},
        )
        return html_str, 404

    # Build result HTML
    exam = result_data["exam"]
    submitted_at = result_data["submitted_at"]
    submitted_time = (
        submitted_at.strftime("%Y-%m-%d %H:%M:%S") if submitted_at else "N/A"
    )

    # Header with overall score
    content_html = f"""
    <div class="result-header">
        <div class="d-flex justify-content-between align-items-start mb-3">
        <h2>{html.escape(exam.get('title', 'Exam'))}</h2>
        <a href="/student-result-pdf?exam_id={exam_id}&student_id={student_id}" 
           class="btn btn-light" 
           download>
            📄 Download PDF
        </a>
    </div>
        <div class="row">
            <div class="col-md-4">
                <div class="score-card">
                    <div class="text-muted mb-2">Total Score</div>
                    <div class="score-value">{result_data['overall_obtained']}/{result_data['overall_total']}</div>
                    <div class="text-muted">{result_data['overall_percentage']}%</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="score-card">
                    <div class="text-muted mb-2">MCQ Score</div>
                    <div class="score-value">{result_data['mcq_obtained']}/{result_data['mcq_total']}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="score-card">
                    <div class="text-muted mb-2">Short Answer Score</div>
                    <div class="score-value">{result_data['sa_obtained']}/{result_data['sa_total']}</div>
                </div>
            </div>
        </div>
        <p class="mt-3 mb-0"><small>📅 Submitted: {submitted_time}</small></p>
    </div>
    """

    # MCQ Results
    if result_data["mcq_results"]:
        content_html += """
        <h4 class="mb-3">📝 Multiple Choice Questions</h4>
        """

        for q in result_data["mcq_results"]:
            is_correct = q["is_correct"]
            card_class = "correct-answer" if is_correct else "incorrect-answer"
            icon = "✅" if is_correct else "❌"

            content_html += f"""
            <div class="question-card">
                <h5>Question {q['question_no']} {icon} ({q['marks_obtained']}/{q['marks']} marks)</h5>
                <p><strong>{html.escape(q['question_text'])}</strong></p>
                
                <div class="mb-2">
                    <span class="option-badge {'option-correct' if q['correct_answer'] == 'A' else ('option-incorrect' if q['student_answer'] == 'A' and not is_correct else 'option-neutral')}">A</span>
                    {html.escape(q['option_a'])}
                    {' ✓ Correct' if q['correct_answer'] == 'A' else ''}
                </div>
                <div class="mb-2">
                    <span class="option-badge {'option-correct' if q['correct_answer'] == 'B' else ('option-incorrect' if q['student_answer'] == 'B' and not is_correct else 'option-neutral')}">B</span>
                    {html.escape(q['option_b'])}
                    {' ✓ Correct' if q['correct_answer'] == 'B' else ''}
                </div>
                <div class="mb-2">
                    <span class="option-badge {'option-correct' if q['correct_answer'] == 'C' else ('option-incorrect' if q['student_answer'] == 'C' and not is_correct else 'option-neutral')}">C</span>
                    {html.escape(q['option_c'])}
                    {' ✓ Correct' if q['correct_answer'] == 'C' else ''}
                </div>
                <div class="mb-2">
                    <span class="option-badge {'option-correct' if q['correct_answer'] == 'D' else ('option-incorrect' if q['student_answer'] == 'D' and not is_correct else 'option-neutral')}">D</span>
                    {html.escape(q['option_d'])}
                    {' ✓ Correct' if q['correct_answer'] == 'D' else ''}
                </div>
                
                <div class="{card_class} mt-3">
                    <strong>Your Answer:</strong> {html.escape(str(q['student_answer']))}
                    <br>
                    <strong>Correct Answer:</strong> {html.escape(q['correct_answer'])}
                </div>
            </div>
            """

    # Short Answer Results
    if result_data["sa_results"]:
        content_html += """
        <h4 class="mb-3 mt-4">✍️ Short Answer Questions</h4>
        """

        for q in result_data["sa_results"]:
            content_html += f"""
            <div class="question-card">
                <h5>Question {q['question_no']} ({q['awarded_marks']}/{q['max_marks']} marks)</h5>
                <p><strong>{html.escape(q['question_text'])}</strong></p>
                
                <div class="mt-3">
                    <strong>📝 Your Answer:</strong>
                    <div class="p-3 bg-light rounded mt-2">
                        {html.escape(q['student_answer']) if q['student_answer'] != 'Not answered' else '<em class="text-muted">No answer provided</em>'}
                    </div>
                </div>
                
                {f'''
                <div class="mt-3">
                    <strong>📚 Sample Answer (Reference):</strong>
                    <div class="p-3 bg-light rounded mt-2">
                        {html.escape(q['sample_answer'])}
                    </div>
                </div>
                ''' if q['sample_answer'] else ''}
                
                {f'''
                <div class="feedback-box">
                    <strong>💬 Instructor Feedback:</strong>
                    <p class="mb-0 mt-2">{html.escape(q['feedback'])}</p>
                </div>
                ''' if q['feedback'] else ''}
            </div>
            """

    html_str = render(
        "student_result.html", {"content_html": content_html, "student_id": student_id}
    )
    return html_str, 200


def get_student_result_pdf(exam_id: str, student_id: str):
    """
    GET handler for downloading student result as PDF
    """
    from services.pdf_service import generate_result_pdf

    if not exam_id or not student_id:
        return "Error: Missing exam ID or student ID", 400

    # Check if results are released
    is_released, release_date, release_time = check_results_released(exam_id)

    if not is_released:
        return "Error: Results not yet released", 403

    # Get student result
    result_data = get_student_result(exam_id, student_id)

    if not result_data:
        return "Error: No submission found", 404

    # Generate PDF
    pdf_bytes = generate_result_pdf(result_data)

    # Return PDF with appropriate headers
    exam = result_data["exam"]
    filename = f"result_{exam.get('title', 'exam').replace(' ', '_')}_{student_id}.pdf"

    return (
        pdf_bytes,
        200,
        {
            "Content-Type": "application/pdf",
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
