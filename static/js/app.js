/**
 * ElectWise AI — Main Application Script
 * Handles navigation, chat, voter guide, and quiz functionality.
 */

"use strict";

/* ── App State ─────────────────────────────────────────────────────── */
const state = {
  country: "India",
  chatHistory: [],      // [{role, content}]
  quizQuestions: [],
  currentQuestion: 0,
  score: 0,
  quizDifficulty: "medium",
  timelineLoaded: false,
  guideLoaded: false,
};

/* ── DOM Cache ─────────────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);

/* ── Initialisation ────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initCountrySelector();
  initChat();
  initQuiz();
  initContrastToggle();
});

/* ── Navigation ─────────────────────────────────────────────────────── */
function initNavigation() {
  const navBtns = document.querySelectorAll(".nav-btn");

  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const section = btn.dataset.section;
      switchSection(section);
    });
  });
}

/**
 * Switch the active section and lazy-load data as needed.
 * @param {string} sectionName - 'chat' | 'timeline' | 'guide' | 'quiz'
 */
function switchSection(sectionName) {
  // Update nav buttons
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    const active = btn.dataset.section === sectionName;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-current", active ? "page" : "false");
  });

  // Show/hide sections
  document.querySelectorAll(".section").forEach((sec) => {
    const show = sec.id === `section-${sectionName}`;
    sec.classList.toggle("active", show);
    sec.classList.toggle("hidden", !show);
    if (show) sec.hidden = false;
  });

  // Lazy-load content
  if (sectionName === "timeline" && !state.timelineLoaded) {
    loadTimeline(state.country);
    state.timelineLoaded = true;
  }
  if (sectionName === "guide" && !state.guideLoaded) {
    loadVoterGuide(state.country);
    state.guideLoaded = true;
  }

  // Announce section change to screen readers
  const sectionEl = $(`section-${sectionName}`);
  if (sectionEl) {
    sectionEl.focus?.();
  }
}

/* ── Country Selector ───────────────────────────────────────────────── */
function initCountrySelector() {
  const select = $("country-select");
  if (!select) return;

  select.addEventListener("change", () => {
    state.country = select.value;
    // Reset lazy-load flags so content refreshes
    state.timelineLoaded = false;
    state.guideLoaded = false;

    // Reload current section if it's timeline or guide
    const activeSection = document.querySelector(".nav-btn.active")?.dataset.section;
    if (activeSection === "timeline") {
      loadTimeline(state.country);
      state.timelineLoaded = true;
    }
    if (activeSection === "guide") {
      loadVoterGuide(state.country);
      state.guideLoaded = true;
    }
  });
}

/* ── Chat ───────────────────────────────────────────────────────────── */
function initChat() {
  const form = $("chat-form");
  const input = $("chat-input");
  const sendBtn = $("send-btn");

  if (!form || !input) return;

  // Auto-resize textarea
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  });

  // Handle Enter to send, Shift+Enter for newline
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitChat();
    }
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    submitChat();
  });

  // Quick prompt chips
  document.querySelectorAll(".prompt-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.dataset.prompt;
      if (prompt && input) {
        input.value = prompt;
        input.dispatchEvent(new Event("input")); // trigger resize
        submitChat();
      }
    });
  });
}

/** Submit the chat message to the API. */
async function submitChat() {
  const input = $("chat-input");
  const sendBtn = $("send-btn");
  const message = input?.value.trim();

  if (!message || sendBtn?.disabled) return;

  // Clear input
  input.value = "";
  input.style.height = "auto";

  // Append user message
  appendMessage("user", message);

  // Update local history
  state.chatHistory.push({ role: "user", content: message });

  // Show typing indicator
  setTyping(true);

  // Disable send button
  if (sendBtn) sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        country: state.country,
        history: state.chatHistory.slice(-10),  // Keep context window light
      }),
    });

    const data = await res.json();

    setTyping(false);

    if (res.ok && data.status === "success") {
      const reply = data.response;
      appendMessage("ai", reply);
      state.chatHistory.push({ role: "model", content: reply });
    } else {
      const errMsg = data.error || "Something went wrong. Please try again.";
      appendMessage("ai", `⚠️ ${errMsg}`, true);
    }
  } catch (err) {
    setTyping(false);
    appendMessage("ai", "⚠️ Network error. Please check your connection and try again.", true);
    console.error("Chat error:", err);
  } finally {
    if (sendBtn) sendBtn.disabled = false;
    input?.focus();
  }
}

/**
 * Append a message bubble to the chat window.
 * @param {'user'|'ai'} role
 * @param {string} text
 * @param {boolean} isError
 */
function appendMessage(role, text, isError = false) {
  const container = $("chat-messages");
  if (!container) return;

  const isAi = role === "ai";
  const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const msgEl = document.createElement("div");
  msgEl.className = `message message-${isAi ? "ai" : "user"}`;
  msgEl.setAttribute("role", "article");
  msgEl.setAttribute("aria-label", `${isAi ? "ElectWise AI" : "You"} at ${now}`);

  const avatar = isAi ? "🗳️" : "👤";
  const name = isAi ? "ElectWise AI" : "You";

  // Format AI text: convert markdown-lite to HTML
  const formattedText = isAi ? formatAiText(text) : `<p>${escapeHtml(text)}</p>`;

  msgEl.innerHTML = `
    <div class="message-avatar" aria-hidden="true">${avatar}</div>
    <div class="message-content">
      <div class="message-header">
        <strong>${name}</strong>
        <span class="message-time" aria-label="Sent at ${now}">${now}</span>
      </div>
      <div class="message-text${isError ? ' style="border-color:var(--clr-danger)"' : ''}">
        ${formattedText}
      </div>
    </div>`;

  container.appendChild(msgEl);

  // Scroll to bottom with smooth behaviour
  container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
}

/**
 * Format AI response text with basic markdown-to-HTML conversion.
 * @param {string} text
 * @returns {string} Safe HTML string
 */
function formatAiText(text) {
  // Escape first, then selectively restore formatting
  let html = escapeHtml(text);

  // Bold: **text** or __text__
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/__(.+?)__/g, "<strong>$1</strong>");

  // Bullet lists: lines starting with - or *
  const lines = html.split("\n");
  const processed = [];
  let inList = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (/^[-*•]\s+/.test(trimmed)) {
      if (!inList) { processed.push("<ul>"); inList = true; }
      processed.push(`<li>${trimmed.replace(/^[-*•]\s+/, "")}</li>`);
    } else {
      if (inList) { processed.push("</ul>"); inList = false; }
      if (trimmed) processed.push(`<p>${trimmed}</p>`);
    }
  }
  if (inList) processed.push("</ul>");

  return processed.join("");
}

/** Show or hide the typing indicator. */
function setTyping(show) {
  const indicator = $("typing-indicator");
  if (indicator) {
    indicator.hidden = !show;
    if (show) {
      const container = $("chat-messages");
      if (container) container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
    }
  }
}

/* ── Voter Guide ────────────────────────────────────────────────────── */

/**
 * Fetch and render the voter registration guide.
 * @param {string} country
 */
async function loadVoterGuide(country) {
  const container = $("guide-container");
  const titleEl = $("guide-title");
  if (!container) return;

  container.innerHTML = `
    <div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--clr-text-muted)">
      <div class="spinner" style="margin:0 auto 16px"></div>
      <p>Loading voter guide…</p>
    </div>`;

  try {
    const res = await fetch(`/api/voter-guide?country=${encodeURIComponent(country)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.status !== "success") throw new Error(data.error);

    const { guide } = data;
    if (titleEl) titleEl.textContent = guide.title;

    container.innerHTML = "";
    guide.checklist.forEach((step, idx) => {
      const card = document.createElement("div");
      card.className = "guide-step-card";
      card.setAttribute("role", "listitem");
      card.setAttribute("aria-label", `Step ${step.step}: ${step.title}`);
      card.style.animationDelay = `${idx * 80}ms`;

      card.innerHTML = `
        <div class="guide-step-icon" aria-hidden="true">${step.icon}</div>
        <div class="guide-step-number">Step ${step.step}</div>
        <h3 class="guide-step-title">${escapeHtml(step.title)}</h3>
        <p class="guide-step-desc">${escapeHtml(step.description)}</p>
        <p class="guide-step-action">→ ${escapeHtml(step.action)}</p>`;

      container.appendChild(card);
    });

  } catch (err) {
    container.innerHTML = `
      <div role="alert" style="grid-column:1/-1;text-align:center;padding:40px;color:var(--clr-text-muted)">
        <p>Failed to load voter guide. <button onclick="loadVoterGuide('${country}')"
          style="color:var(--clr-primary);background:none;border:none;cursor:pointer;font-weight:600;text-decoration:underline">
          Retry
        </button></p>
      </div>`;
    console.error("Voter guide error:", err);
  }
}

/* ── Quiz ───────────────────────────────────────────────────────────── */
function initQuiz() {
  // Difficulty buttons
  document.querySelectorAll(".diff-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".diff-btn").forEach((b) => {
        b.classList.remove("active");
        b.setAttribute("aria-pressed", "false");
      });
      btn.classList.add("active");
      btn.setAttribute("aria-pressed", "true");
      state.quizDifficulty = btn.dataset.diff;
    });
  });

  // Start quiz
  const startBtn = $("start-quiz-btn");
  if (startBtn) {
    startBtn.addEventListener("click", startQuiz);
  }

  // Next question button
  const nextBtn = $("next-btn");
  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      state.currentQuestion++;
      if (state.currentQuestion < state.quizQuestions.length) {
        renderQuestion();
      } else {
        showQuizResults();
      }
    });
  }

  // Retry button
  const retryBtn = $("retry-quiz-btn");
  if (retryBtn) {
    retryBtn.addEventListener("click", resetQuiz);
  }
}

/** Fetch quiz questions from the API and start the quiz. */
async function startQuiz() {
  const startScreen = $("quiz-start-screen");
  const loading = $("quiz-loading");
  const container = $("quiz-container");
  const results = $("quiz-results");

  if (loading) loading.hidden = false;
  if (startScreen) startScreen.style.display = "none";
  if (container) container.hidden = true;
  if (results) results.hidden = true;

  try {
    const res = await fetch("/api/quiz/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        country: state.country,
        difficulty: state.quizDifficulty,
      }),
    });

    const data = await res.json();

    if (loading) loading.hidden = true;

    if (res.ok && data.status === "success") {
      state.quizQuestions = data.questions;
      state.currentQuestion = 0;
      state.score = 0;
      if (container) container.hidden = false;
      renderQuestion();
    } else {
      showQuizError(data.error || "Failed to generate quiz. Please try again.");
    }
  } catch (err) {
    if (loading) loading.hidden = true;
    showQuizError("Network error. Please check your connection.");
    console.error("Quiz error:", err);
  }
}

/** Render the current question. */
function renderQuestion() {
  const q = state.quizQuestions[state.currentQuestion];
  if (!q) return;

  const total = state.quizQuestions.length;
  const idx = state.currentQuestion;
  const pct = Math.round(((idx) / total) * 100);

  // Progress
  const bar = $("quiz-progress-bar");
  if (bar) {
    bar.style.width = pct + "%";
    bar.setAttribute("aria-valuenow", pct);
  }
  const counter = $("quiz-counter");
  if (counter) counter.textContent = `Question ${idx + 1} of ${total}`;

  const scoreDisplay = $("quiz-score-display");
  if (scoreDisplay) scoreDisplay.textContent = `Score: ${state.score}`;

  // Question text
  const questionEl = $("question-text");
  if (questionEl) questionEl.textContent = q.question;

  // Options
  const optionsGrid = $("options-grid");
  if (optionsGrid) {
    optionsGrid.innerHTML = "";
    const letters = ["A", "B", "C", "D"];
    q.options.forEach((option, i) => {
      const btn = document.createElement("button");
      btn.className = "option-btn";
      btn.setAttribute("role", "radio");
      btn.setAttribute("aria-checked", "false");
      btn.setAttribute("data-index", i);
      btn.innerHTML = `
        <span class="option-letter" aria-hidden="true">${letters[i]}</span>
        <span>${escapeHtml(option)}</span>`;
      btn.addEventListener("click", () => handleAnswer(i, q));
      optionsGrid.appendChild(btn);
    });
  }

  // Hide explanation and next button
  const explanationBox = $("explanation-box");
  if (explanationBox) explanationBox.hidden = true;
  const nextBtn = $("next-btn");
  if (nextBtn) nextBtn.hidden = true;
}

/**
 * Handle a user selecting an answer.
 * @param {number} selectedIdx - Index of selected option (0–3)
 * @param {Object} question - Current question data
 */
function handleAnswer(selectedIdx, question) {
  const optionsGrid = $("options-grid");
  const explanationBox = $("explanation-box");
  const nextBtn = $("next-btn");

  // Disable all options
  const optBtns = optionsGrid?.querySelectorAll(".option-btn");
  optBtns?.forEach((btn) => {
    btn.disabled = true;
    btn.setAttribute("aria-checked", "false");
  });

  const isCorrect = selectedIdx === question.correct;

  // Mark correct / wrong
  if (optBtns) {
    optBtns[selectedIdx]?.classList.add(isCorrect ? "correct" : "wrong");
    optBtns[selectedIdx]?.setAttribute("aria-checked", "true");
    if (!isCorrect) {
      optBtns[question.correct]?.classList.add("correct");
    }
  }

  if (isCorrect) {
    state.score++;
    const scoreDisplay = $("quiz-score-display");
    if (scoreDisplay) scoreDisplay.textContent = `Score: ${state.score}`;
  }

  // Show explanation
  if (explanationBox) {
    explanationBox.innerHTML = `
      <strong>${isCorrect ? "✅ Correct!" : "❌ Not quite!"}</strong><br/>
      ${escapeHtml(question.explanation)}`;
    explanationBox.hidden = false;
  }

  // Show next / finish button
  const isLast = state.currentQuestion >= state.quizQuestions.length - 1;
  if (nextBtn) {
    nextBtn.textContent = isLast ? "See Results 🏆" : "Next Question →";
    nextBtn.hidden = false;
    nextBtn.focus();
  }
}

/** Show the quiz results screen. */
function showQuizResults() {
  const container = $("quiz-container");
  const results = $("quiz-results");

  if (container) container.hidden = true;

  const total = state.quizQuestions.length;
  const pct = Math.round((state.score / total) * 100);

  let icon, title, message;
  if (pct === 100) {
    icon = "🏆"; title = "Perfect Score!";
    message = "Outstanding! You're a civic education champion.";
  } else if (pct >= 80) {
    icon = "🌟"; title = "Excellent!";
    message = "Great knowledge of the election process! Review the timeline to fill any gaps.";
  } else if (pct >= 60) {
    icon = "👍"; title = "Good Job!";
    message = "You know the basics. Explore the Election Timeline to learn more.";
  } else {
    icon = "📚"; title = "Keep Learning!";
    message = "Don't worry — use the Election Timeline and Voter Guide to build your knowledge, then try again!";
  }

  if ($("result-icon")) $("result-icon").textContent = icon;
  if ($("result-title")) $("result-title").textContent = title;
  if ($("result-score")) $("result-score").textContent = `${state.score} / ${total} correct (${pct}%)`;
  if ($("result-message")) $("result-message").textContent = message;

  if (results) {
    results.hidden = false;
    results.focus?.();
  }
}

/** Reset the quiz to the start screen. */
function resetQuiz() {
  const startScreen = $("quiz-start-screen");
  const container = $("quiz-container");
  const results = $("quiz-results");
  const loading = $("quiz-loading");

  if (startScreen) startScreen.style.display = "";
  if (container) container.hidden = true;
  if (results) results.hidden = true;
  if (loading) loading.hidden = true;

  state.quizQuestions = [];
  state.currentQuestion = 0;
  state.score = 0;
}

/** Show a quiz error message. */
function showQuizError(message) {
  const startScreen = $("quiz-start-screen");
  if (startScreen) startScreen.style.display = "";

  // Brief accessible alert
  const errEl = document.createElement("div");
  errEl.setAttribute("role", "alert");
  errEl.setAttribute("aria-live", "assertive");
  errEl.style.cssText = `
    color:var(--clr-danger);
    background:rgba(239,68,68,0.1);
    border:1px solid rgba(239,68,68,0.3);
    border-radius:var(--radius-md);
    padding:12px 16px;
    margin-top:16px;
    text-align:center;
    font-size:0.875rem;`;
  errEl.textContent = `⚠️ ${message}`;

  startScreen?.appendChild(errEl);
  setTimeout(() => errEl.remove(), 5000);
}

/* ── High Contrast Toggle ────────────────────────────────────────────── */
function initContrastToggle() {
  const btn = $("contrast-toggle");
  if (!btn) return;

  // Restore preference
  const saved = localStorage.getItem("electwise-contrast");
  if (saved === "high") {
    document.documentElement.classList.add("high-contrast");
    btn.setAttribute("aria-pressed", "true");
  }

  btn.addEventListener("click", () => {
    const isHigh = document.documentElement.classList.toggle("high-contrast");
    btn.setAttribute("aria-pressed", isHigh.toString());
    localStorage.setItem("electwise-contrast", isHigh ? "high" : "normal");
  });
}

/* ── Utility ─────────────────────────────────────────────────────────── */

/**
 * Escape HTML special characters to prevent XSS.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  if (typeof str !== "string") return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");
}
