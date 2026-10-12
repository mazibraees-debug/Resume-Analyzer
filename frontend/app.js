// ============================================================
//  NeuralApply — Premium Frontend Logic
// ============================================================

const API_BASE = "/api/applications";

// ---- DOM References ----
const form           = document.getElementById("application-form");
const formSection    = document.getElementById("form-section");
const statusSection  = document.getElementById("status-section");
const statusText     = document.getElementById("status-text");
const resultsSection = document.getElementById("results-section");
const errorSection   = document.getElementById("error-section");
const errorText      = document.getElementById("error-text");
const dropZone       = document.getElementById("drop-zone");
const dropClickable  = document.getElementById("drop-clickable");
const dropLabel      = document.getElementById("drop-label");
const cvFileInput    = document.getElementById("cv_file");

// ============================================================
//  ANIMATED PARTICLE CANVAS BACKGROUND
// ============================================================
(function initCanvas() {
  const canvas = document.getElementById("bg-canvas");
  const ctx = canvas.getContext("2d");

  let W, H, nodes;

  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function createNodes(count) {
    return Array.from({ length: count }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      r: Math.random() * 2 + 1,
      opacity: Math.random() * 0.5 + 0.2,
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);

    // Connections
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 160) {
          const alpha = (1 - dist / 160) * 0.15;
          ctx.strokeStyle = `rgba(108,140,255,${alpha})`;
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.stroke();
        }
      }
    }

    // Nodes
    nodes.forEach(n => {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(108,140,255,${n.opacity})`;
      ctx.fill();

      n.x += n.vx;
      n.y += n.vy;
      if (n.x < 0 || n.x > W) n.vx *= -1;
      if (n.y < 0 || n.y > H) n.vy *= -1;
    });

    requestAnimationFrame(draw);
  }

  resize();
  nodes = createNodes(70);
  draw();
  window.addEventListener("resize", () => {
    resize();
    nodes = createNodes(70);
  });
})();

// ============================================================
//  DROP ZONE — Drag & Drop + Click
// ============================================================
dropClickable.addEventListener("click", () => cvFileInput.click());

cvFileInput.addEventListener("change", () => {
  const file = cvFileInput.files[0];
  if (file) {
    dropLabel.innerHTML = `<strong style="color:var(--accent-2)">&#10003; ${escapeHtml(file.name)}</strong>`;
    dropZone.style.borderColor = "var(--accent-2)";
    dropZone.style.background = "rgba(56,211,159,0.05)";
  }
});

dropZone.addEventListener("dragover", e => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) {
    cvFileInput.files = e.dataTransfer.files;
    dropLabel.innerHTML = `<strong style="color:var(--accent-2)">&#10003; ${escapeHtml(file.name)}</strong>`;
    dropZone.style.borderColor = "var(--accent-2)";
    dropZone.style.background = "rgba(56,211,159,0.05)";
  }
});

// ============================================================
//  FORM SUBMIT
// ============================================================
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const cvFile        = cvFileInput.files[0];
  const jobTitle      = document.getElementById("job_title").value.trim();
  const jobDescription = document.getElementById("job_description").value.trim();

  if (!cvFile) { showError("Please select a CV file."); return; }
  if (!jobDescription) { showError("Please paste a job description."); return; }

  showOnly(statusSection);
  updateStatusStep(1, "Uploading your CV and job description...");

  const fd = new FormData();
  fd.append("cv_file", cvFile);
  fd.append("job_title", jobTitle);
  fd.append("job_description", jobDescription);

  try {
    const res = await fetch(API_BASE, { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to submit application.");
    }
    const created = await res.json();
    pollForResult(created.id);
  } catch (err) {
    showError(err.message);
  }
});

// ============================================================
//  POLLING
// ============================================================
function pollForResult(id) {
  const steps = [
    [1, "Parsing your CV and extracting text..."],
    [2, "Embedding content with Sentence-Transformers..."],
    [3, "Running the AI Matching Agent..."],
    [4, "Generating tailored CV, cover letter & interview prep..."],
  ];
  let stepIdx = 0;

  updateStatusStep(steps[0][0], steps[0][1]);

  const interval = setInterval(async () => {
    stepIdx = Math.min(stepIdx + 1, steps.length - 1);
    const [step, msg] = steps[stepIdx];
    updateStatusStep(step, msg);

    try {
      const res = await fetch(`${API_BASE}/${id}`);
      if (!res.ok) throw new Error("Could not fetch application status.");
      const data = await res.json();

      if (data.status === "complete") {
        clearInterval(interval);
        renderResults(data);
      } else if (data.status === "failed") {
        clearInterval(interval);
        showError(data.error_message || "The agent pipeline failed.");
      }
    } catch (err) {
      clearInterval(interval);
      showError(err.message);
    }
  }, 3000);
}

function updateStatusStep(activeStep, message) {
  statusText.textContent = message;
  for (let i = 1; i <= 4; i++) {
    const dot = document.querySelector(`#step-${i} .step-dot`);
    if (!dot) continue;
    if (i < activeStep) {
      dot.classList.add("done");
      dot.classList.remove("active");
    } else if (i === activeStep) {
      dot.classList.add("active");
      dot.classList.remove("done");
    } else {
      dot.classList.remove("active", "done");
    }
  }
}

// ============================================================
//  RENDER RESULTS
// ============================================================
function renderResults(data) {
  // --- Score Ring ---
  const score = data.match_score || 0;
  document.getElementById("score-value").textContent = `${score}%`;

  // Animate SVG ring: circumference = 2πr = 2π×50 ≈ 314
  const circumference = 314;
  const offset = circumference - (score / 100) * circumference;

  // Inject gradient def into SVG
  const svg = document.querySelector(".score-ring-svg");
  if (!svg.querySelector("defs")) {
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    defs.innerHTML = `
      <linearGradient id="score-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#6C8CFF"/>
        <stop offset="100%" stop-color="#38D39F"/>
      </linearGradient>`;
    svg.prepend(defs);
    svg.querySelector("defs").style.display = "block";
  }

  // Animate after brief delay
  setTimeout(() => {
    document.getElementById("score-ring-fill").style.strokeDashoffset = offset;
  }, 150);

  // --- Count badges ---
  const matchCount = (data.skill_matches || []).length;
  const gapCount   = (data.skill_gaps || []).length;
  document.getElementById("match-count-badge").textContent = `${matchCount} Strong Match${matchCount !== 1 ? "es" : ""}`;
  document.getElementById("gap-count-badge").textContent   = `${gapCount} Gap${gapCount !== 1 ? "s" : ""} Identified`;

  // --- Skill Matches ---
  const matchesList = document.getElementById("matches-list");
  matchesList.innerHTML = "";
  if (!matchCount) {
    matchesList.innerHTML = `<li style="color:var(--muted)">No strong matches found</li>`;
  } else {
    data.skill_matches.forEach(m => {
      const li = document.createElement("li");
      const strength = m.strength || "partial";
      li.innerHTML = `
        <span style="flex:1">${escapeHtml(m.requirement)}</span>
        <span class="strength-badge strength-${strength}">${strength}</span>`;
      matchesList.appendChild(li);
    });
  }

  // --- Skill Gaps ---
  const gapsList = document.getElementById("gaps-list");
  gapsList.innerHTML = "";
  if (!gapCount) {
    gapsList.innerHTML = `<li style="color:var(--accent-2)">No significant gaps — great fit! &#127881;</li>`;
  } else {
    data.skill_gaps.forEach(g => {
      const li = document.createElement("li");
      li.innerHTML = `<span style="flex:1">${escapeHtml(g)}</span>`;
      gapsList.appendChild(li);
    });
  }

  // --- Tailored CV ---
  const cv = data.tailored_cv_sections || {};
  const tailoredDiv = document.getElementById("tailored-cv");
  tailoredDiv.innerHTML = "";

  if (cv.professional_summary) {
    tailoredDiv.insertAdjacentHTML("beforeend", `
      <div class="cv-section">
        <div class="cv-section-label">Professional Summary</div>
        <div class="cv-section-content">${escapeHtml(cv.professional_summary)}</div>
      </div>`);
  }

  if (cv.highlighted_skills && cv.highlighted_skills.length) {
    const chips = cv.highlighted_skills.map(s => `<span class="skill-chip">${escapeHtml(s)}</span>`).join("");
    tailoredDiv.insertAdjacentHTML("beforeend", `
      <div class="cv-section">
        <div class="cv-section-label">Highlighted Skills</div>
        <div class="skill-chips">${chips}</div>
      </div>`);
  }

  if (cv.experience_bullets && cv.experience_bullets.length) {
    const bullets = cv.experience_bullets.map(b => `<li>${escapeHtml(b)}</li>`).join("");
    tailoredDiv.insertAdjacentHTML("beforeend", `
      <div class="cv-section">
        <div class="cv-section-label">Experience Bullets</div>
        <ul class="cv-bullets">${bullets}</ul>
      </div>`);
  }

  if (cv.notes_for_candidate) {
    tailoredDiv.insertAdjacentHTML("beforeend", `
      <div class="cv-section" style="border-color:rgba(108,140,255,0.2); background:rgba(108,140,255,0.04)">
        <div class="cv-section-label" style="color:var(--accent)">AI Notes for You</div>
        <div class="cv-section-content" style="color:var(--muted)">${escapeHtml(cv.notes_for_candidate)}</div>
      </div>`);
  }

  if (!tailoredDiv.innerHTML) {
    tailoredDiv.innerHTML = `<p style="color:var(--muted)">No tailored CV sections generated.</p>`;
  }

  // --- Cover Letter ---
  document.getElementById("cover-letter").textContent = data.cover_letter || "(No cover letter generated)";

  // Copy button
  document.getElementById("copy-cover-btn").addEventListener("click", () => {
    navigator.clipboard.writeText(data.cover_letter || "").then(() => {
      const btn = document.getElementById("copy-cover-btn");
      btn.style.color = "var(--accent-2)";
      btn.title = "Copied!";
      setTimeout(() => { btn.style.color = ""; btn.title = "Copy to clipboard"; }, 2000);
    });
  });

  // --- Interview Prep ---
  const qDiv = document.getElementById("interview-questions");
  const questions = Array.isArray(data.interview_questions) ? data.interview_questions : [];

  if (!questions.length) {
    qDiv.innerHTML = `<p style="color:var(--muted)">No interview questions generated.</p>`;
  } else {
    qDiv.innerHTML = questions.map(q => `
      <div class="question-item">
        <div class="q-category">${escapeHtml(q.category || "General")}</div>
        <div class="q-text">${escapeHtml(q.question || "")}</div>
        <div class="q-tips">${escapeHtml(q.talking_points || "")}</div>
      </div>`).join("");
  }

  showOnly(resultsSection);

  // Smooth scroll to results
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ============================================================
//  HELPERS
// ============================================================
function showError(message) {
  errorText.textContent = message;
  showOnly(errorSection);
}

function showOnly(section) {
  [formSection, statusSection, resultsSection, errorSection].forEach(s =>
    s.classList.add("hidden")
  );
  section.classList.remove("hidden");
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ---- Reset Buttons ----
document.getElementById("reset-btn").addEventListener("click", resetApp);
document.getElementById("error-reset-btn").addEventListener("click", resetApp);

function resetApp() {
  form.reset();
  cvFileInput.value = "";
  dropLabel.innerHTML = `Drop your CV here or <span class="link-text">browse</span>`;
  dropZone.style.borderColor = "";
  dropZone.style.background = "";
  showOnly(formSection);
}
