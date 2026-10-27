import unittest
import os
from pathlib import Path
from src.config import (
    SRC_DIR,
    PROJECT_ROOT,
    EMBEDDING_MODEL_NAME,
    GENERATION_MODEL_NAME,
    FAST_MODEL_NAME,
    SYSTEM_PROMPT,
    ALLOWED_ORIGINS
)

class TestConfig(unittest.TestCase):
    def test_paths_exist(self):
        self.assertTrue(SRC_DIR.exists(), "SRC_DIR should exist")
        self.assertTrue(PROJECT_ROOT.exists(), "PROJECT_ROOT should exist")

    def test_model_names(self):
        self.assertEqual(EMBEDDING_MODEL_NAME, "all-MiniLM-L6-v2")
        self.assertTrue("gemini" in GENERATION_MODEL_NAME.lower())
        self.assertTrue("gemini" in FAST_MODEL_NAME.lower())

    def test_system_prompt_compliance(self):
        self.assertIn("ComplyGH", SYSTEM_PROMPT)
        self.assertIn("Ghanaian financial regulations", SYSTEM_PROMPT)
        self.assertIn("cite the exact source document name", SYSTEM_PROMPT)

    def test_allowed_origins(self):
        self.assertIsInstance(ALLOWED_ORIGINS, list)
        self.assertTrue(any("3000" in o for o in ALLOWED_ORIGINS))

if __name__ == "__main__":
    unittest.main()
