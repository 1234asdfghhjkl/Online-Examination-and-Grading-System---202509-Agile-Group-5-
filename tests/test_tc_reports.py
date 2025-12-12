# tests/test_tc_reports.py
import unittest
from unittest.mock import patch, ANY

import web.tc_reports as tr


class TCReportsDisplayAndCalculationTests(unittest.TestCase):
    # ------------------------------------------------------------------
    # Helper sample data
    # ------------------------------------------------------------------
    def _sample_exam(self):
        return {
            "doc_id": "exam1",
            "exam_id": "TST100",
            "title": "Testing 101",
            "exam_date": "2025-12-01",
            "start_time": "09:00",
            "end_time": "10:00",
            "duration": 60,
        }

    def _sample_questions(self):
        # two questions totalling 100 marks (60 MCQ, 40 SA)
        return [
            {"marks": 60, "question_type": "MCQ"},
            {"marks": 40, "question_type": "SA"},
        ]

    def _sample_submissions(self):
        # 3 submissions demonstrating edge cases
        return [
            # exact 50% -> should be pass
            {
                "student_id": "stu1",
                "grading_result": {
                    "obtained_marks": 30,
                    "total_marks": 60,
                    "time_taken_seconds": 120,
                },
                "sa_obtained_marks": 20,
                "sa_total_marks": 40,
                "sa_grading_complete": True,
            },
            # zero -> fail
            {
                "student_id": "stu2",
                "grading_result": {
                    "obtained_marks": 0,
                    "total_marks": 60,
                    "time_taken_seconds": 90,
                },
                "sa_obtained_marks": 0,
                "sa_total_marks": 40,
                "sa_grading_complete": True,
            },
            # missing per-part totals -> fallback to exam_total_marks
            {
                "student_id": "stu3",
                "grading_result": {"obtained_marks": 10},  # no total_marks
                "sa_obtained_marks": 5,
                # no sa_total_marks
                "sa_grading_complete": True,
            },
        ]

    # ------------------------------------------------------------------
    # 1. _get_submission_combined_marks: totals present and fallback
    # ------------------------------------------------------------------
    def test_get_submission_combined_marks_totals_and_fallback(self):
        sub_with_totals = {
            "grading_result": {"obtained_marks": 12, "total_marks": 20},
            "sa_obtained_marks": 8,
            "sa_total_marks": 20,
        }
        obt, total = tr._get_submission_combined_marks(
            sub_with_totals, exam_total_marks=100
        )
        self.assertEqual(obt, 20.0)
        self.assertEqual(total, 40.0)  # uses per-part totals

        sub_missing_totals = {
            "grading_result": {"obtained_marks": 15},
            "sa_obtained_marks": 5,
        }
        obt2, total2 = tr._get_submission_combined_marks(
            sub_missing_totals, exam_total_marks=80
        )
        self.assertEqual(obt2, 20.0)
        self.assertEqual(total2, 80.0)  # fallback to exam total marks

    # ------------------------------------------------------------------
    # 2. _compute_exam_report: calculations (avg/high/low/pass/buckets/time)
    # ------------------------------------------------------------------
    @patch("web.tc_reports._get_student_name")
    def test_compute_exam_report_calculations_and_buckets(self, mock_get_student_name):
        exam = self._sample_exam()
        questions = self._sample_questions()
        submissions = self._sample_submissions()

        # deterministic student names
        mock_get_student_name.side_effect = lambda sid: {
            "stu1": "Alice",
            "stu2": "Bob",
            "stu3": "Charlie",
        }.get(sid, sid)

        rpt = tr._compute_exam_report(
            exam, questions=questions, submissions=submissions
        )

        # attempted count
        self.assertEqual(rpt["attempted"], 3)

        # combined obtained marks:
        # stu1: 30 + 20 = 50
        # stu2: 0 + 0 = 0
        # stu3: 10 + 5 = 15 (total denominator uses fallback 100)
        self.assertEqual(rpt["highest_score"], 50)
        self.assertEqual(rpt["lowest_score"], 0)
        self.assertAlmostEqual(rpt["avg_score"], (50 + 0 + 15) / 3.0, places=6)

        # pass rate: only stu1 >=50% -> 1/3 -> 33.333...
        self.assertAlmostEqual(rpt["pass_rate"], (1.0 / 3.0) * 100, places=6)
        self.assertEqual(rpt["pass_count"], 1)
        self.assertEqual(rpt["fail_count"], 2)

        # bucket logic: stu2 -> 0-19, stu3 -> 0-19 (15), stu1 -> 40-59 (50)
        # so expected [2,0,1,0,0]
        self.assertEqual(rpt["bucket_counts"], [2, 0, 1, 0, 0])

        # avg_time_seconds: stu1=120, stu2=90 => mean = 105 (stu3 has no time)
        self.assertEqual(rpt["avg_time_seconds"], 105)

        # top & low student names
        self.assertEqual(rpt["top_student"], "Alice")
        self.assertEqual(rpt["low_student"], "Bob")

    # ------------------------------------------------------------------
    # 3. _exam_short_answers_fully_graded detection logic
    # ------------------------------------------------------------------
    def test_exam_short_answers_fully_graded_various(self):
        # no SA questions -> True regardless of submission flags
        qs_no_sa = [{"question_type": "MCQ"}]
        subs_any = [{"sa_grading_complete": False}, {}]
        self.assertTrue(tr._exam_short_answers_fully_graded(qs_no_sa, subs_any))

        # SA exists, all subs graded -> True
        qs_has_sa = [{"question_type": "SA"}]
        subs_all = [{"sa_grading_complete": True}, {"sa_grading_complete": True}]
        self.assertTrue(tr._exam_short_answers_fully_graded(qs_has_sa, subs_all))

        # SA exists, some not graded -> False
        subs_some = [{"sa_grading_complete": True}, {"sa_grading_complete": False}]
        self.assertFalse(tr._exam_short_answers_fully_graded(qs_has_sa, subs_some))

    # ------------------------------------------------------------------
    # 4. get_exam_results_summary_data: error handling & payload keys/format
    # ------------------------------------------------------------------
    @patch("web.tc_reports._get_all_exams")
    @patch("web.tc_reports._compute_exam_report")
    def test_get_exam_results_summary_data_errors_and_payload(
        self, mock_compute, mock_get_all_exams
    ):
        exam = self._sample_exam()
        mock_get_all_exams.return_value = [exam]

        # compute returns basic report dict
        fake_rd = {
            "num_questions": 2,
            "total_marks": 100,
            "attempted": 3,
            "avg_score": 25.0,
            "highest_score": 50,
            "lowest_score": 0,
            "top_student": "Alice",
            "low_student": "Bob",
            "pass_rate": 33.3333,
            "pass_count": 1,
            "fail_count": 2,
            "bucket_labels": ["0–19", "20–39", "40–59", "60–79", "80–100"],
            "bucket_counts": [2, 0, 1, 0, 0],
        }
        mock_compute.return_value = fake_rd

        # Missing exam_id -> 400
        body, status = tr.get_exam_results_summary_data({})
        self.assertEqual(status, 400)
        self.assertIn("Missing exam_id", body)

        # Non-existent exam -> 404
        body2, status2 = tr.get_exam_results_summary_data({"exam_id": ["nope"]})
        self.assertEqual(status2, 404)

        # Valid exam -> payload contains keys and numeric formatting preserved
        body3, status3 = tr.get_exam_results_summary_data({"exam_id": ["exam1"]})
        self.assertEqual(status3, 200)
        payload = tr.json.loads(body3)  # use module's json to be consistent
        self.assertTrue(payload["ok"])
        self.assertIn("avg_score", payload)
        self.assertIn("bucket_counts", payload)
        self.assertEqual(payload["bucket_counts"], fake_rd["bucket_counts"])

    # ------------------------------------------------------------------
    # 5. get_exam_results_summary_report: HTML contains expected fragments/formatting
    # ------------------------------------------------------------------
    @patch("web.tc_reports._get_all_exams")
    @patch("web.tc_reports._get_questions_for_exam")
    @patch("web.tc_reports._get_submissions_for_exam")
    @patch("web.tc_reports._exam_short_answers_fully_graded")
    @patch("web.tc_reports._get_student_name")
    def test_get_exam_results_summary_report_html_contains_expected(
        self,
        mock_get_student_name,
        mock_sa_check,
        mock_get_subs,
        mock_get_qs,
        mock_get_all_exams,
    ):
        exam = self._sample_exam()
        mock_get_all_exams.return_value = [exam]
        mock_get_qs.return_value = self._sample_questions()
        mock_get_subs.return_value = self._sample_submissions()
        mock_sa_check.return_value = True
        mock_get_student_name.side_effect = lambda sid: {
            "stu1": "Alice",
            "stu2": "Bob",
            "stu3": "Charlie",
        }.get(sid, sid)

        html, status = tr.get_exam_results_summary_report(
            {"exam_id": ["exam1"], "sort": ["best"], "page": ["1"]}
        )
        self.assertEqual(status, 200)

        # Basic pieces
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Exam Results Summary Report", html)
        # Exam overview pieces
        self.assertIn("Testing 101", html)
        self.assertIn("TST100", html)
        self.assertIn("09:00 - 10:00", html)
        self.assertIn("60 mins", html)
        # Class performance header and chart canvas ids
        self.assertIn("Class Performance Summary", html)
        self.assertIn("scoreChart", html)
        self.assertIn("passFailChart", html)

    # ------------------------------------------------------------------
    # 6. Page-level formatting: avg score one decimal, pass rate formatting check
    # ------------------------------------------------------------------
    @patch("web.tc_reports._get_all_exams")
    @patch("web.tc_reports._compute_exam_report")
    def test_display_formatting_avg_and_passrate(
        self, mock_compute, mock_get_all_exams
    ):
        exam = self._sample_exam()
        mock_get_all_exams.return_value = [exam]
        fake_rd = {
            "num_questions": 2,
            "total_marks": 100,
            "attempted": 2,
            "avg_score": 42.0,  # should format as "42.0" in HTML
            "highest_score": 50,
            "lowest_score": 34,
            "top_student": "Alice",
            "low_student": "Bob",
            "pass_rate": 50.0,  # should format as "50.0%"
            "pass_count": 1,
            "fail_count": 1,
            "bucket_labels": ["0–19", "20–39", "40–59", "60–79", "80–100"],
            "bucket_counts": [0, 0, 2, 0, 0],
        }
        mock_compute.return_value = fake_rd

        html, status = tr.get_exam_results_summary_report({"exam_id": ["exam1"]})
        self.assertEqual(status, 200)

        # avg_score formatted with one decimal
        self.assertIn("Average score", html)
        self.assertIn("42.0", html)

        # pass rate formatted with percent sign and one decimal
        self.assertIn("50.0%", html)


if __name__ == "__main__":
    unittest.main()
