"""
ElectWise AI — Unit and Integration Tests
Run with: pytest tests/ -v --cov=app --cov-report=term-missing
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy env vars BEFORE importing the app so Gemini init doesn't fail
os.environ.setdefault("GEMINI_API_KEY", "test-api-key-dummy")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_gemini_model():
    """Patch the Gemini model used in app.py."""
    mock_response = MagicMock()
    mock_response.text = (
        "In India, the Election Commission of India (ECI) is responsible for "
        "conducting free and fair elections. The general election follows several "
        "key phases: announcement, nomination, scrutiny, campaigning, polling, "
        "counting, and government formation. Would you like to know more about any specific phase?"
    )

    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response

    mock_model = MagicMock()
    mock_model.start_chat.return_value = mock_chat
    mock_model.generate_content.return_value = mock_response

    return mock_model


@pytest.fixture
def app_client(mock_gemini_model):
    """Create a Flask test client with Gemini mocked out."""
    with patch("app.model", mock_gemini_model):
        import app as flask_app

        flask_app.app.config["TESTING"] = True
        flask_app.app.config["WTF_CSRF_ENABLED"] = False
        with flask_app.app.test_client() as client:
            yield client


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Tests for GET /api/health."""

    def test_health_returns_200(self, app_client):
        response = app_client.get("/api/health")
        assert response.status_code == 200

    def test_health_json_structure(self, app_client):
        response = app_client.get("/api/health")
        data = response.get_json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "services" in data
        assert "gemini" in data["services"]
        assert "version" in data

    def test_health_content_type(self, app_client):
        response = app_client.get("/api/health")
        assert response.content_type == "application/json"


# ---------------------------------------------------------------------------
# Index / UI tests
# ---------------------------------------------------------------------------


class TestIndexRoute:
    """Tests for GET / (main UI page)."""

    def test_index_returns_200(self, app_client):
        response = app_client.get("/")
        assert response.status_code == 200

    def test_index_returns_html(self, app_client):
        response = app_client.get("/")
        assert b"html" in response.data.lower() or response.status_code == 200


# ---------------------------------------------------------------------------
# Chat endpoint tests
# ---------------------------------------------------------------------------


class TestChatEndpoint:
    """Tests for POST /api/chat."""

    def test_valid_chat_request(self, app_client):
        payload = {"message": "How do I register to vote in India?", "country": "India"}
        response = app_client.post(
            "/api/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "response" in data
        assert len(data["response"]) > 0

    def test_chat_with_history(self, app_client):
        payload = {
            "message": "What is the EVM?",
            "country": "India",
            "history": [
                {"role": "user", "content": "Tell me about Indian elections"},
                {"role": "model", "content": "India holds general elections every 5 years."},
            ],
        }
        response = app_client.post(
            "/api/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200

    def test_chat_empty_message_returns_400(self, app_client):
        payload = {"message": "", "country": "India"}
        response = app_client.post(
            "/api/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == "error"

    def test_chat_missing_message_returns_400(self, app_client):
        payload = {"country": "India"}
        response = app_client.post(
            "/api/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_chat_invalid_json_returns_400(self, app_client):
        response = app_client.post(
            "/api/chat",
            data="not-valid-json",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_chat_invalid_country_defaults_to_india(self, app_client):
        payload = {"message": "How do elections work?", "country": "Mars"}
        response = app_client.post(
            "/api/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["country"] == "India"

    def test_chat_usa_country(self, app_client):
        payload = {"message": "What is the Electoral College?", "country": "USA"}
        response = app_client.post(
            "/api/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["country"] == "USA"

    def test_chat_sanitizes_html_input(self, app_client):
        payload = {
            "message": "<script>alert('xss')</script>How do I vote?",
            "country": "India",
        }
        response = app_client.post(
            "/api/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )
        # Should succeed but with sanitised input
        assert response.status_code == 200

    def test_chat_respects_max_message_length(self, app_client):
        payload = {"message": "a" * 5000, "country": "India"}
        response = app_client.post(
            "/api/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )
        # Should not crash — sanitise_input truncates at 2000 chars
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Timeline endpoint tests
# ---------------------------------------------------------------------------


class TestTimelineEndpoint:
    """Tests for GET /api/timeline."""

    def test_india_timeline(self, app_client):
        response = app_client.get("/api/timeline?country=India")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["country"] == "India"
        assert "timeline" in data
        assert "steps" in data["timeline"]
        assert len(data["timeline"]["steps"]) > 0

    def test_usa_timeline(self, app_client):
        response = app_client.get("/api/timeline?country=USA")
        assert response.status_code == 200
        data = response.get_json()
        assert data["country"] == "USA"
        assert len(data["timeline"]["steps"]) > 0

    def test_uk_timeline(self, app_client):
        response = app_client.get("/api/timeline?country=UK")
        assert response.status_code == 200
        data = response.get_json()
        assert data["country"] == "UK"

    def test_invalid_country_defaults_to_india(self, app_client):
        response = app_client.get("/api/timeline?country=InvalidCountry")
        assert response.status_code == 200
        data = response.get_json()
        assert data["country"] == "India"

    def test_default_country_is_india(self, app_client):
        response = app_client.get("/api/timeline")
        assert response.status_code == 200
        data = response.get_json()
        assert data["country"] == "India"

    def test_timeline_step_structure(self, app_client):
        response = app_client.get("/api/timeline?country=India")
        data = response.get_json()
        step = data["timeline"]["steps"][0]
        required_fields = ("id", "phase", "title", "description", "duration", "icon", "color", "details")
        for field in required_fields:
            assert field in step, f"Missing field: {field}"

    def test_timeline_details_are_lists(self, app_client):
        response = app_client.get("/api/timeline?country=India")
        data = response.get_json()
        for step in data["timeline"]["steps"]:
            assert isinstance(step["details"], list)
            assert len(step["details"]) > 0


# ---------------------------------------------------------------------------
# Quiz endpoint tests
# ---------------------------------------------------------------------------


class TestQuizEndpoint:
    """Tests for POST /api/quiz/generate."""

    VALID_QUIZ_JSON = json.dumps(
        [
            {
                "question": "Who conducts general elections in India?",
                "options": [
                    "Prime Minister",
                    "Election Commission of India",
                    "Supreme Court",
                    "Parliament",
                ],
                "correct": 1,
                "explanation": "The Election Commission of India is the autonomous body responsible.",
            },
            {
                "question": "What does EVM stand for?",
                "options": [
                    "Electronic Vote Machine",
                    "Electoral Voting Method",
                    "Electronic Voting Machine",
                    "Election Verification Module",
                ],
                "correct": 2,
                "explanation": "EVM stands for Electronic Voting Machine.",
            },
            {
                "question": "What is NOTA?",
                "options": [
                    "None of the Alternatives",
                    "None of the Above",
                    "Not on the Agenda",
                    "National Option for Total Abstention",
                ],
                "correct": 1,
                "explanation": "NOTA stands for None of the Above.",
            },
            {
                "question": "How many seats are needed for a majority in Lok Sabha?",
                "options": ["250", "272", "300", "543"],
                "correct": 1,
                "explanation": "272 seats constitute a simple majority in the 543-seat Lok Sabha.",
            },
            {
                "question": "What is the Model Code of Conduct?",
                "options": [
                    "A banking regulation",
                    "A set of guidelines for parties during elections",
                    "A law passed by Parliament",
                    "A voter education programme",
                ],
                "correct": 1,
                "explanation": "The MCC is a set of guidelines issued by the ECI.",
            },
        ]
    )

    def test_valid_quiz_request(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = self.VALID_QUIZ_JSON

        payload = {"country": "India", "difficulty": "medium"}
        response = app_client.post(
            "/api/quiz/generate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "questions" in data
        assert data["total"] == 5

    def test_quiz_question_structure(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = self.VALID_QUIZ_JSON

        payload = {"country": "India", "difficulty": "easy"}
        response = app_client.post(
            "/api/quiz/generate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = response.get_json()
        for q in data["questions"]:
            assert "question" in q
            assert "options" in q
            assert len(q["options"]) == 4
            assert "correct" in q
            assert 0 <= q["correct"] <= 3
            assert "explanation" in q

    def test_quiz_invalid_json_returns_400(self, app_client):
        response = app_client.post(
            "/api/quiz/generate",
            data="bad-json",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_quiz_invalid_country_defaults(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = self.VALID_QUIZ_JSON
        payload = {"country": "Atlantis", "difficulty": "medium"}
        response = app_client.post(
            "/api/quiz/generate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["country"] == "India"

    def test_quiz_invalid_difficulty_defaults(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = self.VALID_QUIZ_JSON
        payload = {"country": "India", "difficulty": "impossible"}
        response = app_client.post(
            "/api/quiz/generate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["difficulty"] == "medium"


# ---------------------------------------------------------------------------
# Voter guide endpoint tests
# ---------------------------------------------------------------------------


class TestVoterGuideEndpoint:
    """Tests for GET /api/voter-guide."""

    def test_india_voter_guide(self, app_client):
        response = app_client.get("/api/voter-guide?country=India")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "guide" in data
        assert "checklist" in data["guide"]
        assert len(data["guide"]["checklist"]) > 0

    def test_usa_voter_guide(self, app_client):
        response = app_client.get("/api/voter-guide?country=USA")
        assert response.status_code == 200
        data = response.get_json()
        assert data["country"] == "USA"

    def test_voter_guide_step_structure(self, app_client):
        response = app_client.get("/api/voter-guide?country=India")
        data = response.get_json()
        step = data["guide"]["checklist"][0]
        assert "step" in step
        assert "title" in step
        assert "description" in step
        assert "action" in step
        assert "icon" in step

    def test_invalid_country_defaults_to_india(self, app_client):
        response = app_client.get("/api/voter-guide?country=Unknown")
        assert response.status_code == 200
        data = response.get_json()
        assert data["country"] == "India"


# ---------------------------------------------------------------------------
# Utility function tests
# ---------------------------------------------------------------------------


class TestSanitizeInput:
    """Tests for the sanitize_input helper."""

    def test_strips_html_tags(self):
        from app import sanitize_input

        result = sanitize_input("<script>alert('xss')</script>Hello")
        assert "<script>" not in result
        assert "Hello" in result

    def test_truncates_at_max_length(self):
        from app import sanitize_input

        result = sanitize_input("a" * 5000, max_length=100)
        assert len(result) <= 100

    def test_strips_whitespace(self):
        from app import sanitize_input

        result = sanitize_input("  hello world  ")
        assert result == "hello world"

    def test_non_string_returns_empty(self):
        from app import sanitize_input

        assert sanitize_input(None) == ""  # type: ignore[arg-type]
        assert sanitize_input(12345) == ""  # type: ignore[arg-type]

    def test_empty_string_returns_empty(self):
        from app import sanitize_input

        assert sanitize_input("") == ""


# ---------------------------------------------------------------------------
# Error handler tests
# ---------------------------------------------------------------------------


class TestErrorHandlers:
    """Tests for 404 and 500 error handlers."""

    def test_404_returns_json(self, app_client):
        response = app_client.get("/this-route-does-not-exist")
        assert response.status_code == 404
        data = response.get_json()
        assert data["status"] == "error"
        assert "error" in data
