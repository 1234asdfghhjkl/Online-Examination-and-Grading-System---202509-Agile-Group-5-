import json
import statistics
import math
from typing import Tuple, Dict, Any, List
from core.firebase_db import db


# ---------------- Basic Firestore helpers ----------------


def _get_student_name(student_id: str) -> str:
    """Fetch student name from users collection."""
    doc = db.collection("users").document(str(student_id)).get()
    if doc.exists:
        data = doc.to_dict()
        return data.get("name") or str(student_id)
    return str(student_id)


def _get_all_exams() -> List[Dict[str, Any]]:
    """Return all non-deleted exams as list of dicts."""
    exams_ref = db.collection("exams")
    docs = exams_ref.stream()
    exams: List[Dict[str, Any]] = []
    for d in docs:
        data = d.to_dict()
        if data.get("is_deleted"):
            continue
        data["doc_id"] = d.id
        exams.append(data)
    return exams


def _get_questions_for_exam(exam_doc_id: str) -> List[Dict[str, Any]]:
    qs = db.collection("questions").where("exam_id", "==", exam_doc_id).stream()
    return [q.to_dict() for q in qs]


def _get_submissions_for_exam(exam_doc_id: str) -> List[Dict[str, Any]]:
    subs = db.collection("submissions").where("exam_id", "==", exam_doc_id).stream()
    return [s.to_dict() for s in subs]


# ---------------- Scoring helpers ----------------


def _get_submission_combined_marks(
    sub: Dict[str, Any], exam_total_marks: int
) -> tuple[float, float]:
    """
    Returns (obtained_marks, total_marks) for ONE submission,
    combining MCQ + short answer where available.
    """
    gr = sub.get("grading_result", {}) or {}

    mcq_obt = gr.get("obtained_marks", 0) or 0
    mcq_total = gr.get("total_marks")  # may be None

    sa_obt = sub.get("sa_obtained_marks", 0) or 0
    sa_total = sub.get("sa_total_marks")  # may be None

    obtained = float(mcq_obt) + float(sa_obt)

    # Prefer explicit totals if present; otherwise fall back to exam_total_marks
    total_from_sub = (mcq_total or 0) + (sa_total or 0)
    total = float(total_from_sub) if total_from_sub else float(exam_total_marks)

    return obtained, total


def _compute_exam_report(
    exam: Dict[str, Any],
    questions: List[Dict[str, Any]] | None = None,
    submissions: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Compute A + B + C metrics for ONE exam."""
    exam_doc_id = exam["doc_id"]

    # ---------- A. Exam overview ----------
    if questions is None:
        questions = _get_questions_for_exam(exam_doc_id)
    num_questions = len(questions)
    total_marks = sum(q.get("marks", 0) for q in questions)

    # ---------- submissions ----------
    if submissions is None:
        submissions = _get_submissions_for_exam(exam_doc_id)
    attempted = len(submissions)

    combined_scores: List[float] = []

    for s in submissions:
        obtained, total = _get_submission_combined_marks(s, total_marks)
        combined_scores.append(obtained)

    if combined_scores:
        avg_score = statistics.mean(combined_scores)
        highest_score = max(combined_scores)
        lowest_score = min(combined_scores)
    else:
        avg_score = None
        highest_score = None
        lowest_score = None

    # highest / lowest student names
    top_student = None
    low_student = None
    if submissions and highest_score is not None and lowest_score is not None:
        highest_sub = max(
            submissions,
            key=lambda sub: _get_submission_combined_marks(sub, total_marks)[0],
        )
        lowest_sub = min(
            submissions,
            key=lambda sub: _get_submission_combined_marks(sub, total_marks)[0],
        )
        top_student = _get_student_name(highest_sub.get("student_id"))
        low_student = _get_student_name(lowest_sub.get("student_id"))

    # ---------- Pass rate ----------
    passes = 0
    for s in submissions:
        obtained, total = _get_submission_combined_marks(s, total_marks)
        if total > 0 and (obtained / total) >= 0.5:
            passes += 1

    pass_rate = (passes / attempted * 100) if attempted > 0 else None
    fails = attempted - passes if attempted > 0 else 0

    # ---------- Avg time taken (optional) ----------
    times: List[float] = []
    for s in submissions:
        gr = s.get("grading_result", {})
        if "time_taken_seconds" in gr:
            times.append(gr["time_taken_seconds"])
    avg_time_seconds = statistics.mean(times) if times else None

    # ---------- Score distribution for chart ----------
    bucket_labels = ["0–19", "20–39", "40–59", "60–79", "80–100"]
    bucket_counts = [0, 0, 0, 0, 0]

    for s in submissions:
        obtained, total = _get_submission_combined_marks(s, total_marks)
        pct = (obtained / total * 100) if total else 0

        if pct < 20:
            bucket_counts[0] += 1
        elif pct < 40:
            bucket_counts[1] += 1
        elif pct < 60:
            bucket_counts[2] += 1
        elif pct < 80:
            bucket_counts[3] += 1
        else:
            bucket_counts[4] += 1

    return {
        "exam": exam,
        "num_questions": num_questions,
        "total_marks": total_marks,
        "attempted": attempted,
        "avg_score": avg_score,
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "top_student": top_student,
        "low_student": low_student,
        "pass_rate": pass_rate,
        "pass_count": passes,
        "fail_count": fails,
        "avg_time_seconds": avg_time_seconds,
        "bucket_labels": bucket_labels,
        "bucket_counts": bucket_counts,
    }


def _exam_short_answers_fully_graded(
    questions: List[Dict[str, Any]],
    submissions: List[Dict[str, Any]],
) -> bool:
    """
    An exam is 'fully graded' only if:
    - It contains NO short-answer questions, OR
    - ALL submissions have sa_grading_complete = True
    """
    # detect if any short-answer question exists (question_type == 'SA')
    has_sa_questions = any(q.get("question_type") == "SA" for q in questions)

    if not has_sa_questions:
        return True

    # If SA exists, every submission must have sa_grading_complete = True
    for s in submissions:
        if not s.get("sa_grading_complete", False):
            return False

    return True


# ---------------- Page Handler ----------------


def get_exam_results_summary_data(query: Dict[str, list]) -> Tuple[str, int]:
    """Return summary for ONE exam as JSON for AJAX requests."""
    selected_exam_id = query.get("exam_id", [""])[0]

    if not selected_exam_id:
        return json.dumps({"ok": False, "error": "Missing exam_id"}), 400

    exams = _get_all_exams()
    selected_exam = None
    for e in exams:
        if e["doc_id"] == selected_exam_id:
            selected_exam = e
            break

    if not selected_exam:
        return json.dumps({"ok": False, "error": "Exam not found"}), 404

    rd = _compute_exam_report(selected_exam)
    exam = selected_exam

    # Format time as "start_time - end_time"
    start_time = exam.get("start_time", "") or ""
    end_time = exam.get("end_time", "") or ""
    if start_time and end_time:
        time_display = f"{start_time} - {end_time}"
    elif start_time:
        time_display = start_time
    else:
        time_display = ""

    resp = {
        "ok": True,
        # A. Exam overview
        "doc_id": exam["doc_id"],
        "exam_id": exam.get("exam_id", ""),
        "title": exam.get("title", ""),
        "exam_date": exam.get("exam_date", ""),
        "time_display": time_display,
        "duration": exam.get("duration", ""),
        "num_questions": rd["num_questions"],
        "total_marks": rd["total_marks"],
        # B. Class performance
        "attempted": rd["attempted"],
        "avg_score": rd["avg_score"],
        "highest_score": rd["highest_score"],
        "lowest_score": rd["lowest_score"],
        "top_student": rd["top_student"],
        "low_student": rd["low_student"],
        "pass_rate": rd["pass_rate"],
        "pass_count": rd["pass_count"],
        "fail_count": rd["fail_count"],
        # C. Chart data
        "bucket_labels": rd["bucket_labels"],
        "bucket_counts": rd["bucket_counts"],
    }

    return json.dumps(resp), 200


# ---------------- Full HTML report page ----------------


def get_exam_results_summary_report(query: Dict[str, list]) -> Tuple[str, int]:
    """
    Render the Exam Results Summary Report page as full HTML.
    Adds pagination for the exam ranking (10 records per page).
    SA-pending exams are always placed at the bottom regardless of sort.
    """
    # --- parse query params ---
    selected_exam_id = query.get("exam_id", [""])[0]
    sort_mode = query.get("sort", ["best"])[0] or "best"  # "best" or "worst"
    # page param for ranking pagination
    try:
        page = int(query.get("page", ["1"])[0])
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1

    # --- load all exams ---
    exams = _get_all_exams()

    # Precompute questions, submissions, and reports for each exam once
    exam_reports: dict[str, Dict[str, Any]] = {}
    exam_questions: dict[str, List[Dict[str, Any]]] = {}
    exam_submissions: dict[str, List[Dict[str, Any]]] = {}
    exam_sa_pending: dict[str, bool] = {}

    for e in exams:
        exam_doc_id = e["doc_id"]
        qs = _get_questions_for_exam(exam_doc_id)
        subs = _get_submissions_for_exam(exam_doc_id)
        exam_questions[exam_doc_id] = qs
        exam_submissions[exam_doc_id] = subs
        exam_reports[exam_doc_id] = _compute_exam_report(
            e, questions=qs, submissions=subs
        )
        exam_sa_pending[exam_doc_id] = not _exam_short_answers_fully_graded(qs, subs)

    # find selected exam dict
    selected_exam = None
    if selected_exam_id:
        for e in exams:
            if e["doc_id"] == selected_exam_id:
                selected_exam = e
                break

    report_data = exam_reports.get(selected_exam_id) if selected_exam else None

    # ---------- build ranking rows ----------
    normal_rows: list[dict[str, Any]] = []
    pending_rows: list[dict[str, Any]] = []

    for e in exams:
        exam_doc_id = e["doc_id"]
        rpt = exam_reports[exam_doc_id]
        sa_pending = exam_sa_pending[exam_doc_id]

        # Skip if no student attempts
        if rpt.get("attempted", 0) == 0:
            continue

        pass_rate = rpt.get("pass_rate")

        if sa_pending:
            # collect separately to ensure they show last
            pending_rows.append(
                {
                    "doc_id": exam_doc_id,
                    "title": e.get("title", ""),
                    "exam_id": e.get("exam_id", ""),
                    "pass_rate_numeric": -1.0,
                    "pass_rate_display": None,
                    "sa_pending": True,
                }
            )
        else:
            pass_rate_numeric = float(pass_rate or 0.0)
            pass_rate_display = f"{pass_rate_numeric:.1f}%"
            normal_rows.append(
                {
                    "doc_id": exam_doc_id,
                    "title": e.get("title", ""),
                    "exam_id": e.get("exam_id", ""),
                    "pass_rate_numeric": pass_rate_numeric,
                    "pass_rate_display": pass_rate_display,
                    "sa_pending": False,
                }
            )

    # --- Sorting logic for normal rows only ---
    if sort_mode == "worst":
        normal_rows.sort(key=lambda r: r["pass_rate_numeric"])
    else:
        normal_rows.sort(key=lambda r: r["pass_rate_numeric"], reverse=True)

    # final ranking order: sorted normal rows, then all pending rows
    ranking_rows_all = normal_rows + pending_rows

    # ---------- Pagination ----------
    PER_PAGE = 10
    # ensure math is imported at the module top
    total_rows = len(ranking_rows_all)
    total_pages = max(1, math.ceil(total_rows / PER_PAGE))
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * PER_PAGE
    end_idx = start_idx + PER_PAGE
    ranking_rows_page = ranking_rows_all[start_idx:end_idx]

    # ---------- exams dropdown options ----------
    exam_options_html = []
    for e in exams:
        eid = e.get("doc_id", "")
        title = e.get("title", "Untitled")
        exam_code = e.get("exam_id", "")
        date = e.get("exam_date", "")
        selected_attr = " selected" if eid == selected_exam_id else ""
        exam_options_html.append(
            f'<option value="{eid}"{selected_attr}>'
            f"{title} — {exam_code} ({date})"
            f"</option>"
        )
    exam_options_html_str = "\n".join(exam_options_html)

    # ---------- A + B + C section (overview + performance + charts) ----------
    if report_data:
        exam = report_data.get("exam") or selected_exam or {}

        # time display from exams collection
        start_time = exam.get("start_time", "") or ""
        end_time = exam.get("end_time", "") or ""
        if start_time and end_time:
            time_display = f"{start_time} - {end_time}"
        elif start_time:
            time_display = start_time
        else:
            time_display = "—"

        avg_score_display = (
            f"{report_data['avg_score']:.1f}"
            if report_data["avg_score"] is not None
            else "N/A"
        )
        highest_display = (
            f"{report_data['highest_score']}"
            if report_data["highest_score"] is not None
            else "N/A"
        )
        lowest_display = (
            f"{report_data['lowest_score']}"
            if report_data["lowest_score"] is not None
            else "N/A"
        )
        pass_display = (
            f"{report_data['pass_rate']:.1f}%"
            if report_data["pass_rate"] is not None
            else "N/A"
        )

        # pass/fail counts for pie chart
        pass_count = report_data.get("pass_count")
        fail_count = report_data.get("fail_count")
        if pass_count is None or fail_count is None:
            attempted = report_data.get("attempted", 0)
            passes_calc = (
                int(round((report_data["pass_rate"] or 0) / 100 * attempted))
                if attempted
                else 0
            )
            pass_count = passes_calc
            fail_count = max(attempted - passes_calc, 0)

        score_labels_json = json.dumps(report_data["bucket_labels"])
        score_data_json = json.dumps(report_data["bucket_counts"])
        pass_labels_json = json.dumps(["Pass", "Fail"])
        pass_data_json = json.dumps([pass_count, fail_count])

        report_main_html = f"""
  <div class="row g-4 mb-4">
    <!-- A. Exam Overview -->
    <div class="col-lg-6">
      <div class="card shadow-sm border-0 h-100">
        <div class="card-body">
          <div class="card-section-title">A. Exam Overview</div>
          <h5 class="mb-3">{exam.get("title", "")}</h5>
          <div class="row gy-3">
            <div class="col-sm-6">
              <div class="stat-chip">
                <div class="stat-label">Exam ID</div>
                <div class="stat-value">{exam.get("exam_id", "")}</div>
              </div>
            </div>
            <div class="col-sm-6">
              <div class="stat-chip">
                <div class="stat-label">Date</div>
                <div class="stat-value">{exam.get("exam_date", "")}</div>
              </div>
            </div>
            <div class="col-sm-6">
              <div class="stat-chip">
                <div class="stat-label">Time</div>
                <div class="stat-value">{time_display}</div>
              </div>
            </div>
            <div class="col-sm-6">
              <div class="stat-chip">
                <div class="stat-label">Duration</div>
                <div class="stat-value">{exam.get("duration", "")} mins</div>
              </div>
            </div>
            <div class="col-sm-6">
              <div class="stat-chip">
                <div class="stat-label">No. of questions</div>
                <div class="stat-value">{report_data["num_questions"]}</div>
              </div>
            </div>
            <div class="col-sm-6">
              <div class="stat-chip">
                <div class="stat-label">Total marks</div>
                <div class="stat-value">{report_data["total_marks"]}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- B. Class Performance Summary -->
    <div class="col-lg-6">
      <div class="card shadow-sm border-0 h-100">
        <div class="card-body">
          <div class="card-section-title">B. Class Performance Summary</div>
          <div class="row gy-3 mb-3">
            <div class="col-sm-6">
              <div class="stat-chip">
                <div class="stat-label">Students attempted</div>
                <div class="stat-value">{report_data["attempted"]}</div>
              </div>
            </div>
            <div class="col-sm-6">
              <div class="stat-chip">
                <div class="stat-label">Pass rate (≥ 50%)</div>
                <div class="stat-value">{pass_display}</div>
              </div>
            </div>
            <div class="col-sm-6">
              <div class="stat-chip">
                <div class="stat-label">Average score</div>
                <div class="stat-value">{avg_score_display}</div>
              </div>
            </div>
            <div class="col-sm-6">
              <div class="stat-chip">
                <div class="stat-label">Highest score</div>
                <div class="stat-value">
                  {highest_display}
                  <span class="text-muted" style="font-size:0.8rem;">
                    ({report_data["top_student"] or "N/A"})
                  </span>
                </div>
              </div>
            </div>
            <div class="col-sm-6">
              <div class="stat-chip">
                <div class="stat-label">Lowest score</div>
                <div class="stat-value">
                  {lowest_display}
                  <span class="text-muted" style="font-size:0.8rem;">
                    ({report_data["low_student"] or "N/A"})
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- C. Performance Distribution -->
  <div class="card shadow-sm border-0 mb-4">
    <div class="card-body">
      <div class="card-section-title mb-2">C. Performance Distribution</div>
      <p class="text-muted small mb-3">
        Number of students in each score range (combined MCQ + short answer marks),
        and overall pass vs fail.
      </p>
      <div class="row">
        <div class="col-md-6 d-flex justify-content-center">
          <div style="width: 100%; max-width: 450px; height: 300px;">
            <canvas id="scoreChart"></canvas>
          </div>
        </div>
        <div class="col-md-6 d-flex justify-content-center">
          <div style="width: 100%; max-width: 350px; height: 300px;">
            <canvas id="passFailChart"></canvas>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    (function () {{
      const scoreLabels    = {score_labels_json};
      const scoreData      = {score_data_json};
      const passFailLabels = {pass_labels_json};
      const passFailData   = {pass_data_json};

      const barCanvas = document.getElementById('scoreChart');
      if (barCanvas && scoreLabels.length) {{
        const ctx = barCanvas.getContext('2d');
        new Chart(ctx, {{
          type: 'bar',
          data: {{
            labels: scoreLabels,
            datasets: [{{
              label: 'Number of students',
              data: scoreData
            }}]
          }},
          options: {{
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
              x: {{ grid: {{ display: false }} }},
              y: {{ beginAtZero: true, precision: 0 }}
            }}
          }}
        }});
      }}

      const pieCanvas = document.getElementById('passFailChart');
      if (pieCanvas && passFailLabels.length) {{
        const ctxPie = pieCanvas.getContext('2d');
        new Chart(ctxPie, {{
          type: 'pie',
          data: {{
            labels: passFailLabels,
            datasets: [{{
              data: passFailData
            }}]
          }},
          options: {{
            plugins: {{
              legend: {{ position: 'bottom' }}
            }}
          }}
        }});
      }}
    }})();
  </script>
"""
    else:
        report_main_html = """
  <div class="alert alert-info shadow-sm border-0">
    Select an exam from the list above and click <strong>View/Sort Report</strong> to see the summary dashboard.
  </div>
"""

    # ---------- ranking table HTML (paginated rows) ----------
    if ranking_rows_page:
        ranking_rows_html = ""
        # compute overall index = start_idx + i for display
        for i, row in enumerate(ranking_rows_page, start=1):
            overall_index = start_idx + i
            exam_id_badge = f"<span class='badge bg-secondary-subtle text-secondary pill-badge'>{row['exam_id']}</span>"

            # SA Pending OR normal pass rate
            if row["sa_pending"]:
                pass_rate_col = "<span class='badge bg-warning text-dark pill-badge'>⏳ SA Pending</span>"
            else:
                pr = row["pass_rate_display"] or "0.0%"
                pass_rate_col = pr

            ranking_rows_html += (
                "<tr>"
                f"<td class='text-muted'>{overall_index}</td>"
                f"<td>{row['title']}</td>"
                f"<td>{exam_id_badge}</td>"
                f"<td>{pass_rate_col}</td>"
                "</tr>\n"
            )
    else:
        ranking_rows_html = "<tr><td colspan='4' class='text-center text-muted py-3'>No exams found.</td></tr>"

    # ---------- pagination controls ----------
    # build base query string pieces to preserve selected exam and sort when switching pages
    base_qs = []
    if selected_exam_id:
        base_qs.append(f"exam_id={selected_exam_id}")
    if sort_mode:
        base_qs.append(f"sort={sort_mode}")
    base_qs_str = "&".join(base_qs)
    if base_qs_str:
        base_qs_str = "&" + base_qs_str  # will be appended after page param

    prev_page = max(1, page - 1)
    next_page = min(total_pages, page + 1)

    # show summary of pages
    page_summary = f"Page {page} of {total_pages} — showing {min(PER_PAGE, max(0, total_rows - start_idx))} of {total_rows} exams"

    # --- build compact page links (centered window) ---
    page_links = []
    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)

    for p in range(start_page, end_page + 1):
        active_cls = "active" if p == page else ""
        page_links.append(
            f'<li class="page-item {active_cls}">'
            f'<a class="page-link" href="?page={p}{base_qs_str}">{p}</a>'
            f"</li>"
        )

    page_links_html = "".join(page_links)

    # ---------- full HTML page ----------
    sort_best_selected = "selected" if sort_mode == "best" else ""
    sort_worst_selected = "selected" if sort_mode == "worst" else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Exam Results Summary Report</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="/static/styles.css">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{ font-family: 'Inter', sans-serif; background-color: #f3f4f6; }}
    .page-header-card {{ border-radius: 1rem; }}
    .stat-chip {{
      border-radius: 0.75rem;
      background-color: #f9fafb;
      border: 1px solid #e5e7eb;
      padding: 0.75rem 1rem;
      height: 100%;
    }}
    .stat-label {{
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: .04em;
      color: #6b7280;
      margin-bottom: 0.15rem;
    }}
    .stat-value {{
      font-size: 1.1rem;
      font-weight: 600;
      color: #111827;
    }}
    .card-section-title {{
      font-size: 0.85rem;
      letter-spacing: .06em;
      text-transform: uppercase;
      color: #6b7280;
      margin-bottom: .5rem;
    }}
    .pill-badge {{
      padding: 0.25rem 0.6rem;
      border-radius: 999px;
      font-size: 0.75rem;
    }}
  </style>
</head>
<body>

<div class="container py-4">

  <!-- Banner -->
  <div class="card shadow-sm border-0 mb-4 page-header-card">
    <div class="card-body d-flex flex-column flex-md-row justify-content-between align-items-md-center">
      <div>
        <h4 class="mb-1 fw-bold d-flex justify-content-center">Exam Results Summary Report</h4>
        <span class="badge bg-primary-subtle text-primary pill-badge">
          Exam Performance Overview
        </span>
      </div>
      <div class="d-flex flex-column flex-md-row align-items-md-center gap-2 mt-3 mt-md-0">
        <a href="/exam-list" class="btn btn-secondary">
          Back to All Exams
        </a>
      </div>
    </div>
  </div>

  <!-- Controls -->
  <div class="card shadow-sm border-0 mb-4">
    <div class="card-body">
      <form method="GET" action="/exam-report" class="row g-3 align-items-end">
        <div class="col-md-6">
          <label for="examSelect" class="form-label mb-1">Select exam</label>
          <select id="examSelect" name="exam_id" class="form-select">
            <option value="">-- Select an exam --</option>
            {exam_options_html_str}
          </select>
        </div>
        <div class="col-md-3">
          <label for="sortSelect" class="form-label mb-1">Sort by</label>
          <select id="sortSelect" name="sort" class="form-select">
            <option value="best" {sort_best_selected}>Best performing</option>
            <option value="worst" {sort_worst_selected}>Worst performing</option>
          </select>
        </div>
        <div class="col-md-3 d-flex align-items-end">
          <button type="submit" class="btn btn-primary w-100">View/Sort Report</button>
        </div>
      </form>
    </div>
  </div>

  {report_main_html}

  <!-- Exam ranking -->
  <div class="card shadow-sm border-0">
    <div class="card-body">
      <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-3">
        <div>
          <div class="card-section-title mb-1">Exam ranking</div>
        </div>
        <div class="mt-3 mt-md-0">
          <span class="badge bg-secondary-subtle text-secondary pill-badge">
            {total_rows} exams
          </span>
        </div>
      </div>
      <div class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th style="width: 60px;">#</th>
              <th>Exam title</th>
              <th style="width: 180px;">Exam ID</th>
              <th style="width: 140px;">Pass rate</th>
            </tr>
          </thead>
          <tbody>
            {ranking_rows_html}
          </tbody>
        </table>
      </div>

      <!-- pagination -->
      <div class="d-flex justify-content-between align-items-center mt-3">
        <div class="text-muted small">{page_summary}</div>
        <div>
          <nav aria-label="Exam ranking pages">
            <ul class="pagination pagination-sm mb-0">
              <li class="page-item {'disabled' if page <= 1 else ''}">
                <a class="page-link" href="?page={prev_page}{base_qs_str}">Prev</a>
              </li>
              {page_links_html}
              <li class="page-item {'disabled' if page >= total_pages else ''}">
                <a class="page-link" href="?page={next_page}{base_qs_str}">Next</a>
              </li>
            </ul>
          </nav>
        </div>
      </div>

    </div>
  </div>

</div> <!-- /container -->

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    return html, 200
