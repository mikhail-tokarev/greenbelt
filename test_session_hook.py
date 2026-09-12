import unittest
from pathlib import Path

from session_hook import calculate_used_tokens

FIXTURES_DIR = Path(__file__).parent / "fixtures"

TRANSCRIPTS = [
    (FIXTURES_DIR / "transcript_1.jsonl", 217677),
    (FIXTURES_DIR / "transcript_2.jsonl", 84677),
]


class TestSessionHook(unittest.TestCase):
    def test_calculate_used_tokens(self):
        for transcript_path, expected in TRANSCRIPTS:
            with self.subTest(fixture=transcript_path.name):
                result = calculate_used_tokens(transcript_path)
                self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
