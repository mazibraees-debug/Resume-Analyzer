const API_BASE = "/api/applications";

const form = document.getElementById("application-form");
const formSection = document.getElementById("form-section");
const statusSection = document.getElementById("status-section");
const statusText = document.getElementById("status-text");
const resultsSection = document.getElementById("results-section");
const errorSection = document.getElementById("error-section");
const errorText = document.getElementById("error-text");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  showOnly(statusSection);
  statusText.textContent = "Analyzing CV and job description with AI agents...";

  const cvFile = document.getElementById("cv_file").files[0];
  const jobTitle = document.getElementById("job_title").value;
  const jobDescription = document.getElementById("job_description").value;

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

    // If server completed synchronously (e.g. on Vercel Serverless)
    if (created.status === "complete") {
      renderResults(created);
      return;
    } else if (created.status === "failed") {
      showError(created.error_message || "The agent pipeline failed.");
      return;
    }

    // Otherwise poll for completion (local dev background tasks)
    pollForResult(created.id);
  } catch (err) {
    showError(err.message);
  }
});

async function pollForResult(id) {
  const messages = [
    "Parsing your CV and job description...",
    "Embedding content and matching skills...",
    "Running the LLM agents (tailored CV, cover letter, interview prep)...",
    "Almost there...",
  ];
  let i = 0;

  const interval = setInterval(async () => {
    statusText.textContent = messages[Math.min(i, messages.length - 1)];
    i++;

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
  }, 2000);
}

function renderResults(data) {
  document.getElementById("score-value").textContent = `${data.match_score}%`;
  document.querySelector(".score-ring").style.setProperty("--pct", `${data.match_score}%`);

  const matchesList = document.getElementById("matches-list");
  matchesList.innerHTML = "";
  (data.skill_matches || []).forEach((m) => {
    const li = document.createElement("li");
    li.textContent = `${m.requirement} (${m.strength})`;
    matchesList.appendChild(li);
  });
  if (!data.skill_matches || data.skill_matches.length === 0) {
    matchesList.innerHTML = "<li>No strong matches found</li>";
  }

  const gapsList = document.getElementById("gaps-list");
  gapsList.innerHTML = "";
  (data.skill_gaps || []).forEach((g) => {
    const li = document.createElement("li");
    li.textContent = g;
    gapsList.appendChild(li);
  });
  if (!data.skill_gaps || data.skill_gaps.length === 0) {
    gapsList.innerHTML = "<li>No significant gaps 🎉</li>";
  }

  const cv = data.tailored_cv_sections || {};
  const tailoredDiv = document.getElementById("tailored-cv");
  tailoredDiv.innerHTML = `
    <p><strong>Summary:</strong> ${escapeHtml(cv.professional_summary || "")}</p>
    <p><strong>Highlighted skills:</strong> ${(cv.highlighted_skills || []).map(escapeHtml).join(", ")}</p>
    <p><strong>Rewritten bullets:</strong></p>
    <ul>${(cv.experience_bullets || []).map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>
    ${cv.notes_for_candidate ? `<p><em>${escapeHtml(cv.notes_for_candidate)}</em></p>` : ""}
  `;

  document.getElementById("cover-letter").textContent = data.cover_letter || "";

  const qDiv = document.getElementById("interview-questions");
  qDiv.innerHTML = (data.interview_questions || [])
    .map(
      (q) => `
      <div class="question-item">
        <div class="cat">${escapeHtml(q.category || "")}</div>
        <div class="q">${escapeHtml(q.question || "")}</div>
        <div class="tp">${escapeHtml(q.talking_points || "")}</div>
      </div>`
    )
    .join("");

  showOnly(resultsSection);
}

function showError(message) {
  errorText.textContent = message;
  showOnly(errorSection);
}

function showOnly(section) {
  [formSection, statusSection, resultsSection, errorSection].forEach((s) =>
    s.classList.add("hidden")
  );
  section.classList.remove("hidden");
}

document.getElementById("reset-btn").addEventListener("click", () => {
  form.reset();
  showOnly(formSection);
});

document.getElementById("error-reset-btn").addEventListener("click", () => {
  showOnly(formSection);
});

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
