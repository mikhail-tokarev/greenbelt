import os
import unittest

from session_hook import calculate_used_tokens

EXAMPLE = os.path.join(os.path.dirname(__file__), "test_transcript.jsonl")


class TestSessionHook(unittest.TestCase):
    def test_calculate_used_tokens(self):
        result = calculate_used_tokens(EXAMPLE)
        self.assertEqual(result, 11445)


if __name__ == "__main__":
    unittest.main()
