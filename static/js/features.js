/**
 * ElectWise — Phase 2 Features JS
 * Local (Constituency) + Viral (Social) tabs
 * India-only · Bilingual (EN + Indian language variable)
 */
"use strict";

/* ── App-level state for Phase 2 ─────────────────────────────────── */
const p2 = {
  constituency: "Chandni Chowk, Delhi",
  lang: "en",                        // current Indian language code
  vmAnswers: [],                     // Voter Match answers
  vmCurrent: 0,                      // current question index
  squadCode: null,
  squadMembers: [],
};

const VOTER_MATCH_ISSUES = [
  { id: 1, statement: "Free electricity up to 300 units/month should be given to every household.", statement_hi: "हर घर को 300 यूनिट तक मुफ्त बिजली मिलनी चाहिए।" },
  { id: 2, statement: "New highways & metros should take priority over funding public schools.", statement_hi: "नए राजमार्ग व मेट्रो स्कूल फंडिंग से ज़्यादा ज़रूरी हैं।" },
  { id: 3, statement: "Reservations should be extended to economically weaker sections regardless of caste.", statement_hi: "आरक्षण जाति के बजाय आर्थिक आधार पर होना चाहिए।" },
  { id: 4, statement: "India should fast-track nuclear energy to meet its 2050 climate targets.", statement_hi: "भारत को 2050 लक्ष्य के लिये परमाणु ऊर्जा तेज़ करनी चाहिए।" },
  { id: 5, statement: "Farmers deserve a guaranteed minimum income regardless of crop yield.", statement_hi: "किसानों को फसल उत्पादन से निरपेक्ष न्यूनतम आय गारंटी मिले।" },
  { id: 6, statement: "Tech companies should be taxed more to fund rural healthcare.", statement_hi: "टेक कंपनियों पर अधिक कर लगाकर ग्रामीण स्वास्थ्य निधि बनाई जाए।" },
];

/* ── Language System ─────────────────────────────────────────────── */
const LANG_LABELS = { en: "EN", hi: "हिं", ta: "த", te: "తె", bn: "বাং", mr: "म" };
const LANG_NAMES  = { en: "English", hi: "Hindi", ta: "Tamil", te: "Telugu", bn: "Bengali", mr: "Marathi" };

// Hindi static translations for UI elements
const HI_TRANSLATIONS = {
  "Ask AI": "AI से पूछें", "Timeline": "टाइमलाइन", "How to Vote": "वोट कैसे करें",
  "Quiz": "क्विज़", "Local": "स्थानीय", "Viral": "वायरल",
  "Quick asks": "तुरंत पूछें", "Generate Quiz ✨": "क्विज़ बनाएं ✨",
  "Know Your Vote.": "अपना वोट जानो।", "Election Timeline": "चुनाव टाइमलाइन",
  "How to Vote": "वोट करने का तरीका", "Candidate Vibe Check": "उम्मीदवार वाइब चेक",
  "Your Booth": "आपका बूथ", "Local Issues": "स्थानीय मुद्दे",
  "Crowd Reporter": "भीड़ रिपोर्टर", "EVM Practice": "EVM अभ्यास",
  "Voter Match": "वोटर मैच", "Roast My Excuses": "मेरे बहाने रोस्ट करो",
  "Leaderboard": "लीडरबोर्ड", "Squad Pact": "दोस्त गैंग",
};

function initLanguage() {
  const toggle = document.getElementById("lang-btn");
  const select = document.getElementById("lang-select");
  if (!toggle || !select) return;

  // Restore saved language
  const saved = localStorage.getItem("ew-lang") || "en";
  p2.lang = saved;
  applyLanguage(saved);
  if (select) select.value = saved;
  toggle.textContent = LANG_LABELS[saved] || "EN";

  select.addEventListener("change", () => {
    p2.lang = select.value;
    applyLanguage(p2.lang);
    localStorage.setItem("ew-lang", p2.lang);
    toggle.textContent = LANG_LABELS[p2.lang] || "EN";
    select.style.display = "none";
  });

  toggle.addEventListener("click", () => {
    const shown = select.style.display !== "none";
    select.style.display = shown ? "none" : "block";
  });
}

function applyLanguage(lang) {
  // Apply bilingual data attributes
  document.querySelectorAll("[data-en]").forEach(el => {
    const hiText = el.dataset.hi;
    if (lang !== "en" && hiText) {
      el.textContent = hiText;
    } else {
      el.textContent = el.dataset.en;
    }
  });
  // Apply to placeholders
  document.querySelectorAll("[data-en-placeholder]").forEach(el => {
    const hiText = el.dataset["hi-placeholder"];
    el.placeholder = (lang !== "en" && hiText) ? hiText : el.dataset["en-placeholder"];
  });
}

/* ── Local Tab ───────────────────────────────────────────────────── */
let localLoaded = false;

function initLocalTab() {
  const cSelect = document.getElementById("constituency-select");
  if (!cSelect) return;

  // Populate constituency dropdown
  const constituencies = [
    "Chandni Chowk, Delhi", "New Delhi, Delhi",
    "South Delhi, Delhi", "East Delhi, Delhi", "North West Delhi, Delhi",
  ];
  constituencies.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c; opt.textContent = c;
    cSelect.appendChild(opt);
  });

  cSelect.addEventListener("change", () => {
    p2.constituency = cSelect.value;
    loadLocalData();
  });

  // EVM sandbox toggle
  document.getElementById("evm-launch-btn")?.addEventListener("click", () => {
    document.getElementById("evm-overlay").hidden = false;
    document.body.style.overflow = "hidden";
  });
  document.getElementById("evm-close-btn")?.addEventListener("click", closeEvm);
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeEvm();
  });

  // Crowd report submit
  document.getElementById("crowd-submit-btn")?.addEventListener("click", submitCrowdReport);
}

async function loadLocalData() {
  const name = p2.constituency;
  const sections = ["candidates-wrap", "booth-wrap", "issues-wrap", "crowd-wrap", "evm-wrap"];
  sections.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.opacity = "0.4";
  });

  try {
    const res = await fetch(`/api/constituency?name=${encodeURIComponent(name)}`);
    const data = await res.json();
    if (data.status !== "success") throw new Error(data.error);

    const { candidates, booth, issues } = data.data;
    renderCandidates(candidates);
    renderBooth(booth, name);
    renderIssues(issues);
    renderEvm(candidates);
    await loadCrowdData(name);

    sections.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.opacity = "1";
    });
  } catch (err) {
    console.error("Local data load error:", err);
  }
}

/* ── Candidate Vibe Check ──────────────────────────────────────── */
function renderCandidates(candidates) {
  const wrap = document.getElementById("candidates-wrap");
  if (!wrap) return;

  wrap.innerHTML = "";
  let current = 0;

  candidates.forEach((c, i) => {
    const card = document.createElement("div");
    card.className = `cand-card ${i === 0 ? "active" : ""}`;
    card.setAttribute("aria-label", `Candidate: ${c.name}, ${c.party}`);
    card.style.borderColor = c.color + "55";
    card.innerHTML = `
      <div class="cand-header" style="background:linear-gradient(135deg,${c.color}22,${c.color}08)">
        <span class="cand-symbol" style="color:${c.color}" aria-hidden="true">${c.symbol}</span>
        <div>
          <h3 class="cand-name">${esc(c.name)}</h3>
          <span class="cand-party" style="color:${c.color}">${esc(c.party)} · ${esc(c.vibe)}</span>
        </div>
      </div>
      <div class="cand-pillars" aria-label="Top policy pillars">
        ${c.pillars.map(p => `<span class="pillar-tag">${esc(p)}</span>`).join("")}
      </div>
      <div class="cand-meta">
        <p class="cand-record">📋 ${esc(c.record)}</p>
        <p class="cand-endorse">⭐ Endorsed by ${esc(c.endorsements)}</p>
      </div>`;
    wrap.appendChild(card);
  });

  // Dot nav
  const dotsEl = document.getElementById("cand-dots");
  if (dotsEl) {
    dotsEl.innerHTML = "";
    candidates.forEach((_, i) => {
      const dot = document.createElement("button");
      dot.className = `cand-dot ${i === 0 ? "active" : ""}`;
      dot.setAttribute("aria-label", `Candidate ${i + 1} of ${candidates.length}`);
      dot.addEventListener("click", () => goToCandidate(i));
      dotsEl.appendChild(dot);
    });
  }

  // Arrow nav
  document.getElementById("cand-prev")?.addEventListener("click", () => {
    current = (current - 1 + candidates.length) % candidates.length;
    goToCandidate(current);
  });
  document.getElementById("cand-next")?.addEventListener("click", () => {
    current = (current + 1) % candidates.length;
    goToCandidate(current);
  });

  function goToCandidate(idx) {
    current = idx;
    wrap.querySelectorAll(".cand-card").forEach((c, i) => c.classList.toggle("active", i === idx));
    document.querySelectorAll(".cand-dot").forEach((d, i) => d.classList.toggle("active", i === idx));
  }
}

/* ── Booth Navigator ─────────────────────────────────────────────── */
function renderBooth(booth, constituency) {
  const wrap = document.getElementById("booth-wrap");
  if (!wrap) return;

  wrap.innerHTML = `
    <div class="booth-card">
      <div class="booth-header">
        <span aria-hidden="true">📍</span>
        <div>
          <h3 class="booth-name">${esc(booth.name)}</h3>
          <p class="booth-addr">${esc(booth.address)}</p>
        </div>
      </div>
      <p class="booth-tip">🚇 ${esc(booth.tip)}</p>
      <a href="${esc(booth.maps_url)}" target="_blank" rel="noopener noreferrer"
         class="maps-btn" aria-label="Open booth location in Google Maps">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        Open in Google Maps
      </a>
    </div>`;
}

/* ── Heatmap ─────────────────────────────────────────────────────── */
function renderIssues(issues) {
  const wrap = document.getElementById("issues-wrap");
  if (!wrap) return;

  wrap.innerHTML = `<h4 class="local-section-label" data-en="Top Local Issues" data-hi="शीर्ष स्थानीय मुद्दे">Top Local Issues</h4>
    <div class="heatmap" role="list">
      ${issues.map(issue => `
        <div class="heatmap-row" role="listitem" aria-label="${esc(issue.issue)}: ${issue.intensity}% intensity">
          <span class="heat-icon" aria-hidden="true">${issue.icon}</span>
          <div class="heat-info">
            <div class="heat-labels">
              <span class="heat-name">${esc(issue.issue)}</span>
              <span class="heat-name-hi" aria-hidden="true">${esc(issue.issue_hi || "")}</span>
              <span class="heat-pct">${issue.intensity}%</span>
            </div>
            <div class="heat-bar-wrap" aria-hidden="true">
              <div class="heat-bar" style="--pct:${issue.intensity}"></div>
            </div>
          </div>
        </div>`).join("")}
    </div>`;

  // Animate bars
  setTimeout(() => {
    wrap.querySelectorAll(".heat-bar").forEach(bar => {
      bar.style.width = bar.style.getPropertyValue("--pct") + "%";
    });
  }, 100);
}

/* ── Crowd Reporter ──────────────────────────────────────────────── */
async function loadCrowdData(constituency) {
  const wrap = document.getElementById("crowd-status");
  if (!wrap) return;
  try {
    const res = await fetch(`/api/crowd?constituency=${encodeURIComponent(constituency)}`);
    const data = await res.json();
    const reports = data.reports || [];
    const avg = data.avg_wait_min;

    if (reports.length === 0) {
      wrap.innerHTML = `<p class="crowd-empty" data-en="No reports yet. Be the first to report!" data-hi="अभी कोई रिपोर्ट नहीं। पहले रिपोर्ट करें!">No reports yet. Be the first to report!</p>`;
      return;
    }
    wrap.innerHTML = `
      <div class="crowd-summary">
        <span class="crowd-avg-badge">${avg !== null ? avg + " min avg wait" : "Reports available"}</span>
      </div>
      ${reports.slice(-3).reverse().map(r => `
        <div class="crowd-pill">
          ${r.label} · <span class="crowd-ts">${new Date(r.ts).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</span>
        </div>`).join("")}`;
  } catch (err) {
    console.error("Crowd data error:", err);
  }
}

async function submitCrowdReport() {
  const min = parseInt(document.getElementById("crowd-wait-input")?.value || "0");
  const crowded = document.getElementById("crowd-crowded-check")?.checked || false;
  const btn = document.getElementById("crowd-submit-btn");

  if (isNaN(min) || min < 0) return;
  if (btn) btn.disabled = true;

  try {
    const res = await fetch("/api/crowd", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ constituency: p2.constituency, wait_min: min, crowded }),
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast("✅ Report submitted! Thank you.");
      await loadCrowdData(p2.constituency);
    }
  } catch { showToast("⚠️ Could not submit. Try again."); }
  finally { if (btn) btn.disabled = false; }
}

/* ── EVM Sandbox ─────────────────────────────────────────────────── */
function renderEvm(candidates) {
  const wrap = document.getElementById("evm-candidates");
  if (!wrap) return;

  wrap.innerHTML = "";
  candidates.forEach((c, i) => {
    const row = document.createElement("div");
    row.className = "evm-row";
    row.setAttribute("role", "radio");
    row.setAttribute("aria-checked", "false");
    row.setAttribute("aria-label", `Vote for ${c.name}, ${c.party}`);
    row.setAttribute("tabindex", "0");
    row.innerHTML = `
      <span class="evm-num">${i + 1}</span>
      <span class="evm-sym" aria-hidden="true">${c.symbol}</span>
      <div class="evm-info">
        <strong>${esc(c.name)}</strong>
        <span>${esc(c.party)}</span>
      </div>
      <div class="evm-btn-wrap">
        <button class="evm-vote-btn" data-idx="${i}" aria-label="Press to vote for ${c.name}" tabindex="-1">▶</button>
        <div class="evm-led" aria-hidden="true"></div>
      </div>`;
    const pressVote = () => castEvmVote(i, candidates, wrap);
    row.querySelector(".evm-vote-btn").addEventListener("click", pressVote);
    row.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pressVote(); } });
    wrap.appendChild(row);
  });
}

function castEvmVote(selected, candidates, wrap) {
  // Reset all
  wrap.querySelectorAll(".evm-row").forEach(r => {
    r.classList.remove("evm-selected");
    r.setAttribute("aria-checked", "false");
    r.querySelector(".evm-led").classList.remove("lit");
  });
  const rows = wrap.querySelectorAll(".evm-row");
  rows[selected]?.classList.add("evm-selected");
  rows[selected]?.setAttribute("aria-checked", "true");
  rows[selected]?.querySelector(".evm-led").classList.add("lit");

  // VVPAT simulation
  const vvpat = document.getElementById("vvpat-display");
  if (vvpat) {
    const c = candidates[selected];
    vvpat.innerHTML = `
      <div class="vvpat-slip">
        <p class="vvpat-title">VVPAT Paper Trail</p>
        <p class="vvpat-emoji">${c.symbol}</p>
        <p class="vvpat-name">${esc(c.name)}</p>
        <p class="vvpat-party">${esc(c.party)}</p>
        <p class="vvpat-msg">✅ Your vote is recorded securely</p>
      </div>`;
    vvpat.hidden = false;
    setTimeout(() => { vvpat.hidden = true; }, 4000);
  }
  showToast(`🗳️ Practice vote cast for ${candidates[selected].name}`);
}

function closeEvm() {
  const ov = document.getElementById("evm-overlay");
  if (ov) ov.hidden = true;
  document.body.style.overflow = "";
}

/* ── Viral Tab ───────────────────────────────────────────────────── */
function initViralTab() {
  // Roast
  document.getElementById("roast-btn")?.addEventListener("click", generateRoast);
  document.getElementById("roast-input")?.addEventListener("keydown", e => {
    if (e.key === "Enter") generateRoast();
  });

  // Voter Match
  initVoterMatch();

  // Leaderboard
  loadLeaderboard();

  // Squad
  initSquad();
}

/* ── Roast My Excuses ─────────────────────────────────────────────── */
async function generateRoast() {
  const input = document.getElementById("roast-input");
  const output = document.getElementById("roast-output");
  const btn = document.getElementById("roast-btn");
  const excuse = input?.value.trim();
  if (!excuse) { showToast("Type your excuse first!"); return; }

  if (btn) btn.disabled = true;
  if (output) output.innerHTML = `<div class="roast-loading"><span></span><span></span><span></span></div>`;

  try {
    const res = await fetch("/api/roast", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ excuse, lang: p2.lang }),
    });
    const data = await res.json();

    if (data.status === "success") {
      if (output) {
        output.innerHTML = `
          <div class="roast-result" role="region" aria-label="Your roast">
            <p class="roast-text">${esc(data.roast)}</p>
            <button class="roast-share-btn" onclick="copyToClip('roast-text-val','Roast copied!')" title="Copy to clipboard">📋 Copy & Share</button>
            <span id="roast-text-val" style="display:none">${esc(data.roast)}</span>
          </div>`;
      }
    } else {
      if (output) output.innerHTML = `<p style="color:var(--red)">${esc(data.error)}</p>`;
    }
  } catch {
    if (output) output.innerHTML = `<p style="color:var(--red)">Network error. Please try again.</p>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

/* ── Voter Match Wrapped ──────────────────────────────────────────── */
function initVoterMatch() {
  p2.vmAnswers = []; p2.vmCurrent = 0;
  const startBtn = document.getElementById("vm-start-btn");
  startBtn?.addEventListener("click", startVoterMatch);
  document.getElementById("vm-restart-btn")?.addEventListener("click", startVoterMatch);
}

function startVoterMatch() {
  p2.vmAnswers = []; p2.vmCurrent = 0;
  document.getElementById("vm-start")?.setAttribute("hidden", "");
  document.getElementById("vm-result")?.setAttribute("hidden", "");
  document.getElementById("vm-question")?.removeAttribute("hidden");
  renderVmQuestion();
}

function renderVmQuestion() {
  const q = VOTER_MATCH_ISSUES[p2.vmCurrent];
  if (!q) { submitVoterMatch(); return; }

  const pct = Math.round((p2.vmCurrent / VOTER_MATCH_ISSUES.length) * 100);
  const bar = document.getElementById("vm-bar");
  if (bar) { bar.style.width = pct + "%"; bar.setAttribute("aria-valuenow", pct); }
  const ctr = document.getElementById("vm-counter");
  if (ctr) ctr.textContent = `${p2.vmCurrent + 1} / ${VOTER_MATCH_ISSUES.length}`;
  const stmt = document.getElementById("vm-statement");
  if (stmt) {
    stmt.textContent = (p2.lang !== "en" && q.statement_hi) ? q.statement_hi : q.statement;
  }
}

function vmAnswer(agree) {
  const q = VOTER_MATCH_ISSUES[p2.vmCurrent];
  p2.vmAnswers.push({ issue_id: q.id, agree });
  p2.vmCurrent++;
  if (p2.vmCurrent < VOTER_MATCH_ISSUES.length) {
    renderVmQuestion();
  } else {
    submitVoterMatch();
  }
}

async function submitVoterMatch() {
  document.getElementById("vm-question")?.setAttribute("hidden", "");
  document.getElementById("vm-loading")?.removeAttribute("hidden");

  try {
    const res = await fetch("/api/voter-match", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: p2.vmAnswers, lang: p2.lang }),
    });
    const data = await res.json();

    document.getElementById("vm-loading")?.setAttribute("hidden", "");

    if (data.status === "success") {
      const r = data.result;
      const res_el = document.getElementById("vm-result");
      if (res_el) {
        res_el.removeAttribute("hidden");
        document.getElementById("vm-vibe").textContent      = r.vibe_label || "";
        document.getElementById("vm-match-a").textContent   = `${r.match_a?.pct || "–"}% ${r.match_a?.party_style || ""}`;
        document.getElementById("vm-match-b").textContent   = `${r.match_b?.pct || "–"}% ${r.match_b?.party_style || ""}`;
        document.getElementById("vm-top-issue").textContent = r.top_issue || "";
        document.getElementById("vm-tagline").textContent   = r.tagline || "";
        launchViralConfetti();
      }
    } else {
      showToast("⚠️ Could not generate vibe. Try again.");
      document.getElementById("vm-start")?.removeAttribute("hidden");
    }
  } catch {
    document.getElementById("vm-loading")?.setAttribute("hidden", "");
    showToast("Network error. Please try again.");
    document.getElementById("vm-start")?.removeAttribute("hidden");
  }
}

/* ── Leaderboard ─────────────────────────────────────────────────── */
async function loadLeaderboard() {
  const wrap = document.getElementById("leaderboard-list");
  if (!wrap) return;

  try {
    const res = await fetch("/api/leaderboard");
    const data = await res.json();
    if (data.status !== "success") throw new Error();

    wrap.innerHTML = "";
    data.leaderboard.forEach((item, i) => {
      const row = document.createElement("div");
      row.className = "lb-row";
      row.style.animationDelay = `${i * 60}ms`;
      const displayName = (p2.lang !== "en" && item.name_hi) ? item.name_hi : item.name;
      const maxReg = data.leaderboard[0].youth_reg;
      const barPct = Math.round((item.youth_reg / maxReg) * 100);

      row.innerHTML = `
        <span class="lb-emoji" aria-hidden="true">${item.emoji}</span>
        <div class="lb-info">
          <span class="lb-name">${esc(displayName)}</span>
          <div class="lb-bar-wrap" aria-hidden="true">
            <div class="lb-bar" style="width:${barPct}%"></div>
          </div>
        </div>
        <div class="lb-stats">
          <span class="lb-count">${item.youth_reg.toLocaleString("en-IN")}</span>
          <span class="lb-change" style="color:var(--green)">${item.change}</span>
        </div>`;
      wrap.appendChild(row);
    });
  } catch (err) {
    console.error("Leaderboard error:", err);
  }
}

/* ── Squad Pacts ─────────────────────────────────────────────────── */
function initSquad() {
  document.getElementById("squad-create-btn")?.addEventListener("click", createSquad);
  document.getElementById("squad-join-btn")?.addEventListener("click", joinSquad);
  document.getElementById("squad-copy-btn")?.addEventListener("click", () => {
    copyToClip("squad-code-display", "Squad code copied!");
  });

  // Load existing squad from localStorage
  const saved = localStorage.getItem("ew-squad");
  if (saved) {
    try {
      const squad = JSON.parse(saved);
      renderSquad(squad);
    } catch { localStorage.removeItem("ew-squad"); }
  }
}

function createSquad() {
  const nameInput = document.getElementById("squad-name-input");
  const name = nameInput?.value.trim();
  if (!name) { showToast("Enter your name first!"); return; }

  const code = Math.random().toString(36).substring(2, 8).toUpperCase();
  const squad = {
    code,
    members: [{ name, status: "registered", you: true }],
    created: new Date().toISOString(),
  };
  localStorage.setItem("ew-squad", JSON.stringify(squad));
  renderSquad(squad);
}

function joinSquad() {
  const codeInput = document.getElementById("squad-code-input");
  const nameInput = document.getElementById("squad-name-input");
  const code = codeInput?.value.trim().toUpperCase();
  const name = nameInput?.value.trim();
  if (!code) { showToast("Enter a squad code!"); return; }
  if (!name) { showToast("Enter your name!"); return; }

  // In a real app, this would fetch from server. Locally, simulate joining.
  const squad = { code, members: [{ name, status: "registered", you: true }], created: new Date().toISOString() };
  localStorage.setItem("ew-squad", JSON.stringify(squad));
  renderSquad(squad);
}

function renderSquad(squad) {
  document.getElementById("squad-setup")?.setAttribute("hidden", "");
  const active = document.getElementById("squad-active");
  if (!active) return;
  active.removeAttribute("hidden");

  const codeEl = document.getElementById("squad-code-display");
  if (codeEl) codeEl.textContent = squad.code;

  const membersEl = document.getElementById("squad-members");
  if (membersEl) {
    membersEl.innerHTML = squad.members.map(m => `
      <div class="squad-member">
        <span class="member-avatar" aria-hidden="true">👤</span>
        <span class="member-name">${esc(m.name)} ${m.you ? "(you)" : ""}</span>
        <span class="member-status status-${m.status || "registered"}">${statusLabel(m.status)}</span>
      </div>`).join("");
  }

  // Status progression buttons
  document.getElementById("squad-vote-btn")?.addEventListener("click", () => {
    squad.members[0].status = "voted";
    localStorage.setItem("ew-squad", JSON.stringify(squad));
    renderSquad(squad);
    showToast("🎉 Marked as Voted! Your squad is proud.");
    launchViralConfetti();
  });
}

function statusLabel(s) {
  return { registered: "✅ Registered", verified: "🔍 Verified", voted: "🗳️ Voted!" }[s] || "📋 Registered";
}

/* ── I Voted Drip Card ───────────────────────────────────────────── */
function generateIVotedCard() {
  const canvas = document.getElementById("voted-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  canvas.width = 400; canvas.height = 400;

  // Background gradient
  const grad = ctx.createLinearGradient(0, 0, 400, 400);
  grad.addColorStop(0, "#7C3AED");
  grad.addColorStop(0.5, "#EC4899");
  grad.addColorStop(1, "#06B6D4");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 400, 400);

  // Text
  ctx.fillStyle = "#fff";
  ctx.textAlign = "center";
  ctx.font = "bold 72px sans-serif";
  ctx.fillText("🗳️", 200, 160);
  ctx.font = "bold 40px sans-serif";
  ctx.fillText("I VOTED!", 200, 240);
  ctx.font = "20px sans-serif";
  ctx.fillStyle = "rgba(255,255,255,0.8)";
  ctx.fillText("Powered by ElectWise AI", 200, 290);
  ctx.fillText("#MainBhiMatlabRakhta", 200, 320);

  // Convert to download link
  const link = document.getElementById("download-voted-card");
  if (link) {
    link.href = canvas.toDataURL("image/png");
    link.download = "i-voted-electwise.png";
    link.removeAttribute("hidden");
    link.textContent = "⬇️ Download & Share";
  }
  canvas.hidden = false;
}

/* ── Shared Utilities ────────────────────────────────────────────── */
function copyToClip(elId, msg) {
  const el = document.getElementById(elId);
  if (!el) return;
  const text = el.textContent || el.value || "";
  navigator.clipboard.writeText(text).then(() => showToast(msg || "Copied!")).catch(() => showToast("Copy failed"));
}

function showToast(message) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    toast.style.cssText = `position:fixed;bottom:24px;left:50%;transform:translateX(-50%);
      background:rgba(20,20,38,.95);border:1px solid var(--border2);
      color:var(--tx);border-radius:var(--r-pill);padding:10px 20px;
      font-size:.85rem;font-weight:600;z-index:9999;
      animation:fadeUp .3s var(--ease);pointer-events:none;`;
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.opacity = "1";
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => { toast.style.opacity = "0"; }, 2500);
}

function launchViralConfetti() {
  const wrap = document.getElementById("viral-confetti");
  if (!wrap) return;
  wrap.innerHTML = "";
  const colors = ["#7C3AED","#EC4899","#06B6D4","#10B981","#F59E0B","#FF6B35"];
  for (let i = 0; i < 40; i++) {
    const c = document.createElement("div");
    c.className = "confetti-piece";
    c.style.cssText = `left:${Math.random()*100}%;
      background:${colors[Math.floor(Math.random()*colors.length)]};
      animation-delay:${Math.random().toFixed(2)}s;
      animation-duration:${(1.5+Math.random()).toFixed(2)}s;
      width:${6+Math.floor(Math.random()*8)}px;height:${6+Math.floor(Math.random()*8)}px;
      border-radius:${Math.random()>.5?"50%":"2px"};`;
    wrap.appendChild(c);
  }
}

function esc(s) {
  if (typeof s !== "string") return "";
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
           .replace(/"/g,"&quot;").replace(/'/g,"&#x27;");
}

/* ── Bootstrap Phase 2 on DOMContentLoaded ───────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initLanguage();
  initLocalTab();
  initViralTab();

  // Wire "I Voted" card button
  document.getElementById("voted-card-btn")?.addEventListener("click", generateIVotedCard);

  // vmAnswer buttons via delegation
  document.addEventListener("click", e => {
    if (e.target.closest(".vm-agree-btn"))    vmAnswer(true);
    if (e.target.closest(".vm-disagree-btn")) vmAnswer(false);
  });
});
