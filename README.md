# 🗳️ ElectWise AI — Election Process Education Assistant

> **Hack2Skill Prompt Wars — Election Process Education Vertical**  
> An AI-powered civic education guide that helps citizens understand elections, voter rights, and the democratic process — step by step, interactively, and accessibly.

---

## 🎯 Chosen Vertical

**Election Process Education**

ElectWise AI is designed around the persona of a **first-time voter or curious citizen** who needs clear, trustworthy, and engaging guidance through complex election procedures. The assistant breaks down intimidating legal and procedural jargon into digestible, interactive steps.

---

## 📋 Problem Statement

Elections are the cornerstone of democracy, yet millions of eligible voters remain unregistered or uninformed about how the process actually works. Confusion about registration deadlines, polling procedures, voting machines, and result timelines creates barriers to civic participation.

**ElectWise AI solves this by:**
- Providing an always-available, non-partisan AI guide to election education
- Visualising multi-phase election processes as interactive timelines
- Generating personalised civics quizzes to reinforce learning
- Offering step-by-step voter registration checklists
- Supporting **India, USA, and UK** election systems

---

## 🧠 Approach & Logic

### Persona

**ElectWise** is a warm, patient, and knowledgeable civic education guide. It is:
- **Non-partisan** — never opines on political parties or candidates
- **Contextual** — tailors responses based on selected country
- **Structured** — uses bullet points and numbered steps for clarity
- **Safe** — blocks misinformation and voter suppression content

### Agentic Decision Flow

```
User Input
    │
    ▼
[Input Sanitisation] → Strip HTML, limit length, validate country
    │
    ▼
[Context Injection] → Add country context + recent search results (if available)
    │
    ▼
[Gemini 2.0 Flash] → System prompt enforces civic education persona
    │
    ▼
[Response Formatting] → Markdown-to-HTML conversion, XSS protection
    │
    ▼
[UI Render] → Accessible, animated chat bubble with keyboard navigation
```

### Architecture

```
electwise-assistant/
├── app.py                    # Flask REST API + Gemini integration
├── config.py                 # Centralised config + AI system prompt
├── requirements.txt          # Python dependencies
├── Dockerfile                # Multi-stage Cloud Run deployment
├── .env.example              # Environment template
├── .gitignore                
├── tests/
│   ├── conftest.py           # Shared pytest setup
│   ├── test_app.py           # Endpoint unit + integration tests
│   └── test_gemini.py        # AI validation + security tests
├── static/
│   ├── css/style.css         # Glassmorphic dark design system
│   ├── js/app.js             # Chat, quiz, voter guide, navigation
│   └── js/timeline.js        # Interactive election timeline
└── templates/
    └── index.html            # Semantic HTML5 with ARIA
```

---

## ⚙️ How the Solution Works

### 1. AI Chat (`/api/chat`)
- Powered by **Google Gemini 2.0 Flash** via the `google-generativeai` Python SDK
- Maintains a 10-message conversation history for context
- Injects the selected country into every prompt for accurate, localised responses
- Optionally enriches responses with live election news via **Google Custom Search API** (graceful fallback when not configured)

### 2. Interactive Election Timeline (`/api/timeline`)
- Structured data for **India** (8 phases), **USA** (7 phases), and **UK** (6 phases)
- Animated step cards with phase badges, duration, and detailed modals
- Fully keyboard-navigable — click or press Enter on any step

### 3. Voter Registration Guide (`/api/voter-guide`)
- Country-specific step-by-step checklist for registration and voting
- Includes official resource links (ECI, USA.gov, Electoral Commission UK)

### 4. AI Civics Quiz (`/api/quiz/generate`)
- Gemini generates 5 multiple-choice questions in real-time
- Three difficulty levels: Easy, Medium, Hard
- Instant feedback with explanations after each answer
- Score tracking and performance summary

---

## 🛡️ Security Implementation

| Measure | Implementation |
|---|---|
| **API Key Protection** | Environment variables only — never in source code |
| **Input Sanitisation** | HTML tag stripping, 2000-char limit on all inputs |
| **Content Security Policy** | Flask-Talisman with strict CSP headers |
| **Rate Limiting** | Flask-Limiter: 20 req/min (chat), 10 req/min (quiz) |
| **Non-root Docker** | Container user `appuser` with no system privileges |
| **XSS Prevention** | `escapeHtml()` applied to all dynamic DOM insertions |
| **HSTS** | Strict-Transport-Security header in production |

---

## ♿ Accessibility Features

- **WCAG 2.1 AA** compliant colour contrast ratios
- **Skip navigation** link for keyboard users
- **ARIA labels** on all interactive elements (`aria-label`, `aria-live`, `aria-expanded`)
- **Semantic HTML5**: `<header>`, `<nav>`, `<main>`, `<section>`, `<footer>`, `<aside>`
- **Keyboard navigation**: all interactive elements reachable via Tab + Enter/Space
- **Screen reader announcements**: `aria-live="polite"` on chat and quiz regions
- **High-contrast mode toggle** (persisted via `localStorage`)
- **Reduced motion support**: `@media (prefers-reduced-motion: reduce)` disables animations
- **Unique IDs** on all interactive elements

---

## 🌐 Google Services Integration

| Service | Usage |
|---|---|
| **Google Gemini 2.0 Flash** | Primary AI engine for chat, quiz generation — via `google-generativeai` SDK |
| **Google Custom Search API** | Optional live election news enrichment — graceful fallback when not configured |
| **Google Cloud Run** | Serverless deployment target (Dockerfile provided) |
| **Google Fonts** | Inter + Space Grotesk for premium typography |

---

## 🚀 Setup & Running Locally

### Prerequisites
- Python 3.12+
- A Google Gemini API key ([get one free at Google AI Studio](https://aistudio.google.com/app/apikey))

### Steps

```bash
# 1. Clone this repository
git clone <your-repo-url>
cd electwise-assistant

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Run the development server
FLASK_ENV=development python app.py
```

Visit [http://localhost:8080](http://localhost:8080)

---

## 🐳 Google Cloud Run Deployment

```bash
# Build and push to Google Artifact Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/electwise-ai

# Deploy to Cloud Run
gcloud run deploy electwise-ai \
  --image gcr.io/YOUR_PROJECT_ID/electwise-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=your_key_here"
```

---

## 🧪 Running Tests

```bash
# Install test dependencies (included in requirements.txt)
pip install pytest pytest-cov

# Run the full test suite with coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_app.py -v
pytest tests/test_gemini.py -v
```

**Coverage targets:**
- Overall: > 90%
- All API endpoints: 100%
- Security utilities: 100%

---

## 📊 Assumptions Made

1. **Primary audience**: First-time voters and civic education learners (ages 18–35)
2. **Country focus**: India (primary) with USA and UK support — selected for the likely user base of this hackathon
3. **Google Custom Search**: Built as an optional enhancement — the app works fully without it using Gemini's built-in knowledge
4. **Election data**: Timeline and voter guide data is structured and hardcoded for reliability and speed; Gemini handles dynamic Q&A
5. **Language**: English only in this version; i18n can be added as a future enhancement
6. **Offline usage**: Not supported — requires internet connection for Gemini API

---

## 🔮 Future Enhancements

- [ ] Indian languages support (Hindi, Tamil, Bengali) via Gemini translation
- [ ] Real-time election schedule integration with ECI API
- [ ] SMS/WhatsApp bot interface for rural voter reach
- [ ] Accessibility audit with axe-core automated testing
- [ ] Live election results dashboard

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ using Google Gemini 2.0 Flash, Flask, and a deep belief in informed democratic participation.*
