/**
 * ElectWise — Timeline Module (Gen Z Edition)
 * Horizontal scrollable election phases with drag-scroll & animated detail panel.
 */
"use strict";

/* ── Load & Render ──────────────────────────────────────────────────── */
async function loadTimeline(country) {
  const track    = document.getElementById("tl-track");
  const loading  = document.getElementById("tl-loading");
  const trackWrap= document.querySelector(".tl-track-wrap");
  const detailEl = document.getElementById("tl-detail");
  const titleEl  = document.getElementById("timeline-title");
  const descEl   = document.getElementById("timeline-desc");
  if (!track) return;

  // Show skeleton, hide real track while loading
  if (loading)   { loading.hidden = false; }
  if (trackWrap) { trackWrap.style.visibility = "hidden"; trackWrap.style.height = "0"; }
  track.innerHTML = "";
  if (detailEl) detailEl.hidden = true;

  try {
    const res  = await fetch(`/api/timeline?country=${encodeURIComponent(country)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.status !== "success") throw new Error(data.error);

    // Hide skeleton, reveal track
    if (loading)   { loading.hidden = true; }
    if (trackWrap) { trackWrap.style.visibility = ""; trackWrap.style.height = ""; }

    const { timeline } = data;
    if (titleEl) titleEl.textContent = timeline.title;
    if (descEl)  descEl.textContent  = "Tap any phase card to explore details 👇  ·  Drag to scroll →";

    // Render cards
    timeline.steps.forEach((step, idx) => {
      const card = mkCard(step, idx, country);
      track.appendChild(card);
    });

    initDragScroll(trackWrap);

  } catch (err) {
    if (loading)   { loading.hidden = true; }
    if (trackWrap) { trackWrap.style.visibility = ""; trackWrap.style.height = ""; }
    track.innerHTML = `<div role="alert" style="padding:40px;text-align:center;color:var(--tx2)">
      <p style="font-size:2rem;margin-bottom:12px">⚠️</p>
      <p>Failed to load timeline.</p>
      <button onclick="loadTimeline('${country}')"
        style="margin-top:12px;padding:10px 24px;border-radius:999px;background:var(--violet);
               border:none;color:#fff;cursor:pointer;font-weight:700">
        Retry
      </button>
    </div>`;
    console.error("Timeline error:", err);
  }
}

/* ── Card factory ──────────────────────────────────────────────────── */
function mkCard(step, idx, country) {
  const card = document.createElement("div");
  card.className = "tl-card";
  card.setAttribute("role", "listitem");
  card.setAttribute("tabindex", "0");
  card.setAttribute("aria-label", `Phase ${step.id}: ${step.title}`);
  card.style.animationDelay = `${idx * 60}ms`;

  card.innerHTML = `
    <span class="tl-card-icon" aria-hidden="true">${step.icon}</span>
    <p class="tl-card-num">Phase ${step.id}</p>
    <span class="tl-card-phase" style="color:${step.color};border-color:${step.color}40;background:${step.color}15">
      ${esc(step.phase)}
    </span>
    <h3 class="tl-card-title">${esc(step.title)}</h3>
    <p class="tl-card-dur">⏱ ${esc(step.duration)}</p>
    <p class="tl-card-more" aria-hidden="true">Details →</p>`;

  const open = () => showDetail(step);
  card.addEventListener("click", open);
  card.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
  });

  return card;
}

/* ── Detail panel ──────────────────────────────────────────────────── */
function showDetail(step) {
  const panel = document.getElementById("tl-detail");
  if (!panel) return;

  // Highlight active card
  document.querySelectorAll(".tl-card").forEach((c) => c.classList.remove("active-card"));
  const cards = document.querySelectorAll(".tl-card");
  if (cards[step.id - 1]) cards[step.id - 1].classList.add("active-card");

  document.getElementById("d-icon").textContent  = step.icon;
  document.getElementById("d-phase").textContent = `Phase ${step.id} — ${step.phase}`;
  document.getElementById("d-title").textContent = step.title;
  document.getElementById("d-dur").innerHTML     = `⏱ <span>${esc(step.duration)}</span>`;
  document.getElementById("d-desc").textContent  = step.description;

  const facts = document.getElementById("d-facts");
  facts.innerHTML = "";
  step.details.forEach((d) => {
    const li = document.createElement("li");
    li.textContent = d;
    facts.appendChild(li);
  });

  panel.hidden = false;

  // Smooth scroll to detail panel
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });

  // Focus close button for keyboard a11y
  document.getElementById("close-detail")?.focus();
}

/* ── Close detail ──────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("close-detail")?.addEventListener("click", () => {
    const panel = document.getElementById("tl-detail");
    if (panel) panel.hidden = true;
    document.querySelectorAll(".tl-card").forEach((c) => c.classList.remove("active-card"));
  });

  document.addEventListener("keydown", (e) => {
    const panel = document.getElementById("tl-detail");
    if (e.key === "Escape" && panel && !panel.hidden) {
      panel.hidden = true;
      document.querySelectorAll(".tl-card").forEach((c) => c.classList.remove("active-card"));
    }
  });
});

/* ── Drag-to-scroll ─────────────────────────────────────────────────── */
function initDragScroll(el) {
  if (!el) return;
  let isDown = false, startX = 0, scrollLeft = 0;

  el.addEventListener("mousedown", (e) => {
    isDown = true;
    el.style.userSelect = "none";
    startX = e.pageX - el.offsetLeft;
    scrollLeft = el.scrollLeft;
  });
  el.addEventListener("mouseleave", () => { isDown = false; });
  el.addEventListener("mouseup",    () => { isDown = false; el.style.userSelect = ""; });
  el.addEventListener("mousemove",  (e) => {
    if (!isDown) return;
    e.preventDefault();
    const x    = e.pageX - el.offsetLeft;
    const walk = (x - startX) * 1.5;
    el.scrollLeft = scrollLeft - walk;
  });
}

/* ── Utility ────────────────────────────────────────────────────────── */
function esc(s) {
  if (typeof s !== "string") return "";
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
           .replace(/"/g,"&quot;").replace(/'/g,"&#x27;");
}
