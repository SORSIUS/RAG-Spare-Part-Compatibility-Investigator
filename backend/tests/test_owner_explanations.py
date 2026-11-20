import unittest
from app.models.chat import GeneratedAnswer
from app.services.answer_service import validate_citations, CitationError
from app.integrations.groq_client import SYSTEM_PROMPT

class OwnerExplanationTests(unittest.TestCase):
    def test_general_education_does_not_require_fabricated_citations(self):
        answer = GeneratedAnswer(insufficient_evidence=False, claims=[], general_guidance="A cabin filter cleans the air entering the cabin.", unknowns=[], follow_up_questions=[])
        validate_citations(answer, [])

    def test_general_guidance_cannot_rescue_a_fabricated_part_claim(self):
        answer = GeneratedAnswer(insufficient_evidence=False, claims=[{"text":"Part ABC123 fits.","citations":[{"source_id":"S99","quote":"invented source text"}]}], general_guidance="Filters clean the air.", unknowns=[], follow_up_questions=[])
        with self.assertRaises(CitationError):
            validate_citations(answer, [])

    def test_prompt_requires_both_source_use_and_fitment_limits(self):
        self.assertIn("Use sources whenever they answer", SYSTEM_PROMPT)
        self.assertIn("Do not put vehicle-specific fitment", SYSTEM_PROMPT)
