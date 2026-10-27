import unittest
from src.chunk import get_chunks, get_resilient_encoder

class TestChunking(unittest.TestCase):
    def setUp(self):
        self.encoder = get_resilient_encoder()

    def test_empty_string(self):
        chunks = get_chunks("")
        self.assertEqual(chunks, [])
        chunks = get_chunks("   ")
        self.assertEqual(chunks, [])

    def test_short_text(self):
        text = "The Bank of Ghana regulates all banks and specialized deposit-taking institutions."
        chunks = get_chunks(text, max_tokens=100, overlap=10)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_overlap_sliding_window(self):
        # Create repetitive text longer than 50 tokens
        words = ["clause", "compliance", "regulation", "bank", "section"] * 20
        long_text = " ".join(words)
        
        chunks = get_chunks(long_text, max_tokens=20, overlap=5)
        self.assertGreater(len(chunks), 1)
        # Verify chunks have content
        for c in chunks:
            self.assertTrue(len(c.strip()) > 0)

if __name__ == "__main__":
    unittest.main()
