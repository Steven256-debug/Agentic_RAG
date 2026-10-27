import unittest
from src.rag_pipeline import BM25Index

class TestBM25Index(unittest.TestCase):
    def setUp(self):
        self.bm25 = BM25Index()
        self.docs = [
            "A bank must maintain a minimum capital adequacy ratio of ten percent.",
            "Specialised deposit-taking institutions are subject to liquidity reserve requirements.",
            "Electronic money issuers and mobile money agents must comply with customer due diligence rules.",
            "Cybersecurity directives prescribe mandatory breach notification within twenty-four hours."
        ]
        self.ids = ["doc_1", "doc_2", "doc_3", "doc_4"]
        self.bm25.fit(self.ids, self.docs)

    def test_fit_and_tokenize(self):
        self.assertEqual(self.bm25.corpus_size, 4)
        self.assertIn("capital", self.bm25.idf)
        self.assertIn("cybersecurity", self.bm25.idf)

    def test_search_relevant_match(self):
        results = self.bm25.search("capital adequacy ratio", top_k=2)
        self.assertGreater(len(results), 0)
        top_id, score = results[0]
        self.assertEqual(top_id, "doc_1")
        self.assertGreater(score, 0)

    def test_search_cybersecurity(self):
        results = self.bm25.search("cybersecurity breach notification", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "doc_4")

    def test_search_non_existent_terms(self):
        results = self.bm25.search("cryptocurrency extraterrestrial", top_k=2)
        self.assertEqual(results, [])

if __name__ == "__main__":
    unittest.main()
