"""Checks for the standalone dataset review page."""

import tempfile
import unittest
from pathlib import Path

from review import write_review_index


class ReviewIndexTests(unittest.TestCase):
    def test_lists_completed_skipped_and_failed_with_safe_html(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            sources = [Path('a & b #1.jpg'), Path('existing.png'), Path('failed.webp')]
            (output / 'a & b #1.png').touch()
            (output / 'a & b #1.txt').write_text('person <script>alert(1)</script>', encoding='utf-8')
            (output / 'existing.png').touch()
            (output / 'existing.txt').write_text('a portrait', encoding='utf-8')
            records = [
                {'file': 'a & b #1.jpg', 'status': 'ok'},
                {'file': 'failed.webp', 'status': 'error: bad <image>'},
            ]

            page = write_review_index(output, sources, records).read_text(encoding='utf-8')

            self.assertIn('a%20%26%20b%20%231.png', page)
            self.assertIn('a &amp; b #1.jpg', page)
            self.assertIn('person &lt;script&gt;alert(1)&lt;/script&gt;', page)
            self.assertNotIn('<script>', page)
            self.assertIn('既存', page)
            self.assertIn('error: bad &lt;image&gt;', page)
            self.assertIn('確認可能 2 件', page)
            self.assertIn('処理失敗・読み取り失敗 1 件', page)

    def test_missing_pair_is_marked_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'partial.png').touch()

            page = write_review_index(output, [Path('partial.jpg')], []).read_text(encoding='utf-8')

            self.assertIn('未完成 1 件', page)
            self.assertNotIn('<img ', page)


if __name__ == '__main__':
    unittest.main()
