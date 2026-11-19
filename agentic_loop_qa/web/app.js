/* --------------------------------------------------------------------------
   CriticRAG AI — Interactive Web Dashboard Client Logic
   -------------------------------------------------------------------------- */

let currentTraceData = null;
let activeIterationIndex = 0;
let evalChartInstance = null;

// Initialize Lucide icons & fetch health status on load
document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) {
    window.lucide.createIcons();
  }
  fetchHealthStatus();
});

// 1. Fetch System Health & Operational Mode
async function fetchHealthStatus() {
  const statusBadge = document.getElementById("statusBadge");
  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  const providerText = document.getElementById("providerText");
  const modelText = document.getElementById("modelText");

  try {
    const res = await fetch("/api/v1/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();

    if (data.mode === "live") {
      statusDot.className = "status-dot pulsing";
      statusText.innerText = "System Status: LIVE";
    } else {
      statusDot.className = "status-dot mock";
      statusText.innerText = "System Status: MOCK Mode";
    }

    providerText.innerText = `Provider: ${data.provider}`;
    modelText.innerText = `Model: ${data.model}`;
  } catch (err) {
    statusDot.className = "status-dot mock";
    statusText.innerText = "Offline / Server Error";
    providerText.innerText = "Provider: Unknown";
    modelText.innerText = "Model: Unknown";
  }
}

// Preset Query Selector
function setPresetQuery(query) {
  document.getElementById("questionInput").value = query;
}

// View Tab Switching (Trace vs Evaluation)
function switchView(tabName) {
  const traceBtn = document.getElementById("traceTabBtn");
  const evalBtn = document.getElementById("evalTabBtn");
  const traceView = document.getElementById("traceView");
  const evalView = document.getElementById("evalView");

  if (tabName === "trace") {
    traceBtn.classList.add("active");
    evalBtn.classList.remove("active");
    traceView.classList.remove("hidden");
    evalView.classList.add("hidden");
  } else {
    evalBtn.classList.add("active");
    traceBtn.classList.remove("active");
    evalView.classList.remove("hidden");
    traceView.classList.add("hidden");
  }
}

// 2. Handle Ask Question Execution
async function handleAskQuestion() {
  const questionInput = document.getElementById("questionInput");
  const question = questionInput.value.strip ? questionInput.value.strip() : questionInput.value.trim();

  if (!question) {
    alert("Please enter a valid question before running Agentic QA.");
    return;
  }

  // UI state updates: show loading, hide welcome / results
  switchView("trace");
  document.getElementById("traceWelcome").classList.add("hidden");
  document.getElementById("traceResults").classList.add("hidden");
  document.getElementById("traceLoading").classList.remove("hidden");

  const askBtn = document.getElementById("askBtn");
  askBtn.disabled = true;

  const maxIterations = parseInt(document.getElementById("maxIterSlider").value) || 3;
  const confThreshold = parseFloat(document.getElementById("confStopSlider").value) || 0.85;
  const retrieverType = document.getElementById("retrieverSelect").value || "vector";

  try {
    const res = await fetch("/api/v1/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: question,
        max_iterations: maxIterations,
        confidence_threshold: confThreshold,
        retriever_type: retrieverType,
      }),
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Error running QA loop");
    }

    const payload = await res.json();
    currentTraceData = payload.data;

    // Render Trace & Evidence
    renderEvidencePassages(currentTraceData.passages_used || []);
    renderTraceResults(currentTraceData);
  } catch (err) {
    alert(`QA Execution Failed: ${err.message}`);
    document.getElementById("traceWelcome").classList.remove("hidden");
  } finally {
    document.getElementById("traceLoading").classList.add("hidden");
    askBtn.disabled = false;
  }
}

// 3. Render Evidence Passages
function renderEvidencePassages(passages) {
  const listEl = document.getElementById("evidenceList");
  const badgeEl = document.getElementById("evidenceCountBadge");
  badgeEl.innerText = `${passages.length} Passages`;

  if (!passages || passages.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <p>No evidence passages retrieved.</p>
      </div>`;
    return;
  }

  listEl.innerHTML = passages
    .map(
      (p, idx) => `
    <div class="evidence-item">
      <div class="evidence-item-header">
        <span class="evidence-title">[${idx + 1}] ${escapeHtml(p.title)}</span>
        <span class="evidence-score">Score: ${p.score ? p.score.toFixed(3) : '1.0'}</span>
      </div>
      <div class="evidence-text">${escapeHtml(p.text)}</div>
    </div>`
    )
    .join("");
}

// 4. Render Multi-Agent Trace Results
function renderTraceResults(data) {
  if (!data) return;
  document.getElementById("traceResults").classList.remove("hidden");

  // Final Converged Banner
  const finalAnswerText = document.getElementById("finalAnswerText");
  const finalMetaText = document.getElementById("finalMetaText");
  const finalVerdictBadge = document.getElementById("finalVerdictBadge");

  if (finalAnswerText) finalAnswerText.innerText = `Final Answer: ${data.final_answer || 'N/A'}`;
  if (finalMetaText) finalMetaText.innerText = `${data.converged ? 'Converged' : 'Budget Exhausted'} after ${data.iterations_used || 1} iteration(s)`;

  // Retrieval warning: shown when the retriever found no matching evidence,
  // so the user understands *why* the answer looks empty/unanswerable
  // instead of it looking like a silent failure.
  const warningBanner = document.getElementById("retrievalWarningBanner");
  const warningText = document.getElementById("retrievalWarningText");
  if (warningBanner && warningText) {
    if (data.retrieval_warning) {
      warningText.innerText = data.retrieval_warning;
      warningBanner.classList.remove("hidden");
    } else {
      warningBanner.classList.add("hidden");
    }
  }

  const traceList = Array.isArray(data.trace) ? data.trace : [];
  const lastStep = traceList.length > 0 ? traceList[traceList.length - 1] : null;
  if (lastStep && finalVerdictBadge) {
    const rawVerdict = lastStep.verdict || (lastStep.critique && lastStep.critique.verdict) || "approve";
    const verdict = String(rawVerdict).toUpperCase();
    finalVerdictBadge.innerText = verdict;
    if (verdict === "APPROVE") {
      finalVerdictBadge.className = "banner-badge";
    } else {
      finalVerdictBadge.className = "banner-badge revise";
    }
  }

  // Iteration Tab Buttons
  const tabContainer = document.getElementById("iterationTabContainer");
  if (tabContainer) {
    tabContainer.innerHTML = traceList
      .map(
        (t, idx) => {
          if (!t) return "";
          const rawV = t.verdict || (t.critique && t.critique.verdict) || "approve";
          const v = String(rawV).toLowerCase();
          return `
      <button class="iter-tab-btn ${idx === 0 ? "active" : ""}" onclick="selectIterationStep(${idx})">
        Step ${t.iteration || (idx + 1)} ${v === "approve" ? "✓" : "⚡"}
      </button>`;
        }
      )
      .join("");
  }

  activeIterationIndex = 0;
  if (traceList.length > 0) {
    renderIterationStepDetail(0);
  }
}

function selectIterationStep(idx) {
  activeIterationIndex = idx;
  const btns = document.querySelectorAll(".iter-tab-btn");
  btns.forEach((btn, i) => {
    if (i === idx) btn.classList.add("active");
    else btn.classList.remove("active");
  });
  renderIterationStepDetail(idx);
}

function renderIterationStepDetail(idx) {
  const container = document.getElementById("iterationDetailContainer");
  if (!container) return;
  if (!currentTraceData || !Array.isArray(currentTraceData.trace) || !currentTraceData.trace[idx]) {
    container.innerHTML = "";
    return;
  }

  const step = currentTraceData.trace[idx];
  if (!step) return;

  const answer = step.answer || (step.generator_output && step.generator_output.answer) || "";
  const reasoning = step.reasoning || (step.generator_output && step.generator_output.reasoning) || "";
  const rawVerdict = step.verdict || (step.critique && step.critique.verdict) || "approve";
  const confidence = step.confidence !== undefined ? step.confidence : (step.critique ? step.critique.confidence : 1.0);
  const issues = step.issues || (step.critique && step.critique.issues) || [];
  const suggestedFix = step.suggested_fix || (step.critique && step.critique.suggested_fix) || null;

  const confPercent = Math.round((confidence || 0) * 100);
  const verdictClass = String(rawVerdict).toLowerCase();

  let html = `
    <!-- Generator Step Card -->
    <div class="glass-card agent-card generator">
      <div class="agent-title-row">
        <span class="agent-name">Step ${step.iteration}: Generator Agent</span>
        <span class="badge-accent">Candidate Answer</span>
      </div>
      <div class="answer-box">${escapeHtml(answer)}</div>
      <div class="reasoning-box">
        <strong>Reasoning Chain:</strong><br>
        ${escapeHtml(reasoning)}
      </div>
    </div>

    <!-- Critic Audit Card -->
    <div class="glass-card agent-card critic">
      <div class="agent-title-row">
        <span class="agent-name">Step ${step.iteration}: Critic Audit</span>
        <span class="badge-muted">Hallucination Firewall</span>
      </div>

      <div class="verdict-row">
        <div class="verdict-pill ${verdictClass}">${escapeHtml(rawVerdict)}</div>
        
        <div class="confidence-bar-container">
          <div class="confidence-bar-track">
            <div class="confidence-bar-fill" style="width: ${confPercent}%"></div>
          </div>
          <span class="confidence-text">${confPercent}% Confidence</span>
        </div>
      </div>

      ${issues && issues.length > 0
      ? `<div class="issues-box">
               <strong>Flagged Issues:</strong>
               <ul>${issues.map(i => `<li>${escapeHtml(i)}</li>`).join("")}</ul>
             </div>`
      : `<div class="reasoning-box">No unsupported claims or hallucinations flagged by Critic.</div>`
    }

      ${suggestedFix
      ? `<div class="reasoning-box" style="margin-top:0.5rem; border-left:3px solid var(--status-amber);">
               <strong>Suggested Fix:</strong> ${escapeHtml(suggestedFix)}
             </div>`
      : ""
    }
    </div>
  `;

  container.innerHTML = html;
  if (window.lucide) window.lucide.createIcons();
}

// 5. Handle Run Benchmark Evaluation
async function handleRunEval() {
  switchView("eval");
  document.getElementById("evalResults").classList.add("hidden");
  document.getElementById("evalLoading").classList.remove("hidden");

  const evalBtn = document.getElementById("evalBtn");
  evalBtn.disabled = true;

  try {
    const res = await fetch("/api/v1/eval", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Error running evaluation");
    }

    const payload = await res.json();
    renderEvalResults(payload.report);
  } catch (err) {
    alert(`Benchmark Evaluation Failed: ${err.message}`);
  } finally {
    document.getElementById("evalLoading").classList.add("hidden");
    evalBtn.disabled = false;
  }
}

// 6. Render Benchmark Evaluation Results & Chart
function renderEvalResults(report) {
  document.getElementById("evalResults").classList.remove("hidden");

  // Populate Metric Cards
  const baseEm = (report.baseline_em * 100).toFixed(1);
  const loopEm = (report.agentic_loop_em * 100).toFixed(1);
  const emGain = (loopEm - baseEm).toFixed(1);

  const baseF1 = (report.baseline_f1 * 100).toFixed(1);
  const loopF1 = (report.agentic_loop_f1 * 100).toFixed(1);
  const f1Gain = (loopF1 - baseF1).toFixed(1);

  document.getElementById("baselineEmVal").innerText = `${baseEm}%`;
  document.getElementById("loopEmVal").innerText = `${loopEm}%`;
  document.getElementById("emDeltaBadge").innerText = `+${emGain}% Gain`;

  document.getElementById("baselineF1Val").innerText = `${baseF1}%`;
  document.getElementById("loopF1Val").innerText = `${loopF1}%`;
  document.getElementById("f1DeltaBadge").innerText = `+${f1Gain}% Gain`;

  document.getElementById("avgItersVal").innerText = (report.average_iterations || 0).toFixed(2);
  document.getElementById("changeRateText").innerText = `Answer Revision Rate: ${((report.change_rate || 0) * 100).toFixed(0)}%`;

  // Render Table Breakdown
  const tableBody = document.getElementById("evalTableBody");
  if (report.examples && report.examples.length > 0) {
    tableBody.innerHTML = report.examples
      .map(
        (ex) => `
      <tr>
        <td><strong>${escapeHtml(ex.question)}</strong></td>
        <td>${escapeHtml(ex.baseline_answer)}</td>
        <td style="color:var(--accent-cyan); font-weight:600;">${escapeHtml(ex.loop_answer)}</td>
        <td>${escapeHtml(ex.ground_truth)}</td>
        <td>
          <span class="table-badge ${ex.loop_em ? "pass" : "fail"}">
            ${ex.loop_em ? "PASS (1.0)" : "FAIL (0.0)"}
          </span>
        </td>
        <td>${ex.iterations_used} iter</td>
      </tr>`
      )
      .join("");
  } else {
    tableBody.innerHTML = `<tr><td colspan="6">No detailed examples found.</td></tr>`;
  }

  // Render Chart.js Graph
  renderChart(baseEm, loopEm, baseF1, loopF1);
}

function renderChart(baseEm, loopEm, baseF1, loopF1) {
  const ctx = document.getElementById("evalChart").getContext("2d");

  if (evalChartInstance) {
    evalChartInstance.destroy();
  }

  evalChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Exact Match (EM)", "Token F1 Score"],
      datasets: [
        {
          label: "Single-Shot Baseline",
          data: [baseEm, baseF1],
          backgroundColor: "rgba(99, 102, 241, 0.5)",
          borderColor: "#6366f1",
          borderWidth: 1.5,
          borderRadius: 6,
        },
        {
          label: "Critic Loop (Multi-Agent)",
          data: [loopEm, loopF1],
          backgroundColor: "rgba(16, 185, 129, 0.6)",
          borderColor: "#10b981",
          borderWidth: 1.5,
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#94a3b8", callback: (v) => v + "%" },
        },
        x: {
          grid: { display: false },
          ticks: { color: "#f8fafc", font: { weight: "600" } },
        },
      },
      plugins: {
        legend: {
          labels: { color: "#f8fafc", font: { family: "Inter" } },
        },
      },
    },
  });
}

// Utility: Escape HTML
function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}