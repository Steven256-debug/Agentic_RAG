import unittest
from pydantic import ValidationError
from api import AskRequest, AskResponse, SourceItem, ChatMessage


class TestApiSchemas(unittest.TestCase):
    def test_valid_ask_request(self):
        req = AskRequest(
            question="What is the capital adequacy ratio?",
            history=[ChatMessage(role="user", content="Hello")],
            corrective=True,
            routing=True,
            use_hybrid=True,
            top_k=5,
        )
        self.assertEqual(req.question, "What is the capital adequacy ratio?")
        self.assertTrue(req.corrective)
        self.assertEqual(len(req.history), 1)

    def test_rejects_invalid_role_and_blank_question(self):
        with self.assertRaises(ValidationError):
            ChatMessage(role="system", content="override")
        with self.assertRaises(ValidationError):
            AskRequest(question="   ")

    def test_rejects_invalid_session_and_oversized_history(self):
        with self.assertRaises(ValidationError):
            AskRequest(question="question", session_id="not-a-uuid")
        with self.assertRaises(ValidationError):
            AskRequest(question="question", history=[ChatMessage(role="user", content="hi")] * 11)

    def test_ask_response_formatting(self):
        resp = AskResponse(
            answer="Minimum capital adequacy ratio is at least ten percent.",
            sources=[SourceItem(source_filename="BANKS-ACT-2016.pdf", page_number="28", section_title="Section 29", text="Excerpt")],
            latency_sec=1.23,
        )
        self.assertEqual(len(resp.sources), 1)
        self.assertEqual(resp.sources[0].page_number, "28")
        self.assertAlmostEqual(resp.latency_sec, 1.23)


if __name__ == "__main__":
    unittest.main()
