import unittest
from unittest.mock import patch, ANY

from web.exams import get_exam_list


class ExamListDisplayAndSortTests(unittest.TestCase):
    # ------------------------------------------------------------------
    # Helper sample data
    # ------------------------------------------------------------------
    def _sample_exams(self):
        return [
            {
                "exam_id": "E1",
                "title": "Alpha Exam",
                "description": "Alpha description",
                "duration": 30,
                "exam_date": "2025-12-01",
                "status": "published",
                "start_time": "09:00",
                "end_time": "09:30",
            },
            {
                "exam_id": "E2",
                "title": "Midterm Test",
                "description": "Midterm description",
                "duration": 60,
                "exam_date": "2025-12-03",
                "status": "published",
                "start_time": "10:00",
                "end_time": "11:00",
            },
            {
                "exam_id": "E3",
                "title": "Zebra Quiz",
                "description": "Zebra description",
                "duration": 45,
                "exam_date": "2025-11-28",
                "status": "draft",
                "start_time": "14:00",
                "end_time": "14:45",
            },
        ]

    # ------------------------------------------------------------------
    # 1. Load exam list on page load + table layout + actions column
    # ------------------------------------------------------------------
    @patch("web.exams.render")
    @patch("web.exams.get_all_exams")
    def test_exam_list_renders_with_title_duration_date_and_actions(
        self, mock_get_all_exams, render
    ):
        """Exam list should render exam title, duration, date, and actions column."""
        mock_get_all_exams.return_value = self._sample_exams()

        _, status = get_exam_list()

        self.assertEqual(status, 200, "Exam list should return 200 on load")
        render.assert_called_once_with("exam_list.html", ANY)

        ctx = render.call_args[0][1]
        html = ctx["exam_list_html"]

        # title, duration, date
        self.assertIn("Alpha Exam", html)
        self.assertIn("Midterm Test", html)
        self.assertIn("30 mins", html)
        self.assertIn("60 mins", html)
        self.assertIn("2025-12-01", html)
        self.assertIn("2025-12-03", html)

        # actions: view / edit / delete
        self.assertIn("Edit Details", html)
        self.assertIn("View", html)
        self.assertIn("Delete", html)

    # ------------------------------------------------------------------
    # 2. Handle loading/error state (no exams)
    # ------------------------------------------------------------------
    @patch("web.exams.render")
    @patch("services.exam_service.get_all_exams", return_value=[])
    def test_exam_list_handles_empty_state(self, mock_get_all_exams, render):
        """When there are no exams, show an informative empty state message."""

        _, status = get_exam_list()

        self.assertEqual(status, 200)
        render.assert_called_once_with("exam_list.html", ANY)

        ctx = render.call_args[0][1]
        html = ctx["exam_list_html"]

        self.assertIn("No exams found", html)

    # ------------------------------------------------------------------
    # 3. Sort by date (latest exam_date first)
    # ------------------------------------------------------------------
    @patch("web.exams.render")
    @patch("web.exams.get_all_exams")
    def test_sort_by_date_uses_latest_exam_first(self, mock_get_all_exams, render):
        """Sort by date should order exams by exam_date descending (latest first)."""

        mock_get_all_exams.return_value = self._sample_exams()

        _, status = get_exam_list(sort="date")
        self.assertEqual(status, 200)

        ctx = render.call_args[0][1]
        html = ctx["exam_list_html"]

        pos_midterm = html.index("Midterm Test")  # 2025-12-03
        pos_alpha = html.index("Alpha Exam")  # 2025-12-01
        pos_zebra = html.index("Zebra Quiz")  # 2025-11-28

        self.assertLess(pos_midterm, pos_alpha)
        self.assertLess(pos_alpha, pos_zebra)

    # ------------------------------------------------------------------
    # 4. Sort by title (A → Z)
    # ------------------------------------------------------------------
    @patch("web.exams.render")
    @patch("web.exams.get_all_exams")
    def test_sort_by_title_orders_alphabetically(self, mock_get_all_exams, render):
        """Sort by title should order exams alphabetically by title."""

        # reverse order to prove sorting works, not insertion order
        mock_get_all_exams.return_value = list(reversed(self._sample_exams()))

        _, status = get_exam_list(sort="title")
        self.assertEqual(status, 200)

        ctx = render.call_args[0][1]
        html = ctx["exam_list_html"]

        pos_alpha = html.index("Alpha Exam")
        pos_midterm = html.index("Midterm Test")
        pos_zebra = html.index("Zebra Quiz")

        self.assertLess(pos_alpha, pos_midterm)
        self.assertLess(pos_midterm, pos_zebra)

    # ------------------------------------------------------------------
    # 5. Search by exam title
    # ------------------------------------------------------------------
    @patch("web.exams.render")
    @patch("web.exams.get_all_exams")
    def test_search_filters_by_exam_title(self, mock_get_all_exams, render):
        """Search should filter exams by title (case-insensitive)."""

        mock_get_all_exams.return_value = self._sample_exams()

        _, status = get_exam_list(search="mid", sort="date")
        self.assertEqual(status, 200)

        ctx = render.call_args[0][1]
        html = ctx["exam_list_html"]

        self.assertIn("Midterm Test", html)
        self.assertNotIn("Alpha Exam", html)
        self.assertNotIn("Zebra Quiz", html)


if __name__ == "__main__":
    unittest.main()
