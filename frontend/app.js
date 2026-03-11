const resumeFile = document.getElementById("resumeFile");
const parseBtn = document.getElementById("parseBtn");
const dropzoneLabel = document.querySelector(".dropzone span");
const statusMessage = document.getElementById("statusMessage");
const resultCard = document.getElementById("resultCard");
const resultName = document.getElementById("resultName");
const resultEmail = document.getElementById("resultEmail");
const resultPhone = document.getElementById("resultPhone");
const resultSkills = document.getElementById("resultSkills");
const resultMeta = document.getElementById("resultMeta");
const historyList = document.getElementById("historyList");
const historyStatus = document.getElementById("historyStatus");
const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
const historyNameFilter = document.getElementById("historyNameFilter");
const historySkillFilter = document.getElementById("historySkillFilter");
const historySortOrder = document.getElementById("historySortOrder");
const historyDateFrom = document.getElementById("historyDateFrom");
const historyDateTo = document.getElementById("historyDateTo");
const revealItems = document.querySelectorAll(".reveal");

const API_BASE_URL = "";
let allHistoryItems = [];
let filteredHistoryItems = [];

function setStatus(text, type = "") {
  if (!statusMessage) {
    return;
  }

  statusMessage.textContent = text;
  statusMessage.className = "status-message";

  if (type) {
    statusMessage.classList.add(type);
  }
}

function renderResult(data, meta = {}) {
  if (!resultCard) {
    return;
  }

  resultName.textContent = data.name || "Not found";
  resultEmail.textContent = data.email || "Not found";
  resultPhone.textContent = data.phone || "Not found";
  resultSkills.textContent = Array.isArray(data.skills) && data.skills.length
    ? data.skills.join(", ")
    : "Not found";

  if (resultMeta) {
    const quality = (meta.quality || "unknown").toString().toUpperCase();
    const confidence = Number.isFinite(meta.confidence) ? `${meta.confidence}%` : "N/A";
    const ocr = meta.ocr_used ? "Used" : (meta.ocr_attempted ? "Attempted" : "Not used");
    const missingFields = Array.isArray(meta.missing_fields) ? meta.missing_fields : [];
    const filteredWarnings = Array.isArray(meta.warnings)
      ? meta.warnings.filter((warning) => {
        if (!warning.includes("OCR fallback attempted but no OCR text was recovered")) {
          return true;
        }

        return missingFields.includes("email") || missingFields.includes("phone");
      })
      : [];
    const warnings = filteredWarnings.length
      ? ` • Warning: ${filteredWarnings.join("; ")}`
      : "";
    resultMeta.textContent = `Quality: ${quality} • Confidence: ${confidence} • OCR: ${ocr}${warnings}`;
    resultMeta.hidden = false;
  }

  resultCard.hidden = false;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(isoValue) {
  if (!isoValue) {
    return "Unknown date";
  }

  const value = new Date(isoValue);
  if (Number.isNaN(value.getTime())) {
    return "Unknown date";
  }

  return value.toLocaleString();
}

function renderHistory(items, options = {}) {
  if (!historyList) {
    return;
  }

  const { filteredOut = false } = options;

  if (!Array.isArray(items) || items.length === 0) {
    historyList.innerHTML = filteredOut
      ? `<div class="history-empty">No candidates match current filters. Clear filters or click Refresh.</div>`
      : `<div class="history-empty">No candidates yet. Parse a resume to see history here.</div>`;
    return;
  }

  historyList.innerHTML = items
    .map((item) => {
      const skills = Array.isArray(item.skills) ? item.skills : [];
      const chips = skills.length
        ? skills.map((skill) => `<span class="chip">${escapeHtml(skill)}</span>`).join("")
        : `<span class="chip">No skills found</span>`;

      return `
        <article class="history-item">
          <h4>${escapeHtml(item.name || "Unknown Candidate")}</h4>
          <p><strong>Email:</strong> ${escapeHtml(item.email || "Not found")}</p>
          <p><strong>Phone:</strong> ${escapeHtml(item.phone || "Not found")}</p>
          <p><strong>Parsed:</strong> ${escapeHtml(formatDate(item.created_at))}</p>
          <div class="chips">${chips}</div>
        </article>
      `;
    })
    .join("");
}

function updateSkillFilterOptions(items) {
  if (!historySkillFilter) {
    return;
  }

  const previousValue = historySkillFilter.value;
  const uniqueSkills = new Set();

  items.forEach((item) => {
    const skills = Array.isArray(item.skills) ? item.skills : [];
    skills.forEach((skill) => {
      if (skill) {
        uniqueSkills.add(skill.trim());
      }
    });
  });

  const options = ["<option value=\"\">All skills</option>"];
  Array.from(uniqueSkills)
    .sort((a, b) => a.localeCompare(b))
    .forEach((skill) => {
      options.push(`<option value="${escapeHtml(skill)}">${escapeHtml(skill)}</option>`);
    });

  historySkillFilter.innerHTML = options.join("");

  if (previousValue && uniqueSkills.has(previousValue)) {
    historySkillFilter.value = previousValue;
  }
}

function applyHistoryFilters(resetPage = true) {
  const nameQuery = (historyNameFilter?.value || "").trim().toLowerCase();
  const skillQuery = historySkillFilter?.value || "";
  const sortQuery = historySortOrder?.value || "newest";
  const fromQuery = historyDateFrom?.value || "";
  const toQuery = historyDateTo?.value || "";

  const fromDate = fromQuery ? new Date(`${fromQuery}T00:00:00`) : null;
  const toDate = toQuery ? new Date(`${toQuery}T23:59:59.999`) : null;

  const filtered = allHistoryItems.filter((item) => {
    const name = (item.name || "").toLowerCase();
    const email = (item.email || "").toLowerCase();
    const skills = Array.isArray(item.skills) ? item.skills : [];
    const parsedDate = item.created_at ? new Date(item.created_at) : null;

    const matchesName = !nameQuery || name.includes(nameQuery) || email.includes(nameQuery);
    const matchesSkill = !skillQuery || skills.some((skill) => skill === skillQuery);
    const matchesFrom = !fromDate || (parsedDate && parsedDate >= fromDate);
    const matchesTo = !toDate || (parsedDate && parsedDate <= toDate);

    return matchesName && matchesSkill && matchesFrom && matchesTo;
  });

  filtered.sort((a, b) => {
    const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;

    return sortQuery === "oldest" ? dateA - dateB : dateB - dateA;
  });

  filteredHistoryItems = filtered;
  renderHistory(filteredHistoryItems, { filteredOut: filteredHistoryItems.length === 0 && allHistoryItems.length > 0 });

  if (historyStatus) {
    historyStatus.textContent = `Showing ${filteredHistoryItems.length} of ${allHistoryItems.length} candidates.`;
  }
}

async function loadHistory() {
  if (!historyStatus) {
    return;
  }

  historyStatus.textContent = "Loading recent candidates...";

  try {
    const response = await fetch(`${API_BASE_URL}/candidates?limit=100&_ts=${Date.now()}`, {
      cache: "no-store",
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Unable to load candidate history.");
    }

    allHistoryItems = Array.isArray(payload.items) ? payload.items : [];
    updateSkillFilterOptions(allHistoryItems);
    applyHistoryFilters(true);

    if (payload.warning && historyStatus) {
      historyStatus.textContent += ` ${payload.warning}`;
    }
  } catch (error) {
    allHistoryItems = [];
    filteredHistoryItems = [];
    historyStatus.textContent = error.message || "Unable to load candidate history.";
    renderHistory([]);
  }
}

if (resumeFile && dropzoneLabel) {
  resumeFile.addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    dropzoneLabel.textContent = file ? file.name : "Click to choose file";

    if (!file && resultCard) {
      resultCard.hidden = true;
    }

    setStatus("");
  });
}

if (parseBtn && resumeFile) {
  parseBtn.addEventListener("click", async () => {
    const file = resumeFile.files?.[0];

    if (!file) {
      setStatus("Please select a resume file first.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    parseBtn.disabled = true;
    parseBtn.textContent = "Parsing...";
    setStatus("Parsing resume, please wait...", "loading");

    if (resultCard) {
      resultCard.hidden = true;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/parse-resume`, {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.error || "Unable to parse resume.");
      }

      renderResult(payload.data || {}, payload.meta || payload.data?.meta || {});

      setStatus("Resume parsed successfully.", "success");
      await loadHistory();

    } catch (error) {
      setStatus(error.message || "Something went wrong.", "error");
    } finally {
      parseBtn.disabled = false;
      parseBtn.textContent = "Parse Resume";
    }
  });
}

if (refreshHistoryBtn) {
  refreshHistoryBtn.addEventListener("click", async () => {
    const originalLabel = refreshHistoryBtn.textContent;
    refreshHistoryBtn.disabled = true;
    refreshHistoryBtn.textContent = "Refreshing...";

    try {
      if (historyNameFilter) {
        historyNameFilter.value = "";
      }

      if (historySkillFilter) {
        historySkillFilter.value = "";
      }

      if (historyDateFrom) {
        historyDateFrom.value = "";
      }

      if (historyDateTo) {
        historyDateTo.value = "";
      }

      if (historySortOrder) {
        historySortOrder.value = "newest";
      }

      await loadHistory();
      if (historyStatus) {
        historyStatus.textContent += ` Refreshed at ${new Date().toLocaleTimeString()}.`;
      }
    } finally {
      refreshHistoryBtn.disabled = false;
      refreshHistoryBtn.textContent = originalLabel;
    }
  });
}

if (historyNameFilter) {
  historyNameFilter.addEventListener("input", () => {
    applyHistoryFilters(true);
  });
}

if (historySkillFilter) {
  historySkillFilter.addEventListener("change", () => {
    applyHistoryFilters(true);
  });
}

if (historySortOrder) {
  historySortOrder.addEventListener("change", () => {
    applyHistoryFilters(true);
  });
}

if (historyDateFrom) {
  historyDateFrom.addEventListener("change", () => {
    applyHistoryFilters(true);
  });
}

if (historyDateTo) {
  historyDateTo.addEventListener("change", () => {
    applyHistoryFilters(true);
  });
}

loadHistory();

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
      }
    });
  },
  { threshold: 0.15 }
);

revealItems.forEach((item) => observer.observe(item));
