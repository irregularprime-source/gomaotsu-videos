"""Offline checks for the search collector's period arguments (used by manual Actions runs)."""
import io
import os
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import search_collect


class PeriodArgumentTests(unittest.TestCase):
    def run_main(self, *args):
        with mock.patch.dict(os.environ, {"YOUTUBE_API_KEY": "AUDIT_DUMMY_KEY_DO_NOT_USE"}), \
                mock.patch.object(search_collect, "collect_search", return_value=0) as collect, \
                mock.patch("sys.argv", ["search_collect.py", *args]), \
                mock.patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as exit_info:
                search_collect.main()
        return exit_info.exception.code, collect

    def test_period_is_passed_as_utc_day_bounds(self):
        code, collect = self.run_main("--after", "2025-01-01", "--before", "2025-01-08", "--dry-run")
        self.assertEqual(code, 0)
        collect.assert_called_once_with(True, "2025-01-01T00:00:00Z", "2025-01-08T00:00:00Z")

    def test_invalid_dates_are_rejected_before_searching(self):
        for args in [
            ("--after", "2025-1-1"),
            ("--after", "20250101"),
            ("--after", "2025-01-01T00:00:00Z"),
            ("--after", "2025-01-01; echo x"),
            ("--before", "2025-01-08"),
            ("--after", "2025-01-08", "--before", "2025-01-01"),
            ("--after", "2025-01-08", "--before", "2025-01-08"),
        ]:
            with self.subTest(args=args):
                code, collect = self.run_main(*args)
                self.assertEqual(code, 2)
                collect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
