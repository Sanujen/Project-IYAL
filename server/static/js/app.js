// Project IYAL Public Normalizer Application Logic

let supportedEncodings = [];
let userProtectedWords = JSON.parse(localStorage.getItem("iyal_protected_words") || '["Moratuwa", "IYAL"]');
let lastAnalysisResponse = null;
let lastConfirmedText = null;
let lastConfirmedEncoding = null;

document.addEventListener("DOMContentLoaded", async () => {
  renderProtectedWordChips();
  await Promise.all([
    loadPublicConfig(),
    loadEncodings(),
    syncServerProtectedWords(),
  ]);
});

async function loadPublicConfig() {
  try {
    const res = await fetch("/api/v1/public-config");
    if (res.ok) {
      const cfg = await res.json();
      if (cfg.researchgate_paper_url) {
        const navBtn = document.getElementById("researchgate-btn");
        const guideBtn = document.getElementById("researchgate-guide-btn");
        if (navBtn) navBtn.href = cfg.researchgate_paper_url;
        if (guideBtn) guideBtn.href = cfg.researchgate_paper_url;
      }
      if (cfg.github_repo_url) {
        const ghNavBtn = document.getElementById("github-btn");
        const ghGuideBtn = document.getElementById("github-guide-btn");
        if (ghNavBtn) ghNavBtn.href = cfg.github_repo_url;
        if (ghGuideBtn) ghGuideBtn.href = cfg.github_repo_url;
      }
    }
  } catch (err) {
    console.warn("Could not load public config:", err);
  }
}

function showAlert(message, type = "info") {
  const el = document.getElementById("global-alert");
  el.className = `alert alert-${type}`;
  el.textContent = message;
  el.style.display = "block";
  setTimeout(() => {
    el.style.display = "none";
  }, 6000);
}

function switchTab(tabId, btn) {
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  document.getElementById(tabId).classList.add("active");
  btn.classList.add("active");
}

function updateCharCount() {
  const txt = document.getElementById("input-text").value || "";
  document.getElementById("char-count").textContent = `${txt.length.toLocaleString()} / 15,000 characters`;
  if (txt.trim() !== lastConfirmedText) {
    lastConfirmedText = null;
    lastConfirmedEncoding = null;
  }
}

function loadSample(type) {
  const box = document.getElementById("input-text");
  dismissConfirmBanner();
  lastConfirmedText = null;
  lastConfirmedEncoding = null;

  if (type === "mixed") {
    box.value = "Kaalai வணkkam உலகம் cyfk;! Good morning from Moratuwa.";
    document.getElementById("need-translation").checked = true;
    document.getElementById("colloquial-to-standard").checked = false;
  } else if (type === "english") {
    box.value = "Vanakkam! I am translating English words for students in Moratuwa.";
    document.getElementById("need-translation").checked = true;
    document.getElementById("colloquial-to-standard").checked = false;
  } else if (type === "bamini") {
    box.value = "jkpo; nkhopapd; ,dpikAk; njhd;ikAk; cyfk; Nghw;Wk;.";
    document.getElementById("need-translation").checked = false;
    document.getElementById("colloquial-to-standard").checked = false;
  } else if (type === "colloquial") {
    box.value = "என்ன பண்றீங்க எல்லாரும் நல்லா இருக்கீங்களா.";
    document.getElementById("need-translation").checked = false;
    document.getElementById("colloquial-to-standard").checked = true;
  }
  updateCharCount();
}

function clearInput() {
  document.getElementById("input-text").value = "";
  lastConfirmedText = null;
  lastConfirmedEncoding = null;
  updateCharCount();
  dismissConfirmBanner();
}

async function onPostProcessingOptionChange() {
  const inputText = (document.getElementById("input-text").value || "").trim();
  if (!inputText) return;

  // If the confirmation banner is currently open, confirm & run immediately with the new checkbox option
  const banner = document.getElementById("legacy-confirm-banner");
  if (banner && banner.style.display !== "none") {
    await confirmAndProceedAnalysis();
    return;
  }

  // If the user has already analyzed this text, re-run automatically when toggling Step 10 or Step 11
  if (lastAnalysisResponse && lastAnalysisResponse.input_text === inputText) {
    const enc = lastConfirmedEncoding || lastAnalysisResponse.encoding_used || "legacy_font_not_found";
    await executeFullAnalysis(enc);
  }
}

async function loadEncodings() {
  try {
    const res = await fetch("/api/v1/encodings");
    const data = await res.json();
    supportedEncodings = data.encodings || [];

    const manualSel = document.getElementById("manual-encoding-select");
    const confirmSel = document.getElementById("confirm-encoding-select");
    const directSel = document.getElementById("legacy-direct-encoding");

    manualSel.innerHTML = "";
    confirmSel.innerHTML = "";

    supportedEncodings.forEach((enc) => {
      manualSel.innerHTML += `<option value="${enc}">${enc}</option>`;
      confirmSel.innerHTML += `<option value="${enc}">${enc}</option>`;
      directSel.innerHTML += `<option value="${enc}">${enc}</option>`;
    });
  } catch (err) {
    console.error("Failed to load encodings:", err);
  }
}

async function syncServerProtectedWords() {
  try {
    const res = await fetch("/api/v1/protected-words");
    if (res.ok) {
      const data = await res.json();
      const serverWords = (data.words || []).map((w) => w.word);
      serverWords.forEach((sw) => {
        if (!userProtectedWords.some((uw) => uw.toLowerCase() === sw.toLowerCase())) {
          userProtectedWords.push(sw);
        }
      });
      saveProtectedWords();
      renderProtectedWordChips();
    }
  } catch (e) {
    console.warn("Could not fetch global protected words:", e);
  }
}

function saveProtectedWords() {
  localStorage.setItem("iyal_protected_words", JSON.stringify(userProtectedWords));
}

function renderProtectedWordChips() {
  const container = document.getElementById("protected-words-chips");
  if (!userProtectedWords.length) {
    container.innerHTML = `<span style="font-size:0.8rem; color:var(--text-muted);">No custom protected words added yet.</span>`;
    return;
  }
  container.innerHTML = userProtectedWords
    .map(
      (w, idx) => `
      <span class="chip">
        🛡️ ${escapeHtml(w)}
        <button type="button" title="Remove word" onclick="removeProtectedWord(${idx})">×</button>
      </span>
    `
    )
    .join("");
}

async function addProtectedWord() {
  const inp = document.getElementById("protected-word-input");
  const val = (inp.value || "").trim();
  if (!val) return;
  if (val.includes(" ")) {
    showAlert("Please enter a single word without spaces for the protected corpus.", "warning");
    return;
  }
  if (!userProtectedWords.some((w) => w.toLowerCase() === val.toLowerCase())) {
    userProtectedWords.push(val);
    saveProtectedWords();
    renderProtectedWordChips();
    try {
      await fetch("/api/v1/protected-words", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word: val, skip_translation: true }),
      });
    } catch (e) {
      // Ignore network error; saved in session
    }
  }
  inp.value = "";
}

function removeProtectedWord(idx) {
  userProtectedWords.splice(idx, 1);
  saveProtectedWords();
  renderProtectedWordChips();
}

function toggleFontMode() {
  const mode = document.querySelector('input[name="font-mode"]:checked').value;
  document.getElementById("manual-encoding-wrap").style.display = mode === "manual" ? "block" : "none";
  dismissConfirmBanner();
}

function dismissConfirmBanner() {
  document.getElementById("legacy-confirm-banner").style.display = "none";
}

async function handleFileUpload(input) {
  const file = input.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);

  try {
    showAlert(`Extracting text from '${file.name}'...`, "info");
    const res = await fetch("/api/v1/upload-extract", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      showAlert(data.detail || "File extraction failed.", "danger");
      return;
    }
    document.getElementById("input-text").value = data.text;
    updateCharCount();
    showAlert(data.message || "File uploaded and extracted!", "success");
  } catch (err) {
    showAlert(`Upload error: ${err.message}`, "danger");
  } finally {
    input.value = "";
  }
}

async function startAnalyzeFlow() {
  const inputText = (document.getElementById("input-text").value || "").trim();
  if (!inputText) {
    showAlert("Please enter or upload some text to analyze.", "warning");
    return;
  }

  const fontMode = document.querySelector('input[name="font-mode"]:checked').value;
  const btn = document.getElementById("analyze-btn");

  if (fontMode === "manual") {
    const selectedEnc = document.getElementById("manual-encoding-select").value;
    await executeFullAnalysis(selectedEnc);
    return;
  }

  // If the Step 7 confirmation banner is already open, or user already confirmed font for this exact text, proceed directly
  const banner = document.getElementById("legacy-confirm-banner");
  if (banner && banner.style.display !== "none") {
    await confirmAndProceedAnalysis();
    return;
  }
  if (lastConfirmedText === inputText && lastConfirmedEncoding) {
    await executeFullAnalysis(lastConfirmedEncoding);
    return;
  }

  // Step 6 & 7: Auto-detect Legacy Font and show confirmation banner if Legacy Font is found
  btn.disabled = true;
  btn.textContent = "🔍 Detecting Encodings...";
  try {
    const res = await fetch("/api/v1/detect-encoding", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_text: inputText,
        protected_words: userProtectedWords,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      showAlert(data.detail || "Error detecting encoding.", "danger");
      return;
    }

    if (data.requires_confirmation && data.encoding && data.encoding !== "legacy_font_not_found") {
      // Show Step 7 Confirmation Banner
      document.getElementById("detected-font-label").textContent = data.encoding;
      const confirmSel = document.getElementById("confirm-encoding-select");
      if (supportedEncodings.includes(data.encoding)) {
        confirmSel.value = data.encoding;
      }
      const previewsContainer = document.getElementById("legacy-sample-previews");
      previewsContainer.innerHTML = (data.legacy_samples || [])
        .map(
          (s) => `
          <span class="sample-pill">
            <code>${escapeHtml(s.word)}</code> → <strong>${escapeHtml(s.preview_unicode)}</strong>
          </span>
        `
        )
        .join("");
      document.getElementById("legacy-confirm-banner").style.display = "block";
    } else {
      // No legacy font found — proceed immediately
      dismissConfirmBanner();
      lastConfirmedText = inputText;
      lastConfirmedEncoding = "legacy_font_not_found";
      await executeFullAnalysis("legacy_font_not_found");
    }
  } catch (err) {
    showAlert(`Error: ${err.message}`, "danger");
  } finally {
    btn.disabled = false;
    btn.textContent = "🚀 Analyze & Normalize Paragraph";
  }
}

async function confirmAndProceedAnalysis() {
  const inputText = (document.getElementById("input-text").value || "").trim();
  const confirmedEncoding = document.getElementById("confirm-encoding-select").value;
  lastConfirmedText = inputText;
  lastConfirmedEncoding = confirmedEncoding;
  dismissConfirmBanner();
  await executeFullAnalysis(confirmedEncoding);
}

async function executeFullAnalysis(encodingToUse) {
  const inputText = (document.getElementById("input-text").value || "").trim();
  const needTranslation = document.getElementById("need-translation").checked;
  const collToStandard = document.getElementById("colloquial-to-standard").checked;
  const btn = document.getElementById("analyze-btn");

  btn.disabled = true;
  btn.textContent = "⚙️ Running 11-Step Normalization Pipeline...";
  try {
    const res = await fetch("/api/v1/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_text: inputText,
        encoding: encodingToUse,
        need_translation: needTranslation,
        colloquial_to_standard: collToStandard,
        protected_words: userProtectedWords,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      showAlert(data.detail || "Normalization failed.", "danger");
      return;
    }

    lastAnalysisResponse = {
      input_text: inputText,
      ...data,
    };

    document.getElementById("normalized-output").textContent = data.output || "";
    const latBadge = document.getElementById("latency-badge");
    if (data.metrics) {
      latBadge.textContent = `${data.metrics.words_count} words • ${data.metrics.latency_ms} ms`;
      latBadge.style.display = "inline-flex";
    }

    renderBreakdown(data.result || [], collToStandard);
  } catch (err) {
    showAlert(`Request failed: ${err.message}`, "danger");
  } finally {
    btn.disabled = false;
    btn.textContent = "🚀 Analyze & Normalize Paragraph";
  }
}

function getBadgeClass(inputType) {
  if (inputType === "raw_tamil") return "badge-raw_tamil";
  if (inputType === "en_tamil") return "badge-en_tamil";
  if (inputType === "Romanized Text Encoding") return "badge-Romanized";
  if (inputType === "Legacy Font Encoding") return "badge-Legacy";
  if (inputType === "protected_en") return "badge-protected_en";
  if (inputType === "en_translated") return "badge-en_translated";
  if (inputType === "en") return "badge-en";
  return "badge-special_case";
}

function formatInputTypeLabel(inputType) {
  const map = {
    raw_tamil: "Raw Tamil",
    en_tamil: "Tamil+English",
    "Romanized Text Encoding": "Romanized Tanglish",
    "Legacy Font Encoding": "Legacy Font",
    en: "English Corpus",
    protected_en: "Protected Word",
    en_translated: "Translated English",
    special_case: "Special Case",
    numeric: "Numeric",
    en_numeric: "Alphanumeric",
  };
  return map[inputType] || inputType;
}

function renderBreakdown(sentenceResults, collToStandard) {
  const container = document.getElementById("breakdown-container");
  if (!sentenceResults.length) {
    container.innerHTML = "<p>No sentences found.</p>";
    return;
  }

  container.innerHTML = sentenceResults
    .map(
      (sent, idx) => `
      <div style="border:1px solid var(--border-color); border-radius:10px; padding:0.9rem; margin-bottom:0.85rem;">
        <div style="font-size:0.82rem; font-weight:700; color:var(--text-muted); margin-bottom:0.35rem;">
          SENTENCE #${idx + 1}
        </div>
        <div style="font-size:0.88rem; margin-bottom:0.3rem;">
          <strong>Input:</strong> ${escapeHtml(sent.input_sentence)}
        </div>
        ${
          collToStandard && sent.pre_standardized_sentence !== sent.output_sentence
            ? `<div style="font-size:0.88rem; margin-bottom:0.3rem; color:var(--purple);">
                 <strong>Pre-Standardized Tamil:</strong> ${escapeHtml(sent.pre_standardized_sentence)}
               </div>`
            : ""
        }
        <div style="font-size:0.92rem; margin-bottom:0.55rem; color:var(--success);">
          <strong>Final Tamil Output:</strong> ${escapeHtml(sent.output_sentence)}
        </div>
        <div class="token-grid">
          ${(sent.results || [])
            .map(
              (tok) => `
              <div class="token-card">
                <span class="badge ${getBadgeClass(tok.inputType)}">${escapeHtml(formatInputTypeLabel(tok.inputType))}</span>
                <span><code>${escapeHtml(tok.inputWord)}</code> → <strong>${escapeHtml(tok.output)}</strong></span>
              </div>
            `
            )
            .join("")}
        </div>
      </div>
    `
    )
    .join("");
}

async function runDirectLegacyConvert() {
  const txt = (document.getElementById("legacy-direct-input").value || "").trim();
  const enc = document.getElementById("legacy-direct-encoding").value || null;
  if (!txt) {
    showAlert("Please enter legacy text to convert.", "warning");
    return;
  }
  try {
    const res = await fetch("/api/v1/legacy2unicode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input_text: txt, encoding: enc }),
    });
    const data = await res.json();
    if (res.ok) {
      document.getElementById("legacy-direct-output").textContent = data.output || "";
    } else {
      showAlert(data.detail || "Conversion error", "danger");
    }
  } catch (e) {
    showAlert(`Conversion error: ${e.message}`, "danger");
  }
}

function copyOutput() {
  const out = document.getElementById("normalized-output").textContent || "";
  if (!out || out.startsWith("No output yet")) return;
  navigator.clipboard.writeText(out);
  showAlert("Normalized Tamil Unicode copied to clipboard!", "success");
}

async function downloadDocx() {
  const out = document.getElementById("normalized-output").textContent || "";
  if (!out || out.startsWith("No output yet")) {
    showAlert("Please normalize some text before downloading.", "warning");
    return;
  }
  const res = await fetch("/api/v1/export-docx", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: out }),
  });
  if (res.ok) {
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "iyal_normalized_output.docx";
    a.click();
    URL.revokeObjectURL(url);
  }
}

function downloadTxt() {
  const out = document.getElementById("normalized-output").textContent || "";
  if (!out || out.startsWith("No output yet")) {
    showAlert("Please normalize some text before downloading.", "warning");
    return;
  }
  const blob = new Blob([out], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "iyal_normalized_output.txt";
  a.click();
  URL.revokeObjectURL(url);
}

function openFeedbackModal(fromOutput = false) {
  document.getElementById("fb-status-msg").textContent = "";
  if (fromOutput && lastAnalysisResponse) {
    document.getElementById("fb-category").value = "classification";
  }
  document.getElementById("feedback-modal").classList.add("open");
}

function closeFeedbackModal() {
  document.getElementById("feedback-modal").classList.remove("open");
}

async function submitUserFeedback() {
  const category = document.getElementById("fb-category").value;
  const rating = parseInt(document.getElementById("fb-rating").value, 10);
  const feedbackText = (document.getElementById("fb-text").value || "").trim();
  const statusEl = document.getElementById("fb-status-msg");

  if (feedbackText.length < 2) {
    statusEl.style.color = "var(--danger)";
    statusEl.textContent = "Please enter your feedback message before submitting.";
    return;
  }

  try {
    const payload = {
      created_at: new Date().toISOString(),
      category,
      rating,
      input_text: lastAnalysisResponse ? lastAnalysisResponse.input_text : document.getElementById("input-text").value,
      output: lastAnalysisResponse || { note: "General UI feedback" },
      feedback: feedbackText,
    };
    const res = await fetch("/api/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (res.ok) {
      document.getElementById("fb-text").value = "";
      closeFeedbackModal();
      showAlert(data.message || "Feedback submitted! Thank you.", "success");
    } else {
      statusEl.style.color = "var(--danger)";
      statusEl.textContent = data.detail || "Failed to submit feedback.";
    }
  } catch (err) {
    statusEl.style.color = "var(--danger)";
    statusEl.textContent = `Error: ${err.message}`;
  }
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
