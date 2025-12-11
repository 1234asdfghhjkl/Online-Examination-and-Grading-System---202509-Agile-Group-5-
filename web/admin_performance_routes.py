"""
Performance Report Routes - IMPROVED VERSION
Handles admin performance analytics with better no-data UI
"""

import html
import json

from services.admin_performance_report_service import get_exam_performance_report
from .template_engine import render


def get_performance_report(exam_id: str):
    """
    GET handler for exam performance report
    Displays comprehensive analytics and statistics
    """
    if not exam_id:
        error_html = """
        <div class="container mt-5">
            <div class="alert alert-danger">
                <h4>Error</h4>
                <p>Missing exam ID</p>
                <a href="/admin/exam-list" class="btn btn-secondary">Back to Exam List</a>
            </div>
        </div>
        """
        return error_html, 400

    # Get the performance report
    report = get_exam_performance_report(exam_id)
    
    if not report:
        error_html = f"""
        <div class="container mt-5">
            <div class="alert alert-danger">
                <h4>Error</h4>
                <p>Could not generate performance report for exam "{html.escape(exam_id)}"</p>
                <a href="/admin/exam-list" class="btn btn-secondary">Back to Exam List</a>
            </div>
        </div>
        """
        return error_html, 404

    # ==========================================
    # IMPROVED: Handle "No Submissions" Case
    # ==========================================
    if "error" in report:
        exam = report.get("exam", {})
        exam_title = exam.get("title", "Exam") if exam else "Exam"
        exam_date = exam.get("exam_date", "N/A") if exam else "N/A"
        
        no_data_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Performance Report - {html.escape(exam_title)}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="/static/styles.css">
            <style>
                body {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 2rem;
                }}
                .no-data-container {{
                    max-width: 800px;
                    margin: 2rem auto;
                    background: white;
                    border-radius: 16px;
                    padding: 3rem;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.2);
                    text-align: center;
                }}
                .no-data-icon {{
                    font-size: 5rem;
                    margin-bottom: 1.5rem;
                    opacity: 0.3;
                }}
            </style>
        </head>
        <body>
            <nav class="navbar navbar-dark bg-dark shadow-sm mb-4">
                <div class="container">
                    <span class="navbar-brand">📊 Performance Report: {html.escape(exam_title)}</span>
                    <a href="/admin/exam-list" class="btn btn-outline-light btn-sm">← Back to Exam List</a>
                </div>
            </nav>

            <div class="no-data-container">
                <div class="no-data-icon">🔭</div>
                <h2 class="mb-3">No Submissions Yet</h2>
                <p class="text-muted mb-4">
                    <strong>Exam:</strong> {html.escape(exam_title)}<br>
                    <strong>Date:</strong> {html.escape(exam_date)}
                </p>
                <div class="alert alert-info">
                    <p class="mb-0">
                        <strong>What does this mean?</strong><br>
                        No students have submitted this exam yet. The performance report will be available once students complete the exam.
                    </p>
                </div>
                <div class="mt-4">
                    <a href="/admin/exam-list" class="btn btn-primary btn-lg me-2">← Back to Exam List</a>
                    <a href="/admin/grading-settings?exam_id={html.escape(exam_id)}" class="btn btn-outline-primary btn-lg">⚙️ Exam Settings</a>
                </div>
            </div>
        </body>
        </html>
        """
        return no_data_html, 200

    # ==========================================
    # Normal Flow: Extract data for the template
    # ==========================================
    exam = report.get("exam", {})
    overall_stats = report.get("overall_stats", {})
    mcq_stats = report.get("mcq_stats", {})
    sa_stats = report.get("sa_stats", {})
    grade_distribution = report.get("grade_distribution", {})
    question_performance = report.get("question_performance", {})
    top_performers = report.get("top_performers", [])
    students_at_risk = report.get("students_at_risk", [])

    # ==========================================
    # Build chart data - FIXED VERSION
    # ==========================================
    # Build grade distribution data for chart
    grade_labels = []
    grade_counts = []
    grade_colors = []
    
    grade_color_map = {
        "A": "#28a745",  # Green
        "B": "#17a2b8",  # Cyan
        "C": "#ffc107",  # Yellow
        "D": "#fd7e14",  # Orange
        "F": "#dc3545",  # Red
    }
    
    # Check if grade_distribution has data
    print(f"🔍 DEBUG - grade_distribution: {grade_distribution}")
    
    # FIXED: Always include all grades A-F, even if count is 0
    for grade in ["A", "B", "C", "D", "F"]:
        grade_labels.append(f"Grade {grade}")
        grade_colors.append(grade_color_map.get(grade, "#6c757d"))
        
        # Get count from distribution, default to 0 if not present
        if grade in grade_distribution:
            count = grade_distribution[grade].get("count", 0)
            grade_counts.append(count)
        else:
            grade_counts.append(0)
    
    print(f"📊 Chart Data - Grade labels: {grade_labels}")
    print(f"📊 Chart Data - Grade counts: {grade_counts}")

    # Build question performance data for chart
    question_labels = []
    question_success = []
    
    print(f"🔍 DEBUG - question_performance: {question_performance}")
    
    for q_key in sorted(question_performance.keys()):
        q_data = question_performance[q_key]
        question_labels.append(q_key)
        question_success.append(q_data.get("success_rate", 0))
    
    print(f"🎯 Chart Data - Question labels: {question_labels}")
    print(f"🎯 Chart Data - Question success: {question_success}")

    # Convert to JSON strings - ALWAYS create valid JSON arrays
    grade_labels_json = json.dumps(grade_labels)
    grade_counts_json = json.dumps(grade_counts)
    grade_colors_json = json.dumps(grade_colors)
    question_labels_json = json.dumps(question_labels) if question_labels else "[]"
    question_success_json = json.dumps(question_success) if question_success else "[]"
    
    print(f"✅ Final JSON - grade_labels_json: {grade_labels_json}")
    print(f"✅ Final JSON - grade_counts_json: {grade_counts_json}")
    print(f"✅ Final JSON - question_labels_json: {question_labels_json}")

    # ==========================================
    # FIX: Build question performance table HTML
    # ==========================================
    question_perf_html = ""
    if question_performance:
        question_perf_html = """
        <div class="table-responsive">
            <table class="table table-hover">
                <thead class="table-light">
                    <tr>
                        <th>Question</th>
                        <th>Question Text</th>
                        <th>Correct</th>
                        <th>Incorrect</th>
                        <th>Unanswered</th>
                        <th>Success Rate</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for q_key in sorted(question_performance.keys()):
            q_data = question_performance[q_key]
            success_rate = q_data.get("success_rate", 0)
            
            # Color code success rate
            if success_rate >= 80:
                badge_class = "bg-success"
            elif success_rate >= 60:
                badge_class = "bg-info"
            elif success_rate >= 40:
                badge_class = "bg-warning text-dark"
            else:
                badge_class = "bg-danger"
            
            question_perf_html += f"""
                <tr>
                    <td><strong>{html.escape(q_key)}</strong></td>
                    <td>{html.escape(q_data.get('question_text', 'N/A'))}</td>
                    <td><span class="badge bg-success">{q_data.get('correct', 0)}</span></td>
                    <td><span class="badge bg-danger">{q_data.get('incorrect', 0)}</span></td>
                    <td><span class="badge bg-secondary">{q_data.get('unanswered', 0)}</span></td>
                    <td><span class="badge {badge_class}">{success_rate}%</span></td>
                </tr>
            """
        
        question_perf_html += """
                </tbody>
            </table>
        </div>
        """
    else:
        question_perf_html = '<p class="text-center text-muted py-4">No question performance data available.</p>'

    # ==========================================
    # FIX: Build top performers table HTML
    # ==========================================
    top_performers_html = ""
    if top_performers:
        for rank, performer in enumerate(top_performers, start=1):
            medal = ""
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            
            top_performers_html += f"""
            <tr>
                <td>{medal} {rank}</td>
                <td>{html.escape(performer.get('student_id', 'N/A'))}</td>
                <td><strong>{performer.get('percentage', 0)}%</strong></td>
                <td>{performer.get('total_marks', 0)}</td>
                <td>{performer.get('mcq_score', 0)}</td>
                <td>{performer.get('sa_score', 0)}</td>
            </tr>
            """
    else:
        top_performers_html = '<tr><td colspan="6" class="text-center text-muted py-4">No top performers data available.</td></tr>'

    # ==========================================
    # FIX: Build at-risk students table HTML
    # ==========================================
    at_risk_html = ""
    if students_at_risk:
        for student in students_at_risk:
            concerns = ", ".join(student.get('areas_of_concern', []))
            at_risk_html += f"""
            <tr>
                <td>{html.escape(student.get('student_id', 'N/A'))}</td>
                <td><span class="badge bg-danger">{student.get('percentage', 0)}%</span></td>
                <td>{student.get('total_marks', 0)}</td>
                <td><small>{html.escape(concerns)}</small></td>
            </tr>
            """
    else:
        at_risk_html = '<tr><td colspan="4" class="text-center text-muted py-4">No at-risk students identified.</td></tr>'

    # ==========================================
    # DEBUG: Print what we're sending (optional)
    # ==========================================
    print(f"📋 DEBUG - question_perf_html length: {len(question_perf_html)}")
    print(f"📋 DEBUG - top_performers count: {len(top_performers)}")
    print(f"📋 DEBUG - at_risk count: {len(students_at_risk)}")
    print(f"📋 DEBUG - question_performance keys: {list(question_performance.keys())}")

    # Prepare context for template
    context = {
        "exam_id": exam_id,
        "exam_title": exam.get("title", ""),
        "exam_date": exam.get("exam_date", ""),
        "total_students": report.get("total_students", 0),
        
        # Overall stats
        "avg_percentage": overall_stats.get("average_percentage", 0),
        "pass_rate": overall_stats.get("pass_rate", 0),
        "highest_score": overall_stats.get("highest_score", 0),
        "lowest_score": overall_stats.get("lowest_score", 0),
        "median_score": overall_stats.get("median_score", 0),
        "std_dev": overall_stats.get("standard_deviation", 0),
        "passed_count": overall_stats.get("passed_count", 0),
        "failed_count": overall_stats.get("failed_count", 0),
        
        # MCQ stats
        "mcq_avg_score": mcq_stats.get("average_score", 0),
        "mcq_avg_percentage": mcq_stats.get("average_percentage", 0),
        "mcq_total": mcq_stats.get("total_marks", 0),
        
        # Short answer stats
        "sa_avg_score": sa_stats.get("average_score", 0) if sa_stats.get("has_short_answers") else "N/A",
        "sa_avg_percentage": sa_stats.get("average_percentage", 0) if sa_stats.get("has_short_answers") else "N/A",
        "sa_total": sa_stats.get("total_marks", 0) if sa_stats.get("has_short_answers") else "N/A",
        
        # Chart data (as JSON strings for JavaScript)
        "grade_labels_json": grade_labels_json,
        "grade_counts_json": grade_counts_json,
        "grade_colors_json": grade_colors_json,
        "question_labels_json": question_labels_json,
        "question_success_json": question_success_json,
        
        # HTML tables - NOW PROPERLY POPULATED
        "question_perf_html": question_perf_html,
        "top_performers_html": top_performers_html,
        "at_risk_html": at_risk_html,
    }

    html_str = render("admin_performance.html", context)
    return html_str, 200