"""
ElectWise AI — Election Process Education Assistant
Flask backend with Google Gemini 2.0 Flash integration.

Endpoints:
  GET  /                    — Serve main application UI
  GET  /api/health          — Health check
  POST /api/chat            — AI-powered election Q&A
  GET  /api/timeline        — Structured election timeline data
  POST /api/quiz/generate   — AI-generated civics quiz
  GET  /api/voter-guide     — Voter registration checklist
"""

import json
import logging
import os
import re
from datetime import datetime
from functools import wraps
from typing import Optional

import google.generativeai as genai
from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from dotenv import load_dotenv

from config import Config

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# ---------------------------------------------------------------------------
# Security — Content Security Policy (Flask-Talisman)
# ---------------------------------------------------------------------------

csp = {
    "default-src": ["'self'"],
    "script-src": [
        "'self'",
        "'unsafe-inline'",
        "https://fonts.googleapis.com",
    ],
    "style-src": [
        "'self'",
        "'unsafe-inline'",
        "https://fonts.googleapis.com",
        "https://fonts.gstatic.com",
    ],
    "font-src": ["'self'", "https://fonts.gstatic.com"],
    "img-src": ["'self'", "data:", "https:"],
    "connect-src": ["'self'"],
}

Talisman(
    app,
    content_security_policy=csp,
    force_https=False,          # Set True behind a load balancer / Cloud Run
    strict_transport_security=True,
    session_cookie_secure=False,  # False for local HTTP dev; True in prod
    session_cookie_http_only=True,
    referrer_policy="strict-origin-when-cross-origin",
)

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "30 per minute"],
    storage_uri="memory://",
)

# ---------------------------------------------------------------------------
# Google Gemini 2.0 Flash
# ---------------------------------------------------------------------------

gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
model: Optional[genai.GenerativeModel] = None

if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel(
        model_name=Config.GEMINI_MODEL,
        system_instruction=Config.SYSTEM_PROMPT,
    )
    logger.info("Gemini 2.0 Flash model initialised successfully.")
else:
    logger.warning("GEMINI_API_KEY not set — AI features are disabled.")

# ---------------------------------------------------------------------------
# Google Custom Search (optional — graceful fallback when keys are absent)
# ---------------------------------------------------------------------------

search_service = None

if Config.GOOGLE_SEARCH_API_KEY and Config.GOOGLE_SEARCH_ENGINE_ID:
    try:
        from googleapiclient.discovery import build

        search_service = build(
            "customsearch",
            "v1",
            developerKey=Config.GOOGLE_SEARCH_API_KEY,
        )
        logger.info("Google Custom Search API initialised successfully.")
    except Exception as exc:
        logger.warning("Google Custom Search init failed: %s", exc)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def sanitize_input(text: str, max_length: int = 2000) -> str:
    """Sanitise user input — strip HTML tags, limit length, and strip whitespace."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<[^>]+>", "", text)   # Remove HTML tags
    text = text[:max_length]               # Enforce max length
    return text.strip()


def require_gemini(f):
    """Decorator: return 503 when Gemini is not configured."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if model is None:
            return (
                jsonify(
                    {
                        "error": (
                            "AI service unavailable. "
                            "Please set the GEMINI_API_KEY environment variable."
                        ),
                        "status": "error",
                    }
                ),
                503,
            )
        return f(*args, **kwargs)

    return decorated


def fetch_election_news(query: str, country: str) -> Optional[list]:
    """
    Fetch recent election news via Google Custom Search API.
    Returns None gracefully when the service is not configured.
    """
    if not search_service:
        return None
    try:
        result = (
            search_service.cse()
            .list(
                q=f"{country} election {query}",
                cx=Config.GOOGLE_SEARCH_ENGINE_ID,
                num=3,
                dateRestrict="m1",   # Last month
            )
            .execute()
        )
        items = result.get("items", [])
        return [
            {
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "link": item.get("link"),
            }
            for item in items
        ]
    except Exception as exc:
        logger.warning("Custom Search request failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Static timeline data
# ---------------------------------------------------------------------------

TIMELINES: dict = {
    "India": {
        "title": "Indian General Election Process",
        "description": "The world's largest democratic exercise — understanding the Lok Sabha election process step by step.",
        "steps": [
            {
                "id": 1,
                "phase": "Announcement",
                "title": "Election Announcement",
                "description": "The Election Commission of India (ECI) announces the election schedule. The Model Code of Conduct (MCC) comes into effect immediately.",
                "duration": "~4–6 weeks before polling",
                "icon": "📢",
                "color": "#6366f1",
                "details": [
                    "ECI announces multi-phase polling schedule",
                    "Model Code of Conduct (MCC) activated immediately",
                    "Government spending restrictions enforced",
                    "Political parties officially notified",
                ],
            },
            {
                "id": 2,
                "phase": "Nomination",
                "title": "Candidate Nomination",
                "description": "Candidates file nomination papers with the Returning Officer. A security deposit is mandatory.",
                "duration": "~3–4 weeks before polling",
                "icon": "📝",
                "color": "#8b5cf6",
                "details": [
                    "Candidates file Form 2B nomination",
                    "Security deposit: ₹25,000 (General) / ₹12,500 (SC/ST)",
                    "Affidavit on criminal record and assets required",
                    "Proposers from constituency needed",
                ],
            },
            {
                "id": 3,
                "phase": "Scrutiny",
                "title": "Scrutiny of Nominations",
                "description": "Returning Officer examines nomination papers for validity. Defective nominations can be rejected.",
                "duration": "1 day (fixed schedule)",
                "icon": "🔍",
                "color": "#a855f7",
                "details": [
                    "Returning Officer verifies eligibility",
                    "Checks age, citizenship, constituency enrollment",
                    "Checks for disqualifications under RPA 1951",
                    "Candidates may be present with their agents",
                ],
            },
            {
                "id": 4,
                "phase": "Withdrawal",
                "title": "Withdrawal of Candidature",
                "description": "Candidates may withdraw their nominations within a 2-day window after scrutiny.",
                "duration": "2 days after scrutiny",
                "icon": "🔄",
                "color": "#ec4899",
                "details": [
                    "Written notice to Returning Officer required",
                    "Final list of contesting candidates published",
                    "Election symbols allotted to candidates",
                ],
            },
            {
                "id": 5,
                "phase": "Campaigning",
                "title": "Election Campaign",
                "description": "Parties campaign across constituencies under strict expenditure limits. Campaign ends 48 hours before polling.",
                "duration": "2–3 weeks",
                "icon": "🗣️",
                "color": "#f59e0b",
                "details": [
                    "Expenditure limit: ₹75–95 lakh per candidate",
                    "Flying squads monitor MCC violations",
                    "Paid news monitored by Media Certification Committee",
                    "48-hour silence period before voting",
                ],
            },
            {
                "id": 6,
                "phase": "Voting",
                "title": "Polling Day",
                "description": "Registered voters cast votes using EVM + VVPAT. Polling typically runs 7 AM – 6 PM.",
                "duration": "Single day (per phase)",
                "icon": "🗳️",
                "color": "#10b981",
                "details": [
                    "Voter ID or 12 alternative documents accepted",
                    "EVM records vote; VVPAT provides paper trail",
                    "NOTA (None of the Above) option available",
                    "Persons with Disabilities get priority access",
                ],
            },
            {
                "id": 7,
                "phase": "Counting",
                "title": "Vote Counting",
                "description": "Votes are counted at designated counting centres. Results are declared constituency by constituency.",
                "duration": "Counting day (begins ~5 AM)",
                "icon": "🔢",
                "color": "#06b6d4",
                "details": [
                    "Postal ballots counted first",
                    "EVM counting progresses round by round",
                    "5 VVPAT slips verified per assembly segment",
                    "Returning Officer declares result officially",
                ],
            },
            {
                "id": 8,
                "phase": "Government",
                "title": "Government Formation",
                "description": "The party or coalition with 272+ seats is invited by the President to form the government.",
                "duration": "Within days of result",
                "icon": "🏛️",
                "color": "#3b82f6",
                "details": [
                    "President invites majority party/coalition leader",
                    "Party elects leader as Prime Minister",
                    "Cabinet sworn in by the President",
                    "New government assumes office",
                ],
            },
        ],
    },
    "USA": {
        "title": "U.S. Presidential Election Process",
        "description": "America's quadrennial democratic process — from primaries to inauguration.",
        "steps": [
            {
                "id": 1,
                "phase": "Primaries",
                "title": "Primaries & Caucuses",
                "description": "Each party holds state-level contests to select a presidential nominee through delegate voting.",
                "duration": "January – June (election year)",
                "icon": "🗓️",
                "color": "#6366f1",
                "details": [
                    "Iowa caucuses traditionally first",
                    "Super Tuesday: multiple states vote simultaneously",
                    "Delegates pledged to candidates",
                    "Winner-take-all vs. proportional allocation",
                ],
            },
            {
                "id": 2,
                "phase": "Conventions",
                "title": "National Conventions",
                "description": "Parties formally nominate their presidential and vice-presidential candidates.",
                "duration": "July – August",
                "icon": "🎪",
                "color": "#8b5cf6",
                "details": [
                    "Delegates formally cast votes for nominee",
                    "VP nominee usually announced before convention",
                    "Party platform adopted",
                    "Nominee delivers acceptance speech",
                ],
            },
            {
                "id": 3,
                "phase": "Campaign",
                "title": "General Election Campaign",
                "description": "Nominees campaign nationwide, focusing on swing states. Three presidential debates held.",
                "duration": "September – early November",
                "icon": "🗣️",
                "color": "#ec4899",
                "details": [
                    "3 presidential debates + 1 VP debate",
                    "Key swing states: PA, MI, WI, AZ, GA, NV",
                    "PAC/Super PAC fundraising",
                    "State-level voter registration deadlines",
                ],
            },
            {
                "id": 4,
                "phase": "Election Day",
                "title": "Election Day",
                "description": "Registered voters cast ballots (in-person, early vote, or mail-in) on the first Tuesday after the first Monday in November.",
                "duration": "First Tuesday of November",
                "icon": "🗳️",
                "color": "#10b981",
                "details": [
                    "Early voting available in 45+ states",
                    "Mail-in ballots available in most states",
                    "Voter ID requirements vary by state",
                    "Polls close 7–8 PM local time",
                ],
            },
            {
                "id": 5,
                "phase": "Electoral College",
                "title": "Electoral College Vote",
                "description": "538 Electors cast electoral votes. 270 votes needed to win the presidency.",
                "duration": "Mid-December",
                "icon": "🗺️",
                "color": "#f59e0b",
                "details": [
                    "Winner-take-all in 48 states + DC",
                    "Maine & Nebraska: congressional district method",
                    "Faithless electors fined in many states",
                    "Electors meet in state capitals to vote",
                ],
            },
            {
                "id": 6,
                "phase": "Certification",
                "title": "Congressional Certification",
                "description": "Congress meets in joint session on January 6 to certify Electoral College results.",
                "duration": "January 6th",
                "icon": "📜",
                "color": "#06b6d4",
                "details": [
                    "VP presides over joint session",
                    "Electoral votes counted state by state",
                    "Objections require both chambers",
                    "Official winner declared",
                ],
            },
            {
                "id": 7,
                "phase": "Inauguration",
                "title": "Presidential Inauguration",
                "description": "The President-elect is sworn in on the steps of the U.S. Capitol on January 20.",
                "duration": "January 20th",
                "icon": "🏛️",
                "color": "#3b82f6",
                "details": [
                    "Chief Justice administers oath of office",
                    "President delivers inaugural address",
                    "Outgoing president departs",
                    "New administration begins",
                ],
            },
        ],
    },
    "UK": {
        "title": "UK General Election Process",
        "description": "Understanding the United Kingdom's parliamentary election system.",
        "steps": [
            {
                "id": 1,
                "phase": "Dissolution",
                "title": "Parliament Dissolution",
                "description": "The Prime Minister advises the King to dissolve Parliament, triggering a general election.",
                "duration": "25 days before polling",
                "icon": "📢",
                "color": "#6366f1",
                "details": [
                    "Fixed-term parliaments with 5-year maximum",
                    "King formally dissolves Parliament",
                    "Caretaker government operates",
                    "Writ of election issued to constituencies",
                ],
            },
            {
                "id": 2,
                "phase": "Nomination",
                "title": "Candidate Nomination",
                "description": "Prospective parliamentary candidates submit nomination papers and a £500 deposit.",
                "duration": "Following dissolution",
                "icon": "📝",
                "color": "#8b5cf6",
                "details": [
                    "£500 deposit required (returned if 5%+ votes)",
                    "10 constituency electors must sign nomination",
                    "Candidates must be UK / Commonwealth / Irish citizens",
                    "Candidates submit spending return forms",
                ],
            },
            {
                "id": 3,
                "phase": "Campaign",
                "title": "Short Campaign",
                "description": "Parties campaign across 650 constituencies. Strict spending limits enforced by the Electoral Commission.",
                "duration": "~25 days",
                "icon": "🗣️",
                "color": "#ec4899",
                "details": [
                    "BBC leaders' debate broadcast",
                    "Party election broadcasts on TV",
                    "Constituency spending limit: ~£15,000",
                    "Postal and proxy voting available",
                ],
            },
            {
                "id": 4,
                "phase": "Polling",
                "title": "Polling Day",
                "description": "Registered voters visit their polling station or vote by post. Polls open 7 AM – 10 PM.",
                "duration": "One Thursday",
                "icon": "🗳️",
                "color": "#10b981",
                "details": [
                    "Photo ID required since 2023",
                    "First-Past-The-Post (FPTP) system",
                    "Each voter marks an X on the ballot",
                    "Postal votes counted at returning officer's station",
                ],
            },
            {
                "id": 5,
                "phase": "Counting",
                "title": "Counting & Results",
                "description": "Votes counted overnight at local count centres. Most results declared by early morning.",
                "duration": "Overnight (election night)",
                "icon": "🔢",
                "color": "#06b6d4",
                "details": [
                    "Returning Officer declares local winner",
                    "BBC and media project national outcome",
                    "Party with 326+ seats wins majority",
                    "Exit poll released at 10 PM",
                ],
            },
            {
                "id": 6,
                "phase": "Formation",
                "title": "Government Formation",
                "description": "The party leader with a Commons majority is invited by the King to form the government.",
                "duration": "Day after election",
                "icon": "🏛️",
                "color": "#3b82f6",
                "details": [
                    "King invites majority party leader",
                    "Leader becomes Prime Minister",
                    "Cabinet appointed",
                    "King's Speech sets legislative agenda",
                ],
            },
        ],
    },
}

VOTER_GUIDE: dict = {
    "India": {
        "title": "Indian Voter Registration & Voting Guide",
        "checklist": [
            {
                "step": 1,
                "title": "Check Eligibility",
                "description": "You must be an Indian citizen, at least 18 years old on the qualifying date (1 January of the registration year), and ordinarily resident in the constituency.",
                "action": "Verify your eligibility on the National Voters' Service Portal (nvsp.in)",
                "icon": "✅",
            },
            {
                "step": 2,
                "title": "Register / Update Voter ID",
                "description": "Apply for a new Voter ID (EPIC) or update existing details using Form 6 (new registration), Form 8 (corrections), or Form 8A (shifting constituency).",
                "action": "Visit nvsp.in or your local Electoral Registration Officer (ERO)",
                "icon": "📋",
            },
            {
                "step": 3,
                "title": "Verify Your Name on Electoral Roll",
                "description": "Confirm your name appears on the Electoral Roll for your constituency before the election is announced.",
                "action": "Search on nvsp.in using your Voter ID number or name + address",
                "icon": "🔍",
            },
            {
                "step": 4,
                "title": "Know Your Polling Station",
                "description": "Your Voter Slip / EPIC card shows your designated polling booth. You can also check online.",
                "action": "Find your polling station on nvsp.in or ECI Voter Helpline App",
                "icon": "📍",
            },
            {
                "step": 5,
                "title": "Carry Valid ID to the Booth",
                "description": "Bring your Voter ID (EPIC) or one of 12 alternative photo IDs: Aadhaar, Passport, Driving License, PAN Card, MNREGS Job Card, etc.",
                "action": "Keep your Voter Slip + ID ready before heading to the booth",
                "icon": "🪪",
            },
            {
                "step": 6,
                "title": "Cast Your Vote",
                "description": "Press the blue button next to your chosen candidate on the EVM. The VVPAT will briefly display a slip confirming your choice.",
                "action": "Vote confidently — your vote is secret and secure",
                "icon": "🗳️",
            },
        ],
    },
    "USA": {
        "title": "U.S. Voter Registration & Voting Guide",
        "checklist": [
            {
                "step": 1,
                "title": "Check Eligibility",
                "description": "You must be a U.S. citizen, at least 18 years old by Election Day, and meet your state's residency requirements.",
                "action": "Check USA.gov/register-to-vote for state-specific rules",
                "icon": "✅",
            },
            {
                "step": 2,
                "title": "Register to Vote",
                "description": "Register online, by mail, or in person. Deadlines vary by state (15–30 days before election, or same-day in some states).",
                "action": "Register at vote.gov — takes under 5 minutes",
                "icon": "📋",
            },
            {
                "step": 3,
                "title": "Verify Your Registration",
                "description": "Confirm your registration status and polling location before Election Day.",
                "action": "Check at vote.gov or your state's Secretary of State website",
                "icon": "🔍",
            },
            {
                "step": 4,
                "title": "Request Mail-In Ballot (if applicable)",
                "description": "Most states allow voting by mail. Request your ballot early to ensure it arrives and is returned in time.",
                "action": "Apply for absentee ballot through your county clerk's office",
                "icon": "✉️",
            },
            {
                "step": 5,
                "title": "Know Your Polling Place",
                "description": "Find your assigned polling location. Hours vary but are typically 7 AM – 8 PM local time.",
                "action": "Use vote.gov/polling-place-locator to find your polling place",
                "icon": "📍",
            },
            {
                "step": 6,
                "title": "Bring Required ID",
                "description": "ID requirements vary by state — from no ID required to strict photo ID laws. Know your state's rule.",
                "action": "Check NCSL.org for your state's specific voter ID requirement",
                "icon": "🪪",
            },
            {
                "step": 7,
                "title": "Cast Your Vote",
                "description": "Vote using your state's method — optical scan ballot, touchscreen, or paper ballot. Ask a poll worker if unsure.",
                "action": "If your ballot is rejected or you face issues, ask for a provisional ballot",
                "icon": "🗳️",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    """Serve the main ElectWise application page."""
    return render_template("index.html")


@app.route("/api/health")
def health():
    """Health check endpoint — returns service status."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": {
                "gemini": "connected" if model else "disconnected",
                "custom_search": "connected" if search_service else "unavailable",
            },
            "version": "1.0.0",
        }
    )


@app.route("/api/chat", methods=["POST"])
@limiter.limit("20 per minute")
@require_gemini
def chat():
    """
    AI-powered election Q&A endpoint.

    Request body:
        message  (str): User question (required)
        country  (str): 'India' | 'USA' | 'UK' (optional, default 'India')
        history  (list): Prior chat messages [{role, content}] (optional)

    Returns:
        JSON with AI response text.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload.", "status": "error"}), 400

    user_message: str = sanitize_input(data.get("message", ""))
    country: str = sanitize_input(data.get("country", "India"), max_length=10)
    history: list = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Message cannot be empty.", "status": "error"}), 400

    if country not in Config.SUPPORTED_COUNTRIES:
        country = "India"

    try:
        # Build Gemini-compatible chat history (last 10 messages for context window)
        chat_history: list = []
        for msg in history[-10:]:
            role = msg.get("role", "user")
            content = sanitize_input(msg.get("content", ""))
            if role in ("user", "model") and content:
                chat_history.append({"role": role, "parts": [content]})

        # Inject country context
        contextualized_message = f"[Context: User is asking about {country} elections]\n\n{user_message}"

        # Optionally enrich with live search results
        search_news = None
        news_keywords = ("news", "latest", "recent", "current", "update", "today")
        if any(kw in user_message.lower() for kw in news_keywords):
            search_news = fetch_election_news(user_message, country)

        if search_news:
            news_text = json.dumps(search_news[:3], ensure_ascii=False)
            contextualized_message += (
                f"\n\n[Recent news results for added context: {news_text}]"
            )

        chat_session = model.start_chat(history=chat_history)
        response = chat_session.send_message(contextualized_message)

        return jsonify(
            {
                "status": "success",
                "response": response.text,
                "country": country,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

    except Exception as exc:
        logger.error("Chat endpoint error: %s", exc, exc_info=True)
        return (
            jsonify(
                {
                    "error": "Failed to get AI response. Please try again.",
                    "status": "error",
                }
            ),
            500,
        )


@app.route("/api/timeline", methods=["GET"])
def get_timeline():
    """
    Return structured election timeline data for a given country.

    Query params:
        country (str): 'India' | 'USA' | 'UK' (default 'India')
    """
    country: str = sanitize_input(request.args.get("country", "India"), max_length=10)
    if country not in Config.SUPPORTED_COUNTRIES:
        country = "India"

    return jsonify(
        {
            "status": "success",
            "country": country,
            "timeline": TIMELINES.get(country, TIMELINES["India"]),
        }
    )


@app.route("/api/quiz/generate", methods=["POST"])
@limiter.limit("10 per minute")
@require_gemini
def generate_quiz():
    """
    Generate a civics quiz using Gemini AI.

    Request body:
        country    (str): 'India' | 'USA' | 'UK'
        difficulty (str): 'easy' | 'medium' | 'hard'

    Returns:
        JSON with 5 multiple-choice questions.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload.", "status": "error"}), 400

    country: str = sanitize_input(data.get("country", "India"), max_length=10)
    difficulty: str = sanitize_input(data.get("difficulty", "medium"), max_length=10)

    if country not in Config.SUPPORTED_COUNTRIES:
        country = "India"
    if difficulty not in ("easy", "medium", "hard"):
        difficulty = "medium"

    prompt = f"""Generate a {difficulty}-level civics quiz about the {country} election process.
Return ONLY a valid JSON array of exactly 5 multiple-choice questions.
Each item must have these exact keys:
  "question"    : question text (string)
  "options"     : array of exactly 4 answer strings
  "correct"     : index (0–3) of the correct answer (integer)
  "explanation" : brief explanation of why the answer is correct (string)

Return pure JSON — no markdown, no code fences, no extra text."""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Robustly extract JSON array even if model wraps it in markdown
        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        raw_json = json_match.group() if json_match else response_text
        questions: list = json.loads(raw_json)

        # Validate each question structure
        validated: list = []
        for q in questions[:5]:
            if all(k in q for k in ("question", "options", "correct", "explanation")):
                if (
                    isinstance(q["options"], list)
                    and len(q["options"]) == 4
                    and isinstance(q["correct"], int)
                    and 0 <= q["correct"] <= 3
                ):
                    validated.append(q)

        if not validated:
            raise ValueError("No valid questions in AI response.")

        return jsonify(
            {
                "status": "success",
                "country": country,
                "difficulty": difficulty,
                "questions": validated,
                "total": len(validated),
            }
        )

    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Quiz JSON parse error: %s", exc)
        return (
            jsonify({"error": "Failed to parse quiz. Please try again.", "status": "error"}),
            500,
        )
    except Exception as exc:
        logger.error("Quiz generation error: %s", exc, exc_info=True)
        return (
            jsonify({"error": "Failed to generate quiz. Please try again.", "status": "error"}),
            500,
        )


@app.route("/api/voter-guide", methods=["GET"])
def voter_guide():
    """
    Return voter registration checklist for a given country.

    Query params:
        country (str): 'India' | 'USA' (default 'India')
    """
    country: str = sanitize_input(request.args.get("country", "India"), max_length=10)
    if country not in VOTER_GUIDE:
        country = "India"

    return jsonify(
        {
            "status": "success",
            "country": country,
            "guide": VOTER_GUIDE[country],
        }
    )


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.errorhandler(404)
def not_found(exc):
    """Handle 404 Not Found."""
    return jsonify({"error": "Resource not found.", "status": "error"}), 404


@app.errorhandler(429)
def rate_limit_exceeded(exc):
    """Handle 429 Too Many Requests."""
    return (
        jsonify(
            {"error": "Too many requests — please slow down.", "status": "error"}
        ),
        429,
    )


@app.errorhandler(500)
def server_error(exc):
    """Handle 500 Internal Server Error."""
    logger.error("Unhandled 500 error: %s", exc)
    return jsonify({"error": "Internal server error.", "status": "error"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
