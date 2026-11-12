import unittest

from win95lx.apps.wordpad import Run, Style, read_rtf, write_rtf


class WordPadRTFTests(unittest.TestCase):
    def test_round_trip_preserves_styles_unicode_and_whitespace(self):
        runs = [
            Run("Text {with} café, 😀 and \\"),
            Run("\n\tformatted", Style(bold=True, italic=True, underline=True, half_points=37)),
            Run(" plain"),
        ]
        self.assertEqual(read_rtf(write_rtf(runs)), runs)

    def test_nested_groups_restore_style_and_hide_metadata(self):
        document = (
            br"{\rtf1\ansi{\fonttbl{\f0 Times New Roman;}}\fs20 "
            br"one{\b two{\i three}four}{\*\private secret}five}"
        )
        self.assertEqual(
            read_rtf(document),
            [
                Run("one"),
                Run("two", Style(bold=True)),
                Run("three", Style(bold=True, italic=True)),
                Run("four", Style(bold=True)),
                Run("five"),
            ],
        )

    def test_rejects_incomplete_document(self):
        with self.assertRaises(ValueError):
            read_rtf(br"{\rtf1 unfinished")
