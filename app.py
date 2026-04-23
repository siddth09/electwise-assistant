"""
ElectWise AI — Election Process Education Assistant
Flask backend with Google Gemini 2.0 Flash + Google Cloud integration.

Google Services Used:
  - Google Gemini 2.0 Flash     (google-generativeai) — AI chat, quiz, roast, vibe, translate
  - Google Cloud Logging        (google-cloud-logging) — Structured request/event logs on Cloud Run
  - Google Cloud Firestore      (google-cloud-firestore) — Persistent crowd wait-time reports
  - Google Custom Search API    (google-api-python-client) — Live election news enrichment
  - Google Cloud Run            — Serverless container deployment
  - Google Maps                 — Booth navigation deep-links

Endpoints:
  GET  /                    — Serve main application UI
  GET  /api/health          — Health check
  POST /api/chat            — AI-powered election Q&A (Gemini)
  GET  /api/timeline        — Structured election timeline data
  POST /api/quiz/generate   — AI-generated civics quiz (Gemini)
  GET  /api/voter-guide     — Voter registration checklist
  GET  /api/constituency    — Hyper-local candidate + booth + issue data
  GET|POST /api/crowd       — Community crowd wait-time reporter (Firestore)
  POST /api/roast           — AI excuse roaster (Gemini)
  POST /api/voter-match     — Political vibe analyser (Gemini)
  GET  /api/leaderboard     — Youth registration leaderboard
  POST /api/translate       — Real-time bilingual translation (Gemini)
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
from flask_cors import CORS
from flask_compress import Compress
from dotenv import load_dotenv

# ── Google Cloud Logging ─────────────────────────────────────────────────────
try:
    import google.cloud.logging as cloud_logging
    from google.cloud.logging.handlers import CloudLoggingHandler
    _cloud_log_client = cloud_logging.Client()
    _cloud_handler = CloudLoggingHandler(_cloud_log_client, name="electwise-ai")
    _GCP_LOGGING = True
except Exception:  # noqa: BLE001 — graceful fallback outside Cloud Run
    _GCP_LOGGING = False

# ── Google Cloud Firestore ───────────────────────────────────────────────────
try:
    from google.cloud import firestore as _firestore
    _db = _firestore.Client()
    _FIRESTORE_OK = True
except Exception:  # noqa: BLE001 — graceful fallback to in-memory store
    _db = None
    _FIRESTORE_OK = False

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

# Attach Cloud Logging handler when running on Cloud Run
if _GCP_LOGGING:
    logger.addHandler(_cloud_handler)
    logger.info("Google Cloud Logging initialised — logs streaming to Cloud Logging.")

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for security and cross-origin resource sharing
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Enable Gzip/Brotli compression for efficiency
Compress(app)

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
# India Constituency Data (Hyper-Local Features)
# ---------------------------------------------------------------------------

CONSTITUENCIES: dict = {
    "Chandni Chowk, Delhi": {
        "candidates": [
            {
                "name": "Praveen Khandelwal", "party": "BJP", "symbol": "🪷",
                "pillars": ["Traders' Rights", "Infrastructure", "Digital Markets"],
                "vibe": "Stability & Commerce", "record": "National Sec. Gen., CAIT",
                "endorsements": "PM Modi", "color": "#FF6B35",
            },
            {
                "name": "JP Agarwal", "party": "INC", "symbol": "✋",
                "pillars": ["Small Business Support", "Affordable Healthcare", "Education"],
                "vibe": "Inclusive Growth", "record": "Former Delhi MLA & MP",
                "endorsements": "Rahul Gandhi", "color": "#138808",
            },
            {
                "name": "Raghav Chadha (Supp.)", "party": "AAP", "symbol": "🧹",
                "pillars": ["Free Utilities", "Mohalla Clinics", "School Quality"],
                "vibe": "Aam Aadmi First", "record": "Rajya Sabha MP, Ex-AAP Delhi",
                "endorsements": "Arvind Kejriwal", "color": "#00BFFF",
            },
        ],
        "booth": {
            "name": "Govt. Boys Sr. Sec. School, Chandni Chowk",
            "address": "Near Fatehpuri Mosque, Chandni Chowk, Delhi 110006",
            "maps_url": "https://maps.google.com/?q=Govt+Boys+School+Chandni+Chowk+Delhi",
            "tip": "Nearest Metro: Chandni Chowk (Yellow Line) — 5 min walk",
        },
        "issues": [
            {"issue": "Air Pollution", "issue_hi": "वायु प्रदूषण", "intensity": 94, "icon": "🌫️"},
            {"issue": "Trader Regulation", "issue_hi": "व्यापार नियमन", "intensity": 82, "icon": "🏪"},
            {"issue": "Traffic & Parking", "issue_hi": "यातायात व पार्किंग", "intensity": 76, "icon": "🚗"},
        ],
    },
    "New Delhi, Delhi": {
        "candidates": [
            {
                "name": "Bansuri Swaraj", "party": "BJP", "symbol": "🪷",
                "pillars": ["Women's Safety", "Diplomatic Quarter Dev.", "Heritage"],
                "vibe": "Progressive Conservatism", "record": "Daughter of late Sushma Swaraj",
                "endorsements": "PM Modi", "color": "#FF6B35",
            },
            {
                "name": "Somnath Bharti", "party": "AAP", "symbol": "🧹",
                "pillars": ["Legal Aid", "Anti-Corruption", "Drainage Infra"],
                "vibe": "Accountability First", "record": "Former MLA, Malviya Nagar",
                "endorsements": "Arvind Kejriwal", "color": "#00BFFF",
            },
            {
                "name": "Ajay Maken", "party": "INC", "symbol": "✋",
                "pillars": ["Affordable Housing", "Employment", "Urban Development"],
                "vibe": "People's Welfare", "record": "2-term MP, Former Union Minister",
                "endorsements": "Rahul Gandhi", "color": "#138808",
            },
        ],
        "booth": {
            "name": "Modern School, Barakhamba Road",
            "address": "Barakhamba Road, New Delhi 110001",
            "maps_url": "https://maps.google.com/?q=Modern+School+Barakhamba+Road+New+Delhi",
            "tip": "Nearest Metro: Barakhamba Road (Blue Line) — 2 min walk",
        },
        "issues": [
            {"issue": "Water Supply", "issue_hi": "जल आपूर्ति", "intensity": 88, "icon": "💧"},
            {"issue": "Air Quality", "issue_hi": "वायु गुणवत्ता", "intensity": 91, "icon": "🌫️"},
            {"issue": "Heritage Preservation", "issue_hi": "विरासत संरक्षण", "intensity": 65, "icon": "🏛️"},
        ],
    },
    "South Delhi, Delhi": {
        "candidates": [
            {
                "name": "Ramvir Singh Bidhuri", "party": "BJP", "symbol": "🪷",
                "pillars": ["Urban Infra", "Security", "Road Development"],
                "vibe": "Development & Order", "record": "Delhi Assembly Speaker",
                "endorsements": "PM Modi", "color": "#FF6B35",
            },
            {
                "name": "Sahibraam Chauhan", "party": "INC", "symbol": "✋",
                "pillars": ["Employment", "Healthcare Access", "Youth Programs"],
                "vibe": "Grassroots Welfare", "record": "Local Congress leader",
                "endorsements": "Mallikarjun Kharge", "color": "#138808",
            },
            {
                "name": "Raaj Kumar Anand", "party": "BSP", "symbol": "🐘",
                "pillars": ["Dalit Rights", "Equal Access", "Anti-Discrimination"],
                "vibe": "Social Justice", "record": "Former AAP Minister",
                "endorsements": "Mayawati", "color": "#0000FF",
            },
        ],
        "booth": {
            "name": "DPS R.K. Puram Community Centre",
            "address": "Sector 12, R.K. Puram, South Delhi 110022",
            "maps_url": "https://maps.google.com/?q=RK+Puram+Community+Centre+New+Delhi",
            "tip": "Nearest Metro: Munirka (Yellow Line) — 10 min walk",
        },
        "issues": [
            {"issue": "Yamuna Pollution", "issue_hi": "यमुना प्रदूषण", "intensity": 89, "icon": "🌊"},
            {"issue": "Unauthorised Colonies", "issue_hi": "अनधिकृत कॉलोनी", "intensity": 79, "icon": "🏘️"},
            {"issue": "Power Outages", "issue_hi": "बिजली कटौती", "intensity": 71, "icon": "⚡"},
        ],
    },
    "East Delhi, Delhi": {
        "candidates": [
            {
                "name": "Harsh Malhotra", "party": "BJP", "symbol": "🪷",
                "pillars": ["Industrial Dev.", "Flood Control", "Smart Roads"],
                "vibe": "Rapid Development", "record": "BJP Delhi Unit Treasurer",
                "endorsements": "PM Modi", "color": "#FF6B35",
            },
            {
                "name": "Kuldeep Kumar", "party": "AAP", "symbol": "🧹",
                "pillars": ["Flood Relief", "Clean Yamuna", "Urban Planning"],
                "vibe": "Aam Aadmi Values", "record": "AAP East Delhi leader",
                "endorsements": "Atishi", "color": "#00BFFF",
            },
            {
                "name": "Aradhana Mishra", "party": "INC", "symbol": "✋",
                "pillars": ["Women Safety", "Employment", "Education Reform"],
                "vibe": "Inclusive Progress", "record": "INC Spokesperson",
                "endorsements": "Priyanka Gandhi", "color": "#138808",
            },
        ],
        "booth": {
            "name": "Laxmi Nagar Govt. School",
            "address": "Laxmi Nagar, East Delhi 110092",
            "maps_url": "https://maps.google.com/?q=Laxmi+Nagar+East+Delhi",
            "tip": "Nearest Metro: Laxmi Nagar (Blue Line) — 3 min walk",
        },
        "issues": [
            {"issue": "Flooding & Drainage", "issue_hi": "बाढ़ और ड्रेनेज", "intensity": 93, "icon": "🌊"},
            {"issue": "Industrial Pollution", "issue_hi": "औद्योगिक प्रदूषण", "intensity": 80, "icon": "🏭"},
            {"issue": "Overcrowding", "issue_hi": "भीड़भाड़", "intensity": 74, "icon": "👥"},
        ],
    },
    "North West Delhi, Delhi": {
        "candidates": [
            {
                "name": "Yogendra Chandolia", "party": "BJP", "symbol": "🪷",
                "pillars": ["Transport Links", "Health Infrastructure", "Cleanliness"],
                "vibe": "Modern Governance", "record": "BJP District President",
                "endorsements": "PM Modi", "color": "#FF6B35",
            },
            {
                "name": "Udit Raj", "party": "INC", "symbol": "✋",
                "pillars": ["SC/ST Rights", "Reservations", "Education Access"],
                "vibe": "Social Equity", "record": "Former BJP MP turned INC",
                "endorsements": "Rahul Gandhi", "color": "#138808",
            },
            {
                "name": "Gurdeep Singh", "party": "AAP", "symbol": "🧹",
                "pillars": ["Free Bus Passes", "Mohalla Schools", "Healthcare"],
                "vibe": "Free Services", "record": "AAP North Delhi leader",
                "endorsements": "Sanjay Singh", "color": "#00BFFF",
            },
        ],
        "booth": {
            "name": "Rohini Sec-7 Community Hall",
            "address": "Sector 7, Rohini, North West Delhi 110085",
            "maps_url": "https://maps.google.com/?q=Rohini+Sector+7+Delhi",
            "tip": "Nearest Metro: Rohini West (Red Line) — 7 min walk",
        },
        "issues": [
            {"issue": "Waste Management", "issue_hi": "कचरा प्रबंधन", "intensity": 85, "icon": "♻️"},
            {"issue": "Water Quality", "issue_hi": "जल गुणवत्ता", "intensity": 82, "icon": "💧"},
            {"issue": "School Infrastructure", "issue_hi": "स्कूल अवसंरचना", "intensity": 68, "icon": "🏫"},
        ],
    },
}

# Leaderboard: Youth registration data (mock, India-only)
LEADERBOARD: list = [
    {"rank": 1, "name": "Chandni Chowk, Delhi", "name_hi": "चांदनी चौक, दिल्ली", "youth_reg": 31420, "change": "+18%", "emoji": "🥇"},
    {"rank": 2, "name": "Lajpat Nagar, Delhi", "name_hi": "लाजपत नगर, दिल्ली", "youth_reg": 28950, "change": "+14%", "emoji": "🥈"},
    {"rank": 3, "name": "Rohini Sector 7, Delhi", "name_hi": "रोहिणी सेक्टर 7, दिल्ली", "youth_reg": 26700, "change": "+11%", "emoji": "🥉"},
    {"rank": 4, "name": "Laxmi Nagar, Delhi", "name_hi": "लक्ष्मी नगर, दिल्ली", "youth_reg": 24100, "change": "+9%", "emoji": "4️⃣"},
    {"rank": 5, "name": "R.K. Puram, Delhi", "name_hi": "आर.के. पुरम, दिल्ली", "youth_reg": 21800, "change": "+7%", "emoji": "5️⃣"},
    {"rank": 6, "name": "Dwarka Sector 12, Delhi", "name_hi": "द्वारका सेक्टर 12, दिल्ली", "youth_reg": 19500, "change": "+5%", "emoji": "6️⃣"},
    {"rank": 7, "name": "Shahdara, Delhi", "name_hi": "शाहदरा, दिल्ली", "youth_reg": 17300, "change": "+3%", "emoji": "7️⃣"},
]

# Voter Match issue statements (India-specific)
VOTER_MATCH_ISSUES: list = [
    {"id": 1, "statement": "The government should provide free electricity up to 300 units per month to every household.", "issue": "Energy Subsidy"},
    {"id": 2, "statement": "Building new highways and metro lines should take priority over funding public schools.", "issue": "Infrastructure vs Education"},
    {"id": 3, "statement": "Reservations in government jobs should be extended to economically weaker sections regardless of caste.", "issue": "Reservations"},
    {"id": 4, "statement": "India should fast-track nuclear energy to meet its climate targets by 2050.", "issue": "Energy & Climate"},
    {"id": 5, "statement": "Farmers should receive a guaranteed minimum income (PM-KISAN expanded) regardless of crop yield.", "issue": "Agriculture"},
    {"id": 6, "statement": "Tech companies should be taxed more heavily to fund rural development and healthcare.", "issue": "Tech Taxation"},
]

# In-memory stores (reset on server restart — production would use Redis/Firestore)
crowd_reports: dict = {}   # {constituency: [{wait_min, crowded, ts}]}

# ---------------------------------------------------------------------------
# New Phase 2 Routes
# ---------------------------------------------------------------------------


@app.route("/api/constituency", methods=["GET"])
def get_constituency():
    """
    Return hyper-local constituency data: candidates, booth, issues.

    Query params:
        name (str): Constituency name (default 'Chandni Chowk, Delhi')
    """
    name: str = sanitize_input(request.args.get("name", "Chandni Chowk, Delhi"), max_length=60)
    data = CONSTITUENCIES.get(name) or CONSTITUENCIES["Chandni Chowk, Delhi"]
    return jsonify({"status": "success", "constituency": name, "data": data})


@app.route("/api/crowd", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def crowd():
    """
    Community crowd/wait-time reports for polling booths.
    Persisted in Google Cloud Firestore when available; falls back to in-memory.

    GET  ?constituency=<name>  — fetch latest reports (last 5)
    POST {constituency, wait_min, crowded}  — submit a report
    """
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        constituency = sanitize_input(body.get("constituency", ""), max_length=60)
        wait_min = int(body.get("wait_min", 0))
        crowded = bool(body.get("crowded", False))

        if not constituency:
            return jsonify({"error": "constituency required", "status": "error"}), 400
        if wait_min < 0 or wait_min > 180:
            return jsonify({"error": "wait_min must be 0–180", "status": "error"}), 400

        report = {
            "wait_min": wait_min,
            "crowded": crowded,
            "ts": datetime.utcnow().isoformat() + "Z",
            "label": "Very crowded 😤" if crowded else ("Moderate 🙂" if wait_min > 15 else "Short wait ✅"),
            "constituency": constituency,
        }

        # ── Persist to Google Cloud Firestore ──────────────────────────────
        if _FIRESTORE_OK and _db:
            try:
                _db.collection("crowd_reports").add(report)
                logger.info("Crowd report written to Firestore for: %s", constituency)
            except Exception as fstore_err:  # noqa: BLE001
                logger.warning("Firestore write failed — falling back to memory: %s", fstore_err)
                crowd_reports.setdefault(constituency, []).append(report)
                crowd_reports[constituency] = crowd_reports[constituency][-20:]
        else:
            # In-memory fallback for local dev
            crowd_reports.setdefault(constituency, []).append(report)
            crowd_reports[constituency] = crowd_reports[constituency][-20:]

        return jsonify({"status": "success", "report": report})

    # GET — fetch latest reports
    constituency = sanitize_input(request.args.get("constituency", ""), max_length=60)

    # ── Read from Google Cloud Firestore ────────────────────────────────────
    if _FIRESTORE_OK and _db:
        try:
            docs = (
                _db.collection("crowd_reports")
                .where("constituency", "==", constituency)
                .order_by("ts", direction="DESCENDING")
                .limit(5)
                .stream()
            )
            reports = [doc.to_dict() for doc in docs]
            logger.info("Crowd reports fetched from Firestore for: %s", constituency)
        except Exception as fstore_err:  # noqa: BLE001
            logger.warning("Firestore read failed — using memory fallback: %s", fstore_err)
            reports = crowd_reports.get(constituency, [])[-5:]
    else:
        reports = crowd_reports.get(constituency, [])[-5:]

    avg_wait = round(sum(r["wait_min"] for r in reports) / len(reports)) if reports else None
    return jsonify({"status": "success", "reports": reports, "avg_wait_min": avg_wait})


@app.route("/api/roast", methods=["POST"])
@limiter.limit("5 per minute")
@require_gemini
def roast_excuse():
    """
    Gemini-powered "Roast My Excuse" feature.
    Generates a witty, fact-based, shareable comeback to a voting excuse.

    Request body:
        excuse (str): The excuse for not voting (required)
        lang   (str): Language code 'en'|'hi'|'ta'|'te'|'bn'|'mr' (default 'en')
    """
    body = request.get_json(silent=True) or {}
    excuse = sanitize_input(body.get("excuse", ""), max_length=300)
    lang = sanitize_input(body.get("lang", "en"), max_length=5)

    if not excuse:
        return jsonify({"error": "excuse cannot be empty", "status": "error"}), 400

    lang_map = {"hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali", "mr": "Marathi", "en": "English"}
    language = lang_map.get(lang, "English")

    prompt = f"""A young Indian voter gave this excuse for NOT voting: "{excuse}"

Write a witty, fact-based, and encouraging comeback in {language} that:
1. Gently roasts the excuse with humour
2. Includes ONE surprising election fact from India (ECI data, voter turnout stats, etc.)
3. Ends with a motivating one-liner to inspire them to vote
4. Is under 80 words total
5. Is fun and screenshot-worthy — like something you'd share in a WhatsApp group

Return ONLY the roast text. No introduction, no explanations."""

    try:
        resp = model.generate_content(prompt)
        return jsonify({"status": "success", "roast": resp.text.strip(), "lang": lang})
    except Exception as exc:
        logger.error("Roast endpoint error: %s", exc)
        return jsonify({"error": "Failed to generate roast. Try again!", "status": "error"}), 500


@app.route("/api/voter-match", methods=["POST"])
@limiter.limit("10 per minute")
@require_gemini
def voter_match():
    """
    Generate Spotify-Wrapped-style "Political Vibe" from user's issue answers.

    Request body:
        answers (list): [{issue_id, agree: bool}] — 6 answers
        lang    (str): Language code (default 'en')
    """
    body = request.get_json(silent=True) or {}
    answers = body.get("answers", [])
    lang = sanitize_input(body.get("lang", "en"), max_length=5)

    if not answers or len(answers) < 3:
        return jsonify({"error": "At least 3 answers required", "status": "error"}), 400

    lang_map = {"hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali", "mr": "Marathi", "en": "English"}
    language = lang_map.get(lang, "English")

    # Map answers to issue names
    issue_map = {i["id"]: i["issue"] for i in VOTER_MATCH_ISSUES}
    answered = []
    for a in answers[:6]:
        iid = a.get("issue_id")
        agree = a.get("agree", False)
        if iid in issue_map:
            answered.append(f"{'Agrees' if agree else 'Disagrees'} with: {issue_map[iid]}")

    answers_text = "\n".join(answered)
    prompt = f"""Based on these Indian voter preferences:
{answers_text}

Generate a Spotify-Wrapped style "Political Vibe" card in {language} with:
1. A catchy 3-word "vibe label" (e.g., "Tech-Progressive Pragmatist", "Rural-First Traditionalist")
2. A percentage match score for 2 contrasting Indian political philosophies
3. Your #1 issue prediction for this voter
4. A fun emoji-rich one-liner about their civic identity

Return as JSON with keys: vibe_label, match_a ({{party_style, pct}}), match_b ({{party_style, pct}}), top_issue, tagline
Return ONLY valid JSON, no markdown fences."""

    try:
        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(json_match.group() if json_match else raw)
        return jsonify({"status": "success", "result": result, "lang": lang})
    except Exception as exc:
        logger.error("VoterMatch error: %s", exc)
        return jsonify({"error": "Could not generate vibe. Try again!", "status": "error"}), 500


@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    """Return constituency youth-registration leaderboard (India-only)."""
    return jsonify({"status": "success", "leaderboard": LEADERBOARD, "total_constituencies": len(LEADERBOARD)})


@app.route("/api/translate", methods=["POST"])
@limiter.limit("15 per minute")
@require_gemini
def translate():
    """
    Translate UI text or AI response to an Indian language using Gemini.

    Request body:
        text (str): Text to translate (required, max 500 chars)
        lang (str): Target language code 'hi'|'ta'|'te'|'bn'|'mr'
    """
    body = request.get_json(silent=True) or {}
    text = sanitize_input(body.get("text", ""), max_length=500)
    lang = sanitize_input(body.get("lang", "hi"), max_length=5)

    if not text:
        return jsonify({"error": "text cannot be empty", "status": "error"}), 400

    lang_map = {"hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali", "mr": "Marathi"}
    language = lang_map.get(lang, "Hindi")

    prompt = f"""Translate the following election/civic text to {language}.
Maintain the same tone (friendly + informative). Preserve any emojis.
Return ONLY the translated text — no notes or explanations.

Text: {text}"""

    try:
        resp = model.generate_content(prompt)
        return jsonify({"status": "success", "translated": resp.text.strip(), "lang": lang, "language": language})
    except Exception as exc:
        logger.error("Translate error: %s", exc)
        return jsonify({"error": "Translation failed. Please try again.", "status": "error"}), 500


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
