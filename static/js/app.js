/**
 * ElectWise — Main App Script (Gen Z Edition)
 * Handles navigation, chat, voter guide, quiz, and micro-interactions.
 */
"use strict";

/* ── State ──────────────────────────────────────────────────────────── */
const state = {
  country: "India",
  chatHistory: [],
  quiz: { questions: [], current: 0, score: 0 },
  difficulty: "medium",
  timelineLoaded: false,
  guideLoaded: false,
  localLoaded: false,
  viralLoaded: false,
};

/* ── $ shortcut ─────────────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);

/* ── Boot ───────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initCountry();
  initChat();
  initQuiz();
  initContrast();
});

/* ══ NAVIGATION ═════════════════════════════════════════════════════════ */
function initTabs() {
  document.querySelectorAll(".pill").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

function switchTab(name) {
  // Buttons
  document.querySelectorAll(".pill").forEach((b) => {
    const on = b.dataset.tab === name;
    b.classList.toggle("active", on);
    b.setAttribute("aria-selected", on);
  });

  // Panels
  document.querySelectorAll(".tab").forEach((t) => {
    const show = t.id === `tab-${name}`;
    t.classList.toggle("active", show);
    t.classList.toggle("hidden", !show);
  });

  // Lazy load existing sections
  if (name === "timeline" && !state.timelineLoaded) {
    loadTimeline(state.country);
    state.timelineLoaded = true;
  }
  if (name === "guide" && !state.guideLoaded) {
    loadVoterGuide(state.country);
    state.guideLoaded = true;
  }
  // Phase 2 lazy load (functions live in features.js)
  if (name === "local" && !state.localLoaded) {
    if (typeof loadLocalData === "function") loadLocalData();
    state.localLoaded = true;
  }
  if (name === "viral" && !state.viralLoaded) {
    if (typeof loadLeaderboard === "function") loadLeaderboard();
    state.viralLoaded = true;
  }
}

/* ══ COUNTRY ════════════════════════════════════════════════════════════ */
function initCountry() {
  $("country-select")?.addEventListener("change", (e) => {
    state.country = e.target.value;
    state.timelineLoaded = false;
    state.guideLoaded = false;

    const active = document.querySelector(".pill.active")?.dataset.tab;
    if (active === "timeline") { loadTimeline(state.country); state.timelineLoaded = true; }
    if (active === "guide")    { loadVoterGuide(state.country); state.guideLoaded = true; }
  });
}

/* ══ CHAT ═══════════════════════════════════════════════════════════════ */
function initChat() {
  const form  = $("chat-form");
  const input = $("chat-input");
  const btn   = $("send-btn");
  if (!form) return;

  // Auto-grow textarea
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  });

  // Enter = send, Shift+Enter = newline
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); doSend(); }
  });

  form.addEventListener("submit", (e) => { e.preventDefault(); doSend(); });

  // Quick suggestions
  document.querySelectorAll(".suggestion").forEach((chip) => {
    chip.addEventListener("click", () => {
      input.value = chip.dataset.prompt;
      doSend();
    });
  });
}

async function doSend() {
  const input = $("chat-input");
  const btn   = $("send-btn");
  const msg   = input.value.trim();
  if (!msg || btn.disabled) return;

  input.value = "";
  input.style.height = "auto";
  btn.disabled = true;

  appendMsg("user", msg);
  state.chatHistory.push({ role: "user", content: msg });
  setTyping(true);

  try {
    const res  = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: msg,
        country: state.country,
        history: state.chatHistory.slice(-10),
      }),
    });
    const data = await res.json();
    setTyping(false);

    if (res.ok && data.status === "success") {
      appendMsg("ai", data.response);
      state.chatHistory.push({ role: "model", content: data.response });
    } else {
      appendMsg("ai", `⚠️ ${data.error || "Something went wrong. Try again!"}`, true);
    }
  } catch {
    setTyping(false);
    appendMsg("ai", "⚠️ Network error — check your connection and try again.", true);
  } finally {
    btn.disabled = false;
    input.focus();
  }
}

function appendMsg(role, text, isErr = false) {
  const box = $("messages");
  if (!box) return;

  const isAi = role === "ai";
  const now   = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const row = document.createElement("div");
  row.className = `msg-row ${isAi ? "ai" : "user"}`;
  row.setAttribute("role", "article");
  row.setAttribute("aria-label", `${isAi ? "ElectWise AI" : "You"} at ${now}`);

  const bubbleClass = isAi ? "ai-bubble" : "user-bubble";
  const avatarClass = isAi ? "ai-avatar" : "user-avatar";
  const avatarIcon  = isAi ? "⚡" : "👤";
  const name        = isAi ? "ElectWise AI" : "You";

  row.innerHTML = `
    <div class="avatar ${avatarClass}" aria-hidden="true">${avatarIcon}</div>
    <div class="bubble-wrap">
      <div class="sender">${name} <span class="ts">${now}</span></div>
      <div class="bubble ${bubbleClass}">${isAi ? fmtAI(text) : `<p>${esc(text)}</p>`}</div>
    </div>`;

  box.appendChild(row);
  box.scrollTo({ top: box.scrollHeight, behavior: "smooth" });
}

/** Lightweight markdown → HTML (escaped first, then formatted). */
function fmtAI(raw) {
  let t = esc(raw);

  // Bold
  t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  t = t.replace(/__(.+?)__/g, "<strong>$1</strong>");

  // Split into lines, handle bullets and paragraphs
  const lines = t.split("\n");
  const out   = [];
  let inList  = false;

  for (const line of lines) {
    const s = line.trim();
    if (!s) {
      if (inList) { out.push("</ul>"); inList = false; }
      continue;
    }
    if (/^[-*•]\s/.test(s)) {
      if (!inList) { out.push("<ul>"); inList = true; }
      out.push(`<li>${s.replace(/^[-*•]\s+/, "")}</li>`);
    } else {
      if (inList) { out.push("</ul>"); inList = false; }
      out.push(`<p>${s}</p>`);
    }
  }
  if (inList) out.push("</ul>");
  return out.join("");
}

function setTyping(show) {
  const row = $("typing-row");
  if (!row) return;
  row.hidden = !show;
  if (show) $("messages")?.scrollTo({ top: $("messages").scrollHeight, behavior: "smooth" });
}

/* ══ VOTER GUIDE ════════════════════════════════════════════════════════ */
async function loadVoterGuide(country) {
  const grid    = $("guide-grid");
  const titleEl = $("guide-title");
  if (!grid) return;

  grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:60px;color:var(--tx2)">
    <div class="sk-card" style="width:100%;max-width:300px;height:100px;margin:0 auto"></div>
  </div>`;

  try {
    const res  = await fetch(`/api/voter-guide?country=${encodeURIComponent(country)}`);
    const data = await res.json();
    if (data.status !== "success") throw new Error(data.error);

    const { guide } = data;
    if (titleEl) titleEl.textContent = guide.title;
    grid.innerHTML = "";

    guide.checklist.forEach((step, i) => {
      const card = document.createElement("div");
      card.className = "guide-card";
      card.setAttribute("role", "listitem");
      card.setAttribute("aria-label", `Step ${step.step}: ${step.title}`);
      card.style.animationDelay = `${i * 60}ms`;

      card.innerHTML = `
        <div class="guide-icon" aria-hidden="true">${step.icon}</div>
        <span class="guide-step-tag">Step ${step.step}</span>
        <h3 class="guide-card-title">${esc(step.title)}</h3>
        <p class="guide-card-desc">${esc(step.description)}</p>
        <p class="guide-card-action">→ ${esc(step.action)}</p>`;
      grid.appendChild(card);
    });

  } catch (err) {
    grid.innerHTML = `<div role="alert" style="grid-column:1/-1;text-align:center;padding:40px;color:var(--tx2)">
      ⚠️ Failed to load. <button onclick="loadVoterGuide('${country}')"
        style="color:var(--violet-lt);background:none;border:none;cursor:pointer;font-weight:700;text-decoration:underline">Retry</button>
    </div>`;
    console.error(err);
  }
}

/* ══ QUIZ ════════════════════════════════════════════════════════════════ */
function initQuiz() {
  // Difficulty
  document.querySelectorAll(".diff-btn").forEach((b) => {
    b.addEventListener("click", () => {
      document.querySelectorAll(".diff-btn").forEach((x) => {
        x.classList.remove("active");
        x.setAttribute("aria-pressed", "false");
      });
      b.classList.add("active");
      b.setAttribute("aria-pressed", "true");
      state.difficulty = b.dataset.diff;
    });
  });

  $("gen-quiz-btn")?.addEventListener("click", startQuiz);
  $("next-btn")?.addEventListener("click", nextQ);
  $("retry-btn")?.addEventListener("click", resetQuiz);
}

async function startQuiz() {
  show("quiz-loading");
  hide("quiz-start");
  hide("quiz-container");
  hide("quiz-results");

  try {
    const res  = await fetch("/api/quiz/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ country: state.country, difficulty: state.difficulty }),
    });
    const data = await res.json();
    hide("quiz-loading");

    if (res.ok && data.status === "success") {
      state.quiz = { questions: data.questions, current: 0, score: 0 };
      show("quiz-container");
      renderQ();
    } else {
      quizErr(data.error || "Failed to generate quiz. Try again.");
    }
  } catch {
    hide("quiz-loading");
    quizErr("Network error. Please check your connection.");
  }
}

function renderQ() {
  const q     = state.quiz.questions[state.quiz.current];
  const total = state.quiz.questions.length;
  const idx   = state.quiz.current;
  const pct   = Math.round((idx / total) * 100);

  // Progress
  const bar = $("q-bar");
  if (bar) { bar.style.width = pct + "%"; bar.setAttribute("aria-valuenow", pct); }
  if ($("q-counter")) $("q-counter").textContent = `${idx + 1} / ${total}`;
  if ($("q-score"))   $("q-score").textContent   = `⭐ ${state.quiz.score}`;
  if ($("q-num"))     $("q-num").textContent      = `Q${idx + 1}`;
  if ($("q-text"))    $("q-text").textContent     = q.question;

  // Options
  const opts = $("options");
  if (opts) {
    opts.innerHTML = "";
    const letters = ["A", "B", "C", "D"];
    q.options.forEach((opt, i) => {
      const btn = document.createElement("button");
      btn.className = "opt";
      btn.dataset.index = i;
      btn.setAttribute("role", "radio");
      btn.setAttribute("aria-checked", "false");
      btn.innerHTML = `<span class="opt-letter" aria-hidden="true">${letters[i]}</span><span>${esc(opt)}</span>`;
      btn.addEventListener("click", () => pickAnswer(i, q));
      opts.appendChild(btn);
    });
  }

  hide("explanation");
  hide("next-btn");
}

function pickAnswer(selected, q) {
  const allOpts = $("options")?.querySelectorAll(".opt") || [];
  allOpts.forEach((b) => { b.disabled = true; });

  const isCorrect = selected === q.correct;

  allOpts[selected]?.classList.add(isCorrect ? "correct" : "wrong");
  allOpts[selected]?.setAttribute("aria-checked", "true");
  if (!isCorrect) allOpts[q.correct]?.classList.add("correct");

  if (isCorrect) {
    state.quiz.score++;
    if ($("q-score")) $("q-score").textContent = `⭐ ${state.quiz.score}`;
  }

  const expBox = $("explanation");
  if (expBox) {
    expBox.innerHTML = `<strong>${isCorrect ? "✅ Correct!" : "❌ Not quite!"}</strong> ${esc(q.explanation)}`;
    show("explanation");
  }

  const isLast = state.quiz.current >= state.quiz.questions.length - 1;
  const nextBtn = $("next-btn");
  if (nextBtn) {
    nextBtn.textContent = isLast ? "See Results 🏆" : "Next →";
    show("next-btn");
    nextBtn.focus();
  }
}

function nextQ() {
  state.quiz.current++;
  if (state.quiz.current < state.quiz.questions.length) {
    renderQ();
  } else {
    showResults();
  }
}

function showResults() {
  hide("quiz-container");
  const pct   = Math.round((state.quiz.score / state.quiz.questions.length) * 100);
  const total = state.quiz.questions.length;

  let icon, title, msg;
  if (pct === 100) { icon = "🏆"; title = "Perfect!"; msg = "You're a civic legend 🔥 Absolutely crushed it!"; }
  else if (pct >= 80) { icon = "🌟"; title = "Excellent!"; msg = "Top-tier knowledge! A little more and you'll be unstoppable."; }
  else if (pct >= 60) { icon = "👍"; title = "Not bad!"; msg = "Solid effort! Check the Timeline to fill your gaps."; }
  else { icon = "📚"; title = "Keep going!"; msg = "Elections can be complex — use the Timeline & Guide, then try again!"; }

  if ($("res-icon"))  $("res-icon").textContent  = icon;
  if ($("res-title")) $("res-title").textContent  = title;
  if ($("res-score")) $("res-score").textContent  = `${state.quiz.score}/${total} correct · ${pct}%`;
  if ($("res-msg"))   $("res-msg").textContent    = msg;

  show("quiz-results");

  // Confetti when score ≥ 60%
  if (pct >= 60) launchConfetti();
}

function launchConfetti() {
  const wrap = $("confetti-wrap");
  if (!wrap) return;
  wrap.innerHTML = "";
  const colors = ["#7C3AED","#EC4899","#06B6D4","#10B981","#F59E0B","#A78BFA"];
  for (let i = 0; i < 50; i++) {
    const c = document.createElement("div");
    c.className = "confetti-piece";
    c.style.cssText = `
      left:${Math.random()*100}%;
      background:${colors[Math.floor(Math.random()*colors.length)]};
      animation-delay:${Math.random()*1}s;
      animation-duration:${1.5+Math.random()*1}s;
      width:${6+Math.random()*8}px;height:${6+Math.random()*8}px;
      border-radius:${Math.random()>.5?"50%":"2px"};`;
    wrap.appendChild(c);
  }
}

function resetQuiz() {
  hide("quiz-results");
  hide("quiz-container");
  hide("quiz-loading");
  show("quiz-start");
  state.quiz = { questions: [], current: 0, score: 0 };
}

function quizErr(msg) {
  show("quiz-start");
  const existing = document.querySelector(".quiz-err");
  if (existing) existing.remove();
  const el = document.createElement("div");
  el.className = "quiz-err";
  el.setAttribute("role", "alert");
  el.style.cssText = `color:var(--red);background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);
    border-radius:var(--r-lg);padding:12px 16px;margin-top:16px;text-align:center;font-size:.875rem;`;
  el.textContent = `⚠️ ${msg}`;
  $("quiz-start")?.appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

/* ══ HIGH CONTRAST ══════════════════════════════════════════════════════ */
function initContrast() {
  const btn = $("contrast-toggle");
  if (!btn) return;
  if (localStorage.getItem("ew-contrast") === "1") {
    document.documentElement.classList.add("hc");
    btn.setAttribute("aria-pressed", "true");
  }
  btn.addEventListener("click", () => {
    const on = document.documentElement.classList.toggle("hc");
    btn.setAttribute("aria-pressed", on.toString());
    localStorage.setItem("ew-contrast", on ? "1" : "0");
  });
}

/* ══ UTILS ══════════════════════════════════════════════════════════════ */
function esc(s) {
  if (typeof s !== "string") return "";
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
           .replace(/"/g,"&quot;").replace(/'/g,"&#x27;");
}
function show(id) { const el = $(id); if (el) el.hidden = false; }
function hide(id) { const el = $(id); if (el) el.hidden = true; }
