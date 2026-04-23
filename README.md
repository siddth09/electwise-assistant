# 🗳️ ElectWise AI — Election Process Education Assistant

> **Hack2Skill Prompt Wars — Election Process Education Vertical**
> A **smart, dynamic AI assistant** that helps users understand the election process, timelines, and steps in an **interactive and easy-to-follow** way — with hyper-local constituency data, AI-powered civic engagement tools, and a viral Gen Z social layer.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green?logo=flask)](https://flask.palletsprojects.com)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-2.0%20Flash-orange?logo=google)](https://ai.google.dev)
[![Cloud Run](https://img.shields.io/badge/Google%20Cloud%20Run-Deployed-blue?logo=googlecloud)](https://cloud.google.com/run)
[![Tests](https://img.shields.io/badge/Tests-80%20Passed-brightgreen)](#-running-tests)

---

## 🎯 Chosen Vertical

**Election Process Education**

ElectWise AI is built around a clear **persona**: a **first-time Indian voter (age 18–25, Gen Z)** who is overwhelmed by the complexity of the democratic process. The assistant acts as a non-partisan, always-available civic guide that breaks down intimidating legal jargon into digestible, interactive, and shareable experiences — in English and 5 Indian languages.

---

## 📋 Problem Statement

Elections are the cornerstone of democracy, yet millions of eligible voters remain unregistered or uninformed. First-time voters in India face:

- **Confusion** about multi-phase election timelines and ECI procedures
- **Friction** on voting day — not knowing their booth location, expected wait times, or how to use an EVM
- **Disengagement** from the political process due to lack of hyper-local, relatable information
- **Language barriers** preventing access to civic education in regional languages

**ElectWise AI solves this by:**
- Providing an always-available, non-partisan **AI guide** to election education powered by **Google Gemini 2.0 Flash**
- Delivering **hyper-local constituency data** — candidate vibe checks, booth navigation, live crowd wait times, and issue heatmaps
- Creating **viral social hooks** that turn civic duty into a shared cultural moment for Gen Z
- Supporting **6 languages**: English, Hindi, Tamil, Telugu, Bengali, Marathi

---

## 🧠 Persona

**Name:** ElectWise AI
**Archetype:** The Civic Best Friend — warm, non-partisan, witty, and radically accessible

**Behaviour:**
- **Logical decision making based on user context** — detects country (India/USA/UK), constituency, and language preference to tailor every response
- **Non-partisan** — never opines on parties or candidates; surfaces factual records only
- **Structured** — uses timelines, cards, and step-by-step flows for maximum clarity
- **Safe** — blocks misinformation, voter suppression content, and political propaganda

---

## 🤖 Smart, Dynamic Agentic Logic

ElectWise AI demonstrates **ability to build a smart, dynamic assistant** through a multi-layer agentic decision flow:

```
User Input (text / quiz answer / constituency select / excuse text)
     │
     ▼
[Layer 1: Input Guard] → HTML sanitisation, 2000-char limit, country/lang validation
     │
     ▼
[Layer 2: Context Router] → Routes intent to correct agent:
     │   ├─ /api/chat        → Conversational Q&A (Gemini chat session + history)
     │   ├─ /api/quiz        → Adaptive civics quiz (Gemini generates questions)
     │   ├─ /api/roast       → Excuse roaster (Gemini with fact-injection prompt)
     │   ├─ /api/voter-match → Political vibe analyzer (Gemini + issue scoring)
     │   ├─ /api/translate   → Real-time bilingual translation (Gemini)
     │   └─ /api/constituency→ Hyper-local data lookup (structured data + Maps)
     │
     ▼
[Layer 3: Gemini Prompt Engineering] → Dynamic system prompts injected with:
     │   - Country/constituency context
     │   - Conversation history (10-message memory)
     │   - Language code for bilingual output
     │   - Persona guardrails (non-partisan, factual, civic-only)
     │
     ▼
[Layer 4: Response Formatter] → Markdown→HTML, XSS protection, JSON schema validation
     │
     ▼
[Layer 5: UI Renderer] → Accessible, animated output with lazy-loaded tab modules
```

### Key Agentic Behaviours
| Behaviour | Implementation |
|---|---|
| **Context memory** | 10-message Gemini chat history maintained per session |
| **Intent routing** | 6 specialised endpoints — each with tuned system prompts |
| **Graceful fallback** | Gemini `KeyError`/timeout → structured error with user-friendly message |
| **Dynamic content** | Quiz questions generated fresh per country + difficulty via `generate_content` |
| **Self-localisation** | Detects `lang` param → injects language instruction into Gemini prompt |

---

## ⚙️ How the Solution Works

### Phase 1 — Core Election Education

#### 1. AI Chat (`/api/chat`)
- Powered by **Google Gemini 2.0 Flash** via `google-generativeai` SDK
- Maintains **10-message conversation history** for context continuity
- Injects selected country + persona guardrails into every system prompt
- Optionally enriches with live news via **Google Custom Search API**

#### 2. Interactive Election Timeline (`/api/timeline`)
- **India** (8 phases), **USA** (7 phases), **UK** (6 phases) — drag-scrollable cards
- Animated step-by-step breakdown with phase badges, duration chips, and detail modals
- Fully keyboard-navigable — click or press Enter on any step

#### 3. Voter Registration Guide (`/api/voter-guide`)
- Country-specific step-by-step checklist for registration and polling day
- Includes official resource links (ECI India, USA.gov, Electoral Commission UK)

#### 4. AI Civics Quiz (`/api/quiz/generate`)
- Gemini generates 5 fresh MCQs per request — Easy / Medium / Hard
- Instant answer feedback with fact-based explanations
- Score tracking + confetti results screen

### Phase 2 — Hyper-Local Constituency Features

#### 5. Candidate Vibe Check (`/api/constituency`)
- Swipeable visual cards for candidates in 5 Delhi constituencies
- Each card: top 3 policy pillars, voting record, endorsements — under 50 words
- Party-coloured UI without partisan bias

#### 6. Live Polling Booth Navigator
- Booth name, address, metro proximity tip
- **Google Maps** deep-link for one-tap navigation

#### 7. Crowd Wait-Time Reporter (`/api/crowd`)
- Community-powered reporting: users submit wait time + crowded flag
- In-memory crowd aggregator with average wait display and ISO timestamps

#### 8. Hyper-Local Issue Heatmap
- Animated gradient bars showing civic issue intensity per constituency
- Bilingual labels (English + Hindi)

#### 9. Interactive EVM Practice Booth
- Full digital EVM simulation modal with animated VVPAT paper-slip reveal
- Zero-anxiety voting practice before election day

### Phase 2 — Viral Social Growth Hooks

#### 10. Voter Match — Political Vibe (`/api/voter-match`)
- 6 swipe-through Indian policy questions
- Gemini analyses responses → generates personalised "Political Vibe" card
- Spotify-Wrapped aesthetic — designed to be screenshotted and shared

#### 11. Roast My Excuses (`/api/roast`)
- User types their reason for not voting
- Gemini returns witty, fact-based, shareable comeback
- Multi-language support (EN / HI / TA / TE / BN / MR)

#### 12. Youth Registration Leaderboard (`/api/leaderboard`)
- Animated ranked list of Delhi constituencies by youth voter registration
- Real-time bar chart animations — drives social competition

#### 13. Squad Voting Pact
- Create / join friend squads with a shareable code (`localStorage`)
- Track each member's voting journey: Registered → Verified → Voted

#### 14. "I Voted" Digital Badge
- Canvas API generates a personalised, downloadable "I Voted" card
- Drop it on Instagram, WhatsApp, or Snap

---

## 🌐 Effective Use of Google Services

| Google Service | How It's Used | Endpoint/File |
|---|---|---|
| **Google Gemini 2.0 Flash** | AI chat, quiz generation, roast comebacks, political vibe analysis, real-time bilingual translation | `app.py` — all `/api/*` AI endpoints |
| **Google Generative AI SDK** | `google-generativeai` Python library — `GenerativeModel`, `start_chat`, `generate_content` | `requirements.txt`, `app.py` |
| **Google Cloud Run** | Serverless container deployment — auto-scaling, zero cold-start config, health-check probe | `Dockerfile`, `gcloud run deploy` |
| **Google Cloud Build** | `gcloud builds submit` CI pipeline for container image builds | `Dockerfile` |
| **Google Artifact Registry** | Container image storage (`gcr.io/PROJECT/electwise-ai`) | Deployment commands |
| **Google Maps** | Booth navigator deep-link for one-tap directions from polling data | `/api/constituency` response |
| **Google Custom Search API** | Optional live election news enrichment (graceful fallback) | `app.py:chat` |
| **Google Fonts** | `Outfit` + `JetBrains Mono` — premium Gen Z typography | `templates/index.html` |

---

## 🎨 Gen Z UX Design System

ElectWise is designed to make civic duty feel as native as scrolling Instagram:

- **Dark glassmorphic UI** — `rgba` backdrop-filter panels, gradient text, mesh blob backgrounds
- **Swipe-card interactions** — Candidate Vibe Check navigates like a dating app
- **Micro-animations** — bounce, float, shimmer, confetti, bar-fill on scroll
- **Viral-first features** — every output (quiz result, roast, vibe card, badge) is screenshot-ready
- **Gen Z language** — "Vibe Check", "Roast My Excuses", "Squad Pacts", "Drip Badge"
- **Zero friction** — no login, no sign-up, works on mobile, keyboard accessible

---

## 🌏 Bilingual Support (English + 5 Indian Languages)

All UI text supports live switching between:

| Code | Language | Script |
|---|---|---|
| `en` | English | Latin |
| `hi` | Hindi | Devanagari — हिंदी |
| `ta` | Tamil | Tamil — தமிழ் |
| `te` | Telugu | Telugu — తెలుగు |
| `bn` | Bengali | Bengali — বাংলা |
| `mr` | Marathi | Devanagari — मराठी |

**Implementation:** `data-en` / `data-hi` HTML attributes + `/api/translate` Gemini endpoint for dynamic content.

---

## 🛡️ Security Implementation

| Measure | Implementation |
|---|---|
| **API Key Protection** | Environment variables only — never in source code |
| **Input Sanitisation** | `sanitize_input()` — HTML tag stripping, 2000-char max on all inputs |
| **Content Security Policy** | `Flask-Talisman` with strict CSP headers |
| **Rate Limiting** | `Flask-Limiter`: 20 req/min (chat), 10 req/min (quiz), 5 req/min (roast) |
| **Non-root Docker** | Container user `appuser` — no system privileges |
| **XSS Prevention** | `escapeHtml()` on all dynamic DOM insertions |
| **HSTS** | `Strict-Transport-Security` header in production |

---

## ♿ Accessibility (WCAG 2.1 AA)

- `aria-label`, `aria-live="polite"`, `aria-expanded` on all interactive elements
- Semantic HTML5: `<header>`, `<nav>`, `<main>`, `<section>`, `<footer>`, `<aside>`
- Full keyboard navigation (Tab + Enter/Space)
- High-contrast mode toggle (persisted via `localStorage`)
- `@media (prefers-reduced-motion: reduce)` disables all animations
- Skip-navigation link for screen readers

---

## 📁 Repository Structure

```
electwise-assistant/
├── app.py                    # Flask REST API + Gemini 2.0 Flash integration (12 endpoints)
├── config.py                 # Centralised config + AI system prompts
├── requirements.txt          # Python dependencies
├── Dockerfile                # Multi-stage Cloud Run deployment image
├── .env.example              # Environment variable template
├── tests/
│   ├── test_app.py           # 80 unit + integration tests (100% pass rate)
│   └── test_gemini.py        # AI validation + security guardrail tests
├── static/
│   ├── css/style.css         # Glassmorphic Gen Z design system (~1000 lines)
│   ├── js/app.js             # Core navigation, chat, quiz, voter guide
│   ├── js/features.js        # Phase 2: local + viral feature handlers
│   └── js/timeline.js        # Interactive drag-scroll election timeline
└── templates/
    └── index.html            # Semantic HTML5 with ARIA + bilingual data attributes
```

---

## 🚀 Setup & Running Locally

### Prerequisites
- Python 3.12+
- Google Gemini API key — [get one free at Google AI Studio](https://aistudio.google.com/app/apikey)

```bash
# 1. Clone this repository
git clone https://github.com/siddth09/electwise-assistant.git
cd electwise-assistant

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env → add your GEMINI_API_KEY

# 5. Run development server
FLASK_ENV=development python app.py
```

Visit **[http://localhost:8080](http://localhost:8080)**

---

## 🐳 Google Cloud Run Deployment

```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and push container image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/electwise-ai

# Deploy to Cloud Run (fully managed, auto-scaling)
gcloud run deploy electwise-ai \
  --image gcr.io/YOUR_PROJECT_ID/electwise-ai \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --set-env-vars "GEMINI_API_KEY=your_key_here"
```

---

## 🧪 Running Tests

```bash
# Full suite — 80 tests, all pass
pytest tests/ -v --cov=app --cov-report=term-missing

# Phase 1 tests only (core endpoints)
pytest tests/test_app.py::TestChatEndpoint -v

# Phase 2 tests only (new features)
pytest tests/test_app.py::TestConstituencyEndpoint \
       tests/test_app.py::TestCrowdEndpoint \
       tests/test_app.py::TestRoastEndpoint \
       tests/test_app.py::TestVoterMatchEndpoint \
       tests/test_app.py::TestLeaderboardEndpoint \
       tests/test_app.py::TestTranslateEndpoint -v
```

**Results:** `80 passed, 0 failed` in `0.77s` — fully mocked, no real API calls.

---

## 📊 Assumptions Made

1. **Primary persona**: First-time Indian voter, age 18–25, urban, smartphone-first
2. **Country focus**: India (primary) with USA and UK support
3. **Constituency data**: 5 Delhi parliamentary constituencies with realistic candidate, booth, and issue data
4. **Google Custom Search**: Optional enhancement — app works fully without it via Gemini's knowledge
5. **Crowd data**: In-memory store (production would use Firestore / Redis for persistence)
6. **Bilingual**: Gemini handles dynamic translation; static UI uses `data-en`/`data-hi` attributes

---

## 🔮 Future Enhancements

- [ ] Firestore / Redis persistence for crowd reports and squad pacts
- [ ] Real-time ECI election schedule integration
- [ ] WhatsApp Bot for rural reach (Twilio + Gemini)
- [ ] PWA with offline first-time voter guide
- [ ] All 543 Lok Sabha constituencies with live data

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ using **Google Gemini 2.0 Flash**, **Google Cloud Run**, Flask, and a deep belief in informed democratic participation.*
# electwise-edu
