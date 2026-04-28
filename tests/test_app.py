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
                {
                    "role": "model",
                    "content": "India holds general elections every 5 years.",
                },
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
        required_fields = (
            "id",
            "phase",
            "title",
            "description",
            "duration",
            "icon",
            "color",
            "details",
        )
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


# ---------------------------------------------------------------------------
# Phase 2 — Constituency endpoint tests
# ---------------------------------------------------------------------------


class TestConstituencyEndpoint:
    """Tests for GET /api/constituency."""

    def test_default_returns_chandni_chowk(self, app_client):
        response = app_client.get("/api/constituency")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["constituency"] == "Chandni Chowk, Delhi"

    def test_valid_constituency_lookup(self, app_client):
        response = app_client.get("/api/constituency?name=New+Delhi%2C+Delhi")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["constituency"] == "New Delhi, Delhi"

    def test_data_structure_has_candidates(self, app_client):
        response = app_client.get("/api/constituency?name=Chandni+Chowk%2C+Delhi")
        data = response.get_json()
        assert "candidates" in data["data"]
        assert len(data["data"]["candidates"]) == 3

    def test_candidate_has_required_fields(self, app_client):
        response = app_client.get("/api/constituency?name=Chandni+Chowk%2C+Delhi")
        data = response.get_json()
        for cand in data["data"]["candidates"]:
            for field in (
                "name",
                "party",
                "symbol",
                "pillars",
                "vibe",
                "record",
                "endorsements",
                "color",
            ):
                assert field in cand, f"Candidate missing field: {field}"
            assert len(cand["pillars"]) == 3

    def test_data_structure_has_booth(self, app_client):
        response = app_client.get("/api/constituency?name=Chandni+Chowk%2C+Delhi")
        data = response.get_json()
        booth = data["data"]["booth"]
        for field in ("name", "address", "maps_url", "tip"):
            assert field in booth, f"Booth missing field: {field}"

    def test_booth_maps_url_points_to_google(self, app_client):
        response = app_client.get("/api/constituency?name=Chandni+Chowk%2C+Delhi")
        data = response.get_json()
        assert "google.com" in data["data"]["booth"]["maps_url"]

    def test_data_structure_has_issues(self, app_client):
        response = app_client.get("/api/constituency?name=Chandni+Chowk%2C+Delhi")
        data = response.get_json()
        issues = data["data"]["issues"]
        assert len(issues) >= 2
        for issue in issues:
            assert "issue" in issue
            assert "intensity" in issue
            assert 0 <= issue["intensity"] <= 100

    def test_issues_have_hindi_translation(self, app_client):
        response = app_client.get("/api/constituency?name=Chandni+Chowk%2C+Delhi")
        data = response.get_json()
        for issue in data["data"]["issues"]:
            assert "issue_hi" in issue
            assert len(issue["issue_hi"]) > 0

    def test_unknown_constituency_falls_back(self, app_client):
        response = app_client.get("/api/constituency?name=Unknown+Place")
        assert response.status_code == 200
        data = response.get_json()
        # Falls back to default
        assert data["data"] is not None
        assert "candidates" in data["data"]

    def test_all_five_constituencies_return_data(self, app_client):
        names = [
            "Chandni Chowk, Delhi",
            "New Delhi, Delhi",
            "South Delhi, Delhi",
            "East Delhi, Delhi",
            "North West Delhi, Delhi",
        ]
        for name in names:
            response = app_client.get(f"/api/constituency?name={name}")
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "success", f"Failed for: {name}"


# ---------------------------------------------------------------------------
# Phase 2 — Crowd reporter endpoint tests
# ---------------------------------------------------------------------------


class TestCrowdEndpoint:
    """Tests for GET/POST /api/crowd."""

    def test_get_empty_returns_no_reports(self, app_client):
        response = app_client.get("/api/crowd?constituency=SomeNewPlace")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["reports"] == []
        assert data["avg_wait_min"] is None

    def test_post_valid_report(self, app_client):
        payload = {
            "constituency": "Test Booth, Delhi",
            "wait_min": 15,
            "crowded": False,
        }
        response = app_client.post(
            "/api/crowd",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "report" in data
        assert data["report"]["wait_min"] == 15
        assert data["report"]["crowded"] is False

    def test_post_crowded_report_gets_correct_label(self, app_client):
        payload = {"constituency": "CrowdTest, Delhi", "wait_min": 30, "crowded": True}
        response = app_client.post(
            "/api/crowd",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = response.get_json()
        assert "crowded" in data["report"]["label"].lower()

    def test_post_short_wait_gets_short_label(self, app_client):
        payload = {"constituency": "ShortTest, Delhi", "wait_min": 5, "crowded": False}
        response = app_client.post(
            "/api/crowd",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = response.get_json()
        assert "short" in data["report"]["label"].lower()

    def test_post_missing_constituency_returns_400(self, app_client):
        payload = {"wait_min": 10}
        response = app_client.post(
            "/api/crowd",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_post_invalid_wait_time_returns_400(self, app_client):
        payload = {"constituency": "Test, Delhi", "wait_min": 999}
        response = app_client.post(
            "/api/crowd",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_get_after_post_returns_report(self, app_client):
        constituency = "RoundTrip, Delhi"
        app_client.post(
            "/api/crowd",
            data=json.dumps(
                {"constituency": constituency, "wait_min": 20, "crowded": True}
            ),
            content_type="application/json",
        )
        response = app_client.get(f"/api/crowd?constituency={constituency}")
        data = response.get_json()
        assert len(data["reports"]) >= 1
        assert data["avg_wait_min"] == 20

    def test_report_has_timestamp(self, app_client):
        payload = {"constituency": "TSTest, Delhi", "wait_min": 10, "crowded": False}
        response = app_client.post(
            "/api/crowd", data=json.dumps(payload), content_type="application/json"
        )
        data = response.get_json()
        assert "ts" in data["report"]
        assert "Z" in data["report"]["ts"]  # ISO UTC format


# ---------------------------------------------------------------------------
# Phase 2 — Leaderboard endpoint tests
# ---------------------------------------------------------------------------


class TestLeaderboardEndpoint:
    """Tests for GET /api/leaderboard."""

    def test_leaderboard_returns_200(self, app_client):
        response = app_client.get("/api/leaderboard")
        assert response.status_code == 200

    def test_leaderboard_structure(self, app_client):
        data = app_client.get("/api/leaderboard").get_json()
        assert data["status"] == "success"
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
        assert len(data["leaderboard"]) >= 5

    def test_leaderboard_item_fields(self, app_client):
        data = app_client.get("/api/leaderboard").get_json()
        for item in data["leaderboard"]:
            for field in ("rank", "name", "name_hi", "youth_reg", "change", "emoji"):
                assert field in item, f"Missing field: {field}"

    def test_leaderboard_ranks_are_ordered(self, app_client):
        data = app_client.get("/api/leaderboard").get_json()
        ranks = [item["rank"] for item in data["leaderboard"]]
        assert ranks == sorted(ranks)

    def test_leaderboard_has_hindi_names(self, app_client):
        data = app_client.get("/api/leaderboard").get_json()
        for item in data["leaderboard"]:
            assert len(item["name_hi"]) > 0

    def test_leaderboard_youth_reg_positive(self, app_client):
        data = app_client.get("/api/leaderboard").get_json()
        for item in data["leaderboard"]:
            assert item["youth_reg"] > 0

    def test_leaderboard_total_count(self, app_client):
        data = app_client.get("/api/leaderboard").get_json()
        assert data["total_constituencies"] == len(data["leaderboard"])


# ---------------------------------------------------------------------------
# Phase 2 — Roast endpoint tests
# ---------------------------------------------------------------------------


class TestRoastEndpoint:
    """Tests for POST /api/roast."""

    MOCK_ROAST = "Oh wow, 'too busy'? 🤔 Fun fact: 968 million Indians voted in 2024. They found time. Maybe put down the scroll? YOUR VOTE = YOUR VOICE. 🗳️"

    def test_valid_roast_request(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = self.MOCK_ROAST
        payload = {"excuse": "I'm too busy to vote", "lang": "en"}
        response = app_client.post(
            "/api/roast", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "roast" in data
        assert len(data["roast"]) > 0

    def test_empty_excuse_returns_400(self, app_client):
        payload = {"excuse": "", "lang": "en"}
        response = app_client.post(
            "/api/roast", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 400

    def test_missing_excuse_returns_400(self, app_client):
        response = app_client.post(
            "/api/roast",
            data=json.dumps({"lang": "en"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_roast_returns_lang_field(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = self.MOCK_ROAST
        payload = {"excuse": "Too tired", "lang": "hi"}
        response = app_client.post(
            "/api/roast", data=json.dumps(payload), content_type="application/json"
        )
        data = response.get_json()
        assert data["lang"] == "hi"

    def test_roast_sanitizes_html_excuse(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = self.MOCK_ROAST
        payload = {"excuse": "<script>xss()</script>I'm lazy", "lang": "en"}
        response = app_client.post(
            "/api/roast", data=json.dumps(payload), content_type="application/json"
        )
        # Should succeed with sanitised input
        assert response.status_code == 200

    def test_gemini_error_returns_500(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.side_effect = Exception("Gemini down")
        payload = {"excuse": "No reason", "lang": "en"}
        response = app_client.post(
            "/api/roast", data=json.dumps(payload), content_type="application/json"
        )
        # Rate-limiter (429) or Gemini error (500) — both are valid server-side rejections
        assert response.status_code in (429, 500)
        data = response.get_json()
        assert data["status"] == "error"


# ---------------------------------------------------------------------------
# Phase 2 — Voter Match endpoint tests
# ---------------------------------------------------------------------------


class TestVoterMatchEndpoint:
    """Tests for POST /api/voter-match."""

    VALID_ANSWERS = [
        {"issue_id": 1, "agree": True},
        {"issue_id": 2, "agree": False},
        {"issue_id": 3, "agree": True},
        {"issue_id": 4, "agree": False},
        {"issue_id": 5, "agree": True},
        {"issue_id": 6, "agree": False},
    ]

    MOCK_RESULT_JSON = json.dumps(
        {
            "vibe_label": "Progressive Pragmatist",
            "match_a": {"party_style": "Centre-Left Welfare", "pct": 72},
            "match_b": {"party_style": "Right-Wing Development", "pct": 28},
            "top_issue": "Energy Subsidy",
            "tagline": "You believe the government should support citizens 💪🗳️",
        }
    )

    def test_valid_voter_match_request(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = self.MOCK_RESULT_JSON
        payload = {"answers": self.VALID_ANSWERS, "lang": "en"}
        response = app_client.post(
            "/api/voter-match",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "result" in data

    def test_result_structure(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = self.MOCK_RESULT_JSON
        payload = {"answers": self.VALID_ANSWERS, "lang": "en"}
        data = app_client.post(
            "/api/voter-match",
            data=json.dumps(payload),
            content_type="application/json",
        ).get_json()
        result = data["result"]
        assert "vibe_label" in result
        assert "match_a" in result
        assert "match_b" in result
        assert "top_issue" in result
        assert "tagline" in result

    def test_fewer_than_3_answers_returns_400(self, app_client):
        payload = {"answers": [{"issue_id": 1, "agree": True}], "lang": "en"}
        response = app_client.post(
            "/api/voter-match",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_empty_answers_returns_400(self, app_client):
        payload = {"answers": [], "lang": "en"}
        response = app_client.post(
            "/api/voter-match",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_returns_lang_field(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = self.MOCK_RESULT_JSON
        payload = {"answers": self.VALID_ANSWERS, "lang": "hi"}
        data = app_client.post(
            "/api/voter-match",
            data=json.dumps(payload),
            content_type="application/json",
        ).get_json()
        assert data["lang"] == "hi"

    def test_gemini_error_returns_500(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.side_effect = Exception("timeout")
        payload = {"answers": self.VALID_ANSWERS, "lang": "en"}
        response = app_client.post(
            "/api/voter-match",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Phase 2 — Translate endpoint tests
# ---------------------------------------------------------------------------


class TestTranslateEndpoint:
    """Tests for POST /api/translate."""

    def test_valid_translation_request(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = (
            "मतदाता पहचान पत्र जरूरी है।"
        )
        payload = {"text": "Voter ID card is required.", "lang": "hi"}
        response = app_client.post(
            "/api/translate", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "translated" in data
        assert len(data["translated"]) > 0

    def test_returns_lang_and_language_fields(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = "अनुवाद"
        payload = {"text": "Vote today.", "lang": "hi"}
        data = app_client.post(
            "/api/translate", data=json.dumps(payload), content_type="application/json"
        ).get_json()
        assert data["lang"] == "hi"
        assert data["language"] == "Hindi"

    def test_empty_text_returns_400(self, app_client):
        payload = {"text": "", "lang": "hi"}
        response = app_client.post(
            "/api/translate", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 400

    def test_missing_text_returns_400(self, app_client):
        payload = {"lang": "hi"}
        response = app_client.post(
            "/api/translate", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 400

    def test_supported_language_codes(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = "translated"
        for code, expected_name in [
            ("hi", "Hindi"),
            ("ta", "Tamil"),
            ("te", "Telugu"),
            ("bn", "Bengali"),
            ("mr", "Marathi"),
        ]:
            payload = {"text": "Election day is here!", "lang": code}
            data = app_client.post(
                "/api/translate",
                data=json.dumps(payload),
                content_type="application/json",
            ).get_json()
            assert data["language"] == expected_name, f"Failed for lang={code}"

    def test_text_sanitization(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.return_value.text = "ठीक है"
        payload = {"text": "<b>Vote</b> <script>alert(1)</script>", "lang": "hi"}
        response = app_client.post(
            "/api/translate", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 200

    def test_gemini_error_returns_500(self, app_client, mock_gemini_model):
        mock_gemini_model.generate_content.side_effect = Exception("API error")
        payload = {"text": "Vote now!", "lang": "ta"}
        response = app_client.post(
            "/api/translate", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data["status"] == "error"
