"""
PDF Service
Handles generation of PDF reports for student results
"""

from typing import Dict
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER


def generate_result_pdf(result_data: Dict) -> bytes:
    """
    Generate a PDF for student exam results

    Args:
        result_data: Complete result data from get_student_result()

    Returns:
        PDF file as bytes
    """
    buffer = BytesIO()

    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    # Container for PDF elements
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#16a34a"),
        spaceAfter=30,
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=16,
        textColor=colors.HexColor("#2563eb"),
        spaceAfter=12,
        spaceBefore=12,
    )

    # Title
    exam = result_data["exam"]
    title = Paragraph(f"Exam Result: {exam.get('title', 'Exam')}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    # Summary Information
    submitted_at = result_data["submitted_at"]
    submitted_time = (
        submitted_at.strftime("%Y-%m-%d %H:%M:%S") if submitted_at else "N/A"
    )

    summary_data = [
        ["Exam Date:", exam.get("exam_date", "N/A")],
        ["Submitted:", submitted_time],
        ["", ""],
        [
            "Total Score:",
            f"{result_data['overall_obtained']}/{result_data['overall_total']} ({result_data['overall_percentage']}%)",
        ],
        ["MCQ Score:", f"{result_data['mcq_obtained']}/{result_data['mcq_total']}"],
        [
            "Short Answer Score:",
            f"{result_data['sa_obtained']}/{result_data['sa_total']}",
        ],
    ]

    summary_table = Table(summary_data, colWidths=[2 * inch, 4 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#e0f2fe")),
                ("TEXTCOLOR", (0, 3), (-1, 3), colors.HexColor("#0369a1")),
            ]
        )
    )

    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))

    # MCQ Results
    if result_data["mcq_results"]:
        mcq_heading = Paragraph("Multiple Choice Questions", heading_style)
        elements.append(mcq_heading)
        elements.append(Spacer(1, 0.1 * inch))

        for q in result_data["mcq_results"]:
            status = "✓ Correct" if q["is_correct"] else "✗ Incorrect"
            status_color = (
                colors.HexColor("#22c55e")
                if q["is_correct"]
                else colors.HexColor("#dc3545")
            )

            q_data = [
                [
                    f"Question {q['question_no']}",
                    f"{status} ({q['marks_obtained']}/{q['marks']} marks)",
                ],
                [Paragraph(q["question_text"], styles["Normal"]), ""],
                ["A. " + q["option_a"], ""],
                ["B. " + q["option_b"], ""],
                ["C. " + q["option_c"], ""],
                ["D. " + q["option_d"], ""],
                [
                    f"Your Answer: {q['student_answer']}",
                    f"Correct Answer: {q['correct_answer']}",
                ],
            ]

            q_table = Table(q_data, colWidths=[4 * inch, 2.5 * inch])
            q_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                        ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                        ("TEXTCOLOR", (1, 0), (1, 0), status_color),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#f3f4f6")),
                        ("BOX", (0, 0), (-1, -1), 1, colors.grey),
                        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.grey),
                    ]
                )
            )

            elements.append(q_table)
            elements.append(Spacer(1, 0.15 * inch))

    # Short Answer Results
    if result_data["sa_results"]:
        sa_heading = Paragraph("Short Answer Questions", heading_style)
        elements.append(sa_heading)
        elements.append(Spacer(1, 0.1 * inch))

        for q in result_data["sa_results"]:
            sa_data = [
                [
                    f"Question {q['question_no']}",
                    f"({q['awarded_marks']}/{q['max_marks']} marks)",
                ],
                [Paragraph(q["question_text"], styles["Normal"]), ""],
                ["Your Answer:", ""],
                [
                    Paragraph(
                        (
                            q["student_answer"]
                            if q["student_answer"] != "Not answered"
                            else "No answer provided"
                        ),
                        styles["Normal"],
                    ),
                    "",
                ],
            ]

            if q["sample_answer"]:
                sa_data.extend(
                    [
                        ["Sample Answer:", ""],
                        [Paragraph(q["sample_answer"], styles["Normal"]), ""],
                    ]
                )

            if q["feedback"]:
                sa_data.extend(
                    [
                        ["Instructor Feedback:", ""],
                        [Paragraph(q["feedback"], styles["Normal"]), ""],
                    ]
                )

            sa_table = Table(sa_data, colWidths=[5 * inch, 1.5 * inch])
            sa_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f3f4f6")),
                        ("BOX", (0, 0), (-1, -1), 1, colors.grey),
                        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )

            elements.append(sa_table)
            elements.append(Spacer(1, 0.15 * inch))

    # Build PDF
    doc.build(elements)

    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
