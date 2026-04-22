/**
 * ElectWise AI — Timeline Module
 * Handles fetching and rendering the interactive election timeline.
 */

"use strict";

/* ── Timeline renderer ─────────────────────────────────────────────── */

/**
 * Fetch timeline data from the backend and render it.
 * @param {string} country - 'India' | 'USA' | 'UK'
 */
async function loadTimeline(country) {
  const container = document.getElementById("timeline-container");
  const loading = document.getElementById("timeline-loading");
  const titleEl = document.getElementById("timeline-title");
  const descEl = document.getElementById("timeline-desc");

  if (!container) return;

  // Show loading state
  loading.hidden = false;
  container.innerHTML = "";

  try {
    const res = await fetch(`/api/timeline?country=${encodeURIComponent(country)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.status !== "success") throw new Error(data.error || "Unknown error");

    const { timeline } = data;

    // Update header
    if (titleEl) titleEl.textContent = timeline.title;
    if (descEl) descEl.textContent = timeline.description;

    loading.hidden = true;

    // Render each step with staggered animation
    timeline.steps.forEach((step, idx) => {
      const el = createTimelineStep(step, idx);
      container.appendChild(el);
    });

  } catch (err) {
    loading.hidden = true;
    container.innerHTML = `
      <div role="alert" style="text-align:center;padding:40px;color:var(--clr-text-muted)">
        <p style="font-size:2rem;margin-bottom:12px">⚠️</p>
        <p>Failed to load timeline. Please check your connection and try again.</p>
        <button onclick="loadTimeline('${country}')"
          style="margin-top:16px;padding:10px 24px;border-radius:999px;
                 background:var(--clr-primary);border:none;color:#fff;cursor:pointer;font-weight:600">
          Retry
        </button>
      </div>`;
    console.error("Timeline load error:", err);
  }
}

/**
 * Create a single timeline step DOM element.
 * @param {Object} step - Step data from API
 * @param {number} idx - Step index (for animation delay)
 * @returns {HTMLElement}
 */
function createTimelineStep(step, idx) {
  const wrapper = document.createElement("div");
  wrapper.className = "timeline-step";
  wrapper.setAttribute("role", "listitem");
  wrapper.setAttribute("tabindex", "0");
  wrapper.setAttribute("aria-label", `Phase ${step.id}: ${step.title}`);
  wrapper.style.animationDelay = `${idx * 80}ms`;

  wrapper.innerHTML = `
    <div class="step-connector">
      <div class="step-icon"
           style="border-color:${step.color};box-shadow:0 0 16px ${step.color}40"
           aria-hidden="true">
        ${step.icon}
      </div>
    </div>
    <div class="step-card">
      <div class="step-meta">
        <span class="step-phase-badge"
              style="color:${step.color};border-color:${step.color}40;background:${step.color}15">
          ${step.phase}
        </span>
        <span class="step-duration">⏱ ${escapeHtml(step.duration)}</span>
      </div>
      <h3 class="step-title">${escapeHtml(step.title)}</h3>
      <p class="step-desc">${escapeHtml(step.description)}</p>
      <span class="step-more" aria-hidden="true">View details →</span>
    </div>`;

  // Open modal on click or Enter/Space
  const openModal = () => showStepModal(step);
  wrapper.addEventListener("click", openModal);
  wrapper.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openModal();
    }
  });

  return wrapper;
}

/* ── Step Modal ─────────────────────────────────────────────────────── */

/**
 * Display the step detail modal.
 * @param {Object} step - Step data
 */
function showStepModal(step) {
  const modal = document.getElementById("step-modal");
  if (!modal) return;

  document.getElementById("modal-icon").textContent = step.icon;
  document.getElementById("modal-title").textContent = step.title;
  document.getElementById("modal-phase").textContent = `Phase ${step.id} — ${step.phase}`;
  document.getElementById("modal-desc").textContent = step.description;
  document.getElementById("modal-duration").textContent = step.duration;

  const detailsList = document.getElementById("modal-details");
  detailsList.innerHTML = "";
  step.details.forEach((detail) => {
    const li = document.createElement("li");
    li.textContent = detail;
    detailsList.appendChild(li);
  });

  modal.hidden = false;
  document.body.style.overflow = "hidden";

  // Focus the close button for accessibility
  const closeBtn = document.getElementById("modal-close");
  if (closeBtn) closeBtn.focus();
}

/** Close the step detail modal. */
function closeStepModal() {
  const modal = document.getElementById("step-modal");
  if (!modal) return;
  modal.hidden = true;
  document.body.style.overflow = "";
}

/* ── Modal event listeners ──────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
  const closeBtn = document.getElementById("modal-close");
  const backdrop = document.getElementById("modal-backdrop");

  if (closeBtn) closeBtn.addEventListener("click", closeStepModal);
  if (backdrop) backdrop.addEventListener("click", closeStepModal);

  // Close on Escape
  document.addEventListener("keydown", (e) => {
    const modal = document.getElementById("step-modal");
    if (e.key === "Escape" && modal && !modal.hidden) {
      closeStepModal();
    }
  });
});

/* ── Utility ────────────────────────────────────────────────────────── */

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
