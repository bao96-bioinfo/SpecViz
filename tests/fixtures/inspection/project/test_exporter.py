import unittest

from exporter import export_rows


class ExportTests(unittest.TestCase):
    def test_row_limit(self):
        self.assertEqual(len(export_rows("owner", "owner", list(range(120)))), 100)

    def test_owner_guard(self):
        with self.assertRaises(PermissionError):
            export_rows("owner", "someone else", [])
