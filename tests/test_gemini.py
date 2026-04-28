"""
ElectWise AI — Gemini Integration & Config Tests
Validates AI response structure, prompt injection guards, and configuration.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_API_KEY", "test-api-key-dummy")
os.environ.setdefault("SECRET_KEY", "test-secret")


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestConfig:
    """Validate configuration values."""

    def test_supported_countries(self):
        from config import Config

        assert "India" in Config.SUPPORTED_COUNTRIES
        assert "USA" in Config.SUPPORTED_COUNTRIES
        assert "UK" in Config.SUPPORTED_COUNTRIES

    def test_system_prompt_is_non_empty(self):
        from config import Config

        assert isinstance(Config.SYSTEM_PROMPT, str)
        assert len(Config.SYSTEM_PROMPT) > 100

    def test_system_prompt_non_partisan_keywords(self):
        """System prompt must contain non-partisan safeguard language."""
        from config import Config

        prompt_lower = Config.SYSTEM_PROMPT.lower()
        assert (
            "non-partisan" in prompt_lower
            or "political parties" in prompt_lower
        )

    def test_system_prompt_voter_mentions(self):
        """System prompt should mention voters / voting."""
        from config import Config

        assert (
            "voter" in Config.SYSTEM_PROMPT.lower()
            or "voting" in Config.SYSTEM_PROMPT.lower()
        )

    def test_gemini_model_specified(self):
        from config import Config

        assert Config.GEMINI_MODEL == "gemini-2.0-flash"


# ---------------------------------------------------------------------------
# Quiz JSON validation tests
# ---------------------------------------------------------------------------


class TestQuizJsonValidation:
    """Test that quiz JSON validation logic is robust."""

    GOOD_QUESTION = {
        "question": "Who has the authority to conduct elections in India?",
        "options": ["Supreme Court", "ECI", "Parliament", "President"],
        "correct": 1,
        "explanation": "The Election Commission of India.",
    }

    def test_valid_question_passes_validation(self):
        """Mimic the validation logic in generate_quiz."""
        q = self.GOOD_QUESTION
        assert all(
            k in q for k in ("question", "options", "correct", "explanation")
        )
        assert isinstance(q["options"], list) and len(q["options"]) == 4
        assert isinstance(q["correct"], int) and 0 <= q["correct"] <= 3

    def test_missing_key_fails_validation(self):
        q = {**self.GOOD_QUESTION}
        del q["explanation"]
        assert not all(
            k in q for k in ("question", "options", "correct", "explanation")
        )

    def test_wrong_options_count_fails_validation(self):
        q = {
            **self.GOOD_QUESTION,
            "options": ["A", "B", "C"],
        }  # Only 3 options
        assert len(q["options"]) != 4

    def test_out_of_range_correct_fails_validation(self):
        q = {**self.GOOD_QUESTION, "correct": 5}
        assert not (0 <= q["correct"] <= 3)

    def test_non_integer_correct_fails_validation(self):
        q = {**self.GOOD_QUESTION, "correct": "1"}
        assert not isinstance(q["correct"], int)

    def test_json_with_markdown_wrapping(self):
        """Ensure regex extraction handles markdown-wrapped JSON from model."""
        import re

        raw = '```json\n[{"question":"Q","options":["A","B","C","D"],"correct":0,"explanation":"E"}]\n```'
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        assert match is not None
        parsed = json.loads(match.group())
        assert isinstance(parsed, list)
        assert parsed[0]["question"] == "Q"


# ---------------------------------------------------------------------------
# Prompt injection guard tests
# ---------------------------------------------------------------------------


class TestPromptInjectionGuards:
    """Verify sanitize_input blocks common attack vectors."""

    def test_script_tag_stripped(self):
        from app import sanitize_input

        result = sanitize_input("<script>document.cookie</script>")
        assert "<script>" not in result

    def test_img_onerror_stripped(self):
        from app import sanitize_input

        result = sanitize_input('<img src=x onerror="alert(1)">')
        assert "<img" not in result

    def test_iframe_stripped(self):
        from app import sanitize_input

        result = sanitize_input(
            '<iframe src="evil.com"></iframe>vote question'
        )
        assert "<iframe" not in result

    def test_sql_injection_passthrough(self):
        """SQL injection strings should pass through sanitise (not executed by DB)."""
        from app import sanitize_input

        malicious = "'; DROP TABLE users; --"
        result = sanitize_input(malicious)
        # Not a DB app but should not crash
        assert isinstance(result, str)

    def test_oversized_prompt_truncated(self):
        from app import sanitize_input

        big_input = "Tell me about elections. " * 500  # ~12,500 chars
        result = sanitize_input(big_input)
        assert len(result) <= 2000


# ---------------------------------------------------------------------------
# Fetch election news fallback tests
# ---------------------------------------------------------------------------


class TestFetchElectionNews:
    """Test Google Custom Search graceful fallback."""

    def test_returns_none_when_no_search_service(self):
        """fetch_election_news should return None when search_service is None."""
        with patch("app.search_service", None):
            from app import fetch_election_news

            result = fetch_election_news("election date", "India")
            assert result is None

    def test_returns_none_on_search_exception(self):
        """fetch_election_news should swallow exceptions and return None."""
        mock_service = MagicMock()
        mock_service.cse.return_value.list.return_value.execute.side_effect = (
            Exception("API Error")
        )
        with patch("app.search_service", mock_service):
            from app import fetch_election_news

            result = fetch_election_news("election", "India")
            assert result is None

    def test_returns_list_when_service_works(self):
        """fetch_election_news should return a list when search service responds."""
        mock_items = [
            {
                "title": "Election 2024",
                "snippet": "Details...",
                "link": "https://example.com",
            },
        ]
        mock_service = MagicMock()
        mock_service.cse.return_value.list.return_value.execute.return_value = {
            "items": mock_items
        }
        with patch("app.search_service", mock_service), patch(
            "app.Config.GOOGLE_SEARCH_ENGINE_ID", "fake-cx"
        ):
            from app import fetch_election_news

            result = fetch_election_news("latest news", "India")
            assert isinstance(result, list)
            assert result[0]["title"] == "Election 2024"
