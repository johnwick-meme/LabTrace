
"use strict";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const STORAGE_KEY = "labtrace.experiments.v1";

const sampleReadings = [
  { reading_id: "R1", voltage_v: 2, current_a: 0.02 },
  { reading_id: "R2", voltage_v: 4, current_a: 0.04 },
  { reading_id: "R3", voltage_v: 6, current_a: 0.06 },
  { reading_id: "R4", voltage_v: 8, current_a: 0.04 }
];

let lastResult = null;
let lastExperiment = null;
let quizIndex = 0;
let quizScore = 0;
let quizAnswered = false;
let toastTimer;

const quizQuestions = [
  {
    question: "What does Ohm's law state?",
    options: [
      "Voltage is always zero",
      "Current is proportional to voltage at constant physical conditions for an ohmic conductor",
      "Resistance always increases with current",
      "Power is always constant"
    ],
    answer: 1,
    explanation: "Ohm's law states V = IR under the applicable constant physical conditions."
  },
  {
    question: "What is the formula for resistance?",
    options: ["R = V / I", "R = V × I", "R = I / V", "R = V + I"],
    answer: 0,
    explanation: "Resistance in ohms equals voltage in volts divided by current in amperes."
  },
  {
    question: "What resistance results from 2 V and 0.02 A?",
    options: ["10 Ω", "40 Ω", "100 Ω", "200 Ω"],
    answer: 2,
    explanation: "R = 2 / 0.02 = 100 Ω."
  },
  {
    question: "Why should raw measurements remain unchanged?",
    options: [
      "To avoid doing calculations",
      "To make every result look consistent",
      "To maintain an auditable record of the original experiment",
      "To prevent saving experiments"
    ],
    answer: 2,
    explanation: "Keeping the original data preserves scientific integrity and allows the analysis to be checked."
  },
  {
    question: "The calculated resistance is 200 Ω while the others are 100 Ω. What should LabTrace do?",
    options: [
      "Change the value to 100 Ω",
      "Delete the reading",
      "Flag the discrepancy for investigation",
      "Claim the instrument is broken"
    ],
    answer: 2,
    explanation: "The discrepancy should be flagged. The readings alone do not establish its cause."
  },
  {
    question: "What happens when current is zero in R = V / I?",
    options: [
      "Resistance is always zero",
      "Division by zero is undefined",
      "Resistance is always 100 Ω",
      "Voltage becomes zero automatically"
    ],
    answer: 1,
    explanation: "The calculation is undefined for zero current, so the reading must be rejected for this calculation."
  }
];

// ---------- Navigation ----------

function showPage(name) {
  const validPages = ["experiment", "investigation", "memory", "viva", "chat"];
  if (!validPages.includes(name)) return;

  $$(".page").forEach((page) => {
    page.classList.toggle("active", page.id === `page-${name}`);
  });

  $$(".nav-link").forEach((button) => {
    button.classList.toggle("active", button.dataset.page === name);
  });

  $("#breadcrumb").textContent =
    name.charAt(0).toUpperCase() + name.slice(1);

  document.body.classList.remove("menu-open");
}

$$(".nav-link").forEach((button) => {
  button.addEventListener("click", () => showPage(button.dataset.page));
});

$$("[data-go]").forEach((button) => {
  button.addEventListener("click", () => showPage(button.dataset.go));
});

$("#mobile-menu").addEventListener("click", () => {
  document.body.classList.toggle("menu-open");
});

$("#theme-toggle").addEventListener("click", () => {
  document.body.classList.toggle("light");
  $("#theme-toggle").textContent =
    document.body.classList.contains("light") ? "☾" : "☼";
});

// ---------- Notifications ----------

function notify(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");

  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 3000);
}

function feedback(message, type = "info") {
  const element = $("#experiment-feedback");
  element.textContent = message;
  element.className = `feedback show ${type}`;
}

// ---------- Safe rendering helpers ----------

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function formatOhms(value) {
  if (!Number.isFinite(value)) return "—";
  return `${Number(value.toFixed(4))} Ω`;
}

// ---------- Readings table ----------

function renderReadings(readings) {
  const tbody = $("#reading-rows");
  tbody.replaceChildren();

  readings.forEach((reading, index) => {
    const row = document.createElement("tr");

    const idCell = element("td", "", `R${index + 1}`);

    const voltageCell = document.createElement("td");
    const voltage = document.createElement("input");
    voltage.type = "number";
    voltage.step = "any";
    voltage.required = true;
    voltage.setAttribute("aria-label", `R${index + 1} voltage`);
    voltage.value = reading.voltage_v ?? "";
    voltage.dataset.voltage = "";
    voltageCell.append(voltage);

    const currentCell = document.createElement("td");
    const current = document.createElement("input");
    current.type = "number";
    current.step = "any";
    current.required = true;
    current.setAttribute("aria-label", `R${index + 1} current`);
    current.value = reading.current_a ?? "";
    current.dataset.current = "";
    currentCell.append(current);

    const actionCell = document.createElement("td");
    const remove = element("button", "remove-reading", "×");
    remove.type = "button";
    remove.title = `Remove reading R${index + 1}`;
    remove.setAttribute("aria-label", `Remove reading R${index + 1}`);

    remove.addEventListener("click", () => {
      if ($("#reading-rows").children.length <= 1) {
        notify("Keep at least one reading.");
        return;
      }

      row.remove();
      renumberReadings();
      invalidateAnalysis();
    });

    actionCell.append(remove);
    row.append(idCell, voltageCell, currentCell, actionCell);
    tbody.append(row);
  });

  updateReadingCount();
}

function renumberReadings() {
  const currentReadings = $$("#reading-rows tr").map((row) => ({
    voltage_v: row.querySelector("[data-voltage]").value,
    current_a: row.querySelector("[data-current]").value
  }));

  renderReadings(currentReadings);
}

function updateReadingCount() {
  $("#stat-count").textContent = $("#reading-rows").children.length;
}

function invalidateAnalysis() {
  lastResult = null;
  lastExperiment = null;

  $("#stat-flags").textContent = "—";
  $("#stat-flag-note").textContent = "Run verification first";
  $("#result-reference").textContent = "—";
  $("#result-valid").textContent = "—";
  $("#result-anomalies").textContent = "—";

  $("#results-table").textContent =
    "Results need to be recalculated after the inputs change.";
  $("#results-table").className = "empty-state";
}

$("#add-reading").addEventListener("click", () => {
  const readings = collectRawRows();
  readings.push({ voltage_v: "", current_a: "" });
  renderReadings(readings);
  invalidateAnalysis();
  notify("New reading added.");
});

$("#reset-sample").addEventListener("click", () => {
  $("#experiment-id").value = "OHMS-001";
  $("#experiment-title").value = "Ohm's Law Verification";
  $("#tolerance").value = "5";
  $("#observations").value = "";
  renderReadings(sampleReadings);
  invalidateAnalysis();
  feedback("Sample measurements loaded. Original sample values are preserved.", "success");
});

function collectRawRows() {
  return $$("#reading-rows tr").map((row) => ({
    voltage_v: row.querySelector("[data-voltage]").value,
    current_a: row.querySelector("[data-current]").value
  }));
}

function collectExperiment() {
  const experimentId = $("#experiment-id").value.trim();
  const title = $("#experiment-title").value.trim();

  if (!/^[A-Za-z0-9_-]+$/.test(experimentId)) {
    throw new Error("Use a valid experiment ID containing only letters, numbers, _ or -.");
  }

  if (!title) throw new Error("Enter an experiment title.");

  const toleranceText = $("#tolerance").value.trim();
  if (toleranceText === "") throw new Error("Enter a tolerance.");

  const tolerance = Number(toleranceText);

  if (!Number.isFinite(tolerance) || tolerance < 0 || tolerance >= 100) {
    throw new Error("Tolerance must be at least 0% and less than 100%.");
  }

  const rows = $$("#reading-rows tr");
  if (!rows.length) throw new Error("Add at least one reading.");

  const readings = rows.map((row, index) => {
    const vText = row.querySelector("[data-voltage]").value.trim();
    const iText = row.querySelector("[data-current]").value.trim();

    if (vText === "" || iText === "") {
      throw new Error(`Reading R${index + 1} has a missing numeric value.`);
    }

    const voltage = Number(vText);
    const current = Number(iText);

    if (!Number.isFinite(voltage) || !Number.isFinite(current)) {
      throw new Error(`Reading R${index + 1} must contain finite numbers.`);
    }

    if (current === 0) {
      throw new Error(`Reading R${index + 1} has zero current. Resistance cannot be calculated.`);
    }

    const resistance = voltage / current;

    if (!Number.isFinite(resistance)) {
      throw new Error(`Resistance calculation for R${index + 1} is outside the supported numeric range.`);
    }

    return {
      reading_id: `R${index + 1}`,
      voltage_v: voltage,
      current_a: current
    };
  });

  return {
    experiment_id: experimentId,
    title,
    raw_readings: readings,
    observations: $("#observations").value
      .split("\n").map((line) => line.trim()).filter(Boolean),
    tolerance_fraction: tolerance / 100,
    manual_text: $("#manual-text").value,
    manual_query: $("#manual-query").value.trim()
  };
}

// ---------- Deterministic calculations (Moved to backend) ----------

$("#run-button").addEventListener("click", runVerification);
$("#hero-run").addEventListener("click", runVerification);

function setCalculationLoading(isLoading) {
  const btn1 = $("#run-button");
  const btn2 = $("#hero-run");
  if (btn1) {
    btn1.disabled = isLoading;
    btn1.textContent = isLoading ? "Calculating..." : "Run calculations & verification →";
  }
  if (btn2) {
    btn2.disabled = isLoading;
    btn2.textContent = isLoading ? "Calculating..." : "Run calculations →";
  }
}

async function runVerification() {
  try {
    const experiment = collectExperiment();
    
    setCalculationLoading(true);

    const response = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        readings: experiment.raw_readings,
        tolerance: experiment.tolerance_fraction
      })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error: ${response.status}`);
    }

    const result = await response.json();

    lastExperiment = experiment;
    lastResult = result;

    renderResults(result, experiment.raw_readings);
    updateStats(experiment, result);
    renderManualResults(experiment.manual_query, experiment.manual_text);
    showPage("investigation");

    feedback("Verification completed. Original input readings were not changed.", "success");
    notify("Resistance calculations completed.");
  } catch (error) {
    feedback(error.message, "error");
    notify("Please check the experiment inputs.");
  } finally {
    setCalculationLoading(false);
  }
}

function updateStats(experiment, result) {
  $("#stat-id").textContent = experiment.experiment_id;
  $("#stat-count").textContent = experiment.raw_readings.length;
  $("#stat-flags").textContent = result.anomalies.length;
  $("#stat-flag-note").textContent =
    result.anomalies.length ? "Readings require investigation" : "No anomalies flagged";

  $("#result-reference").textContent =
    result.reference_resistance_ohm !== null ? formatOhms(result.reference_resistance_ohm) : "—";
  $("#result-valid").textContent = result.readings.filter(r => r.valid).length;
  $("#result-anomalies").textContent = result.anomalies.length;
}

function renderResults(result, rawReadings) {
  const container = $("#results-table");
  container.className = "results-table";
  container.replaceChildren();

  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");

  ["ID", "Voltage", "Current", "Resistance", "Deviation", "Status"].forEach((text) => {
    headRow.append(element("th", "", text));
  });

  head.append(headRow);
  table.append(head);

  const body = document.createElement("tbody");

  result.readings.forEach((reading, idx) => {
    const raw = rawReadings[idx];
    const row = document.createElement("tr");
    
    // Pull from backend calculation if valid, otherwise fallback to raw input
    const v = reading.valid ? reading.calculation.voltage_v : raw.voltage_v;
    const c = reading.valid ? reading.calculation.current_a : raw.current_a;
    const r = reading.valid ? formatOhms(reading.calculation.resistance_ohm) : "Error";

    const values = [
      reading.reading_id,
      `${v} V`,
      `${c} A`,
      r,
      reading.deviation_fraction === null
        ? "N/A"
        : `${(reading.deviation_fraction * 100).toFixed(2)}%`
    ];

    values.forEach((value) => row.append(element("td", "", value)));

    const statusCell = document.createElement("td");
    const chipClass = reading.valid ? (reading.anomaly ? "flag" : "ok") : "flag";
    const chipText = reading.valid ? (reading.anomaly ? "Flagged" : "Within tolerance") : "Invalid";
    
    const chip = element(
      "span",
      `status-chip ${chipClass}`,
      chipText
    );
    if (!reading.valid) {
      chip.title = reading.message; // Show error message on hover
    }
    statusCell.append(chip);
    row.append(statusCell);
    body.append(row);
  });

  table.append(body);
  container.append(table);

  const note = element(
    "p",
    "muted",
    result.anomalies.length
      ? `Flagged for investigation: ${result.anomalies.join(", ")}. This does not prove a specific cause.`
      : "No readings exceeded the configured tolerance."
  );

  container.append(note);
}

// ---------- Manual passage search (Moved to backend) ----------

async function renderManualResults(query, manualText) {
  const container = $("#manual-results");
  container.replaceChildren();

  if (!manualText.trim()) {
    container.append(element("p", "muted", "Paste actual manual text to search."));
    return;
  }

  if (!query.trim()) {
    container.append(element("p", "muted", "Enter a search query."));
    return;
  }

  container.append(element("p", "muted", "Searching..."));

  try {
    const response = await fetch("/api/manual-search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, manual_text: manualText })
    });
    
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Search failed: ${response.status}`);
    }
    
    const data = await response.json();
    const matches = data.passages;

    container.replaceChildren();

    if (!matches.length) {
      container.append(element("p", "muted", "No matching passages found in the supplied text."));
      return;
    }

    matches.forEach((match) => {
      const passage = element("div", "manual-passage", match.text);
      passage.append(element(
        "small",
        "",
        `Character offsets ${match.start_char}–${match.end_char} · ${match.matched_terms} matching terms`
      ));
      container.append(passage);
    });
  } catch (error) {
    container.replaceChildren(element("p", "feedback error show", error.message));
  }
}

$("#search-manual").addEventListener("click", async () => {
  const btn = $("#search-manual");
  try {
    btn.disabled = true;
    btn.textContent = "Searching...";
    await renderManualResults($("#manual-query").value, $("#manual-text").value);
  } catch (error) {
    notify(error.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Search manual text →";
  }
});

// ---------- Browser-local experiment memory ----------

function readMemory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return [];

    const records = JSON.parse(raw);
    if (!Array.isArray(records)) throw new Error("Memory data is not a list.");

    return records;
  } catch (error) {
    throw new Error(`Cannot read browser memory: ${error.message}`);
  }
}

function writeMemory(records) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

// ---------- Save and Load with Backend Persistence ----------

function currentExperimentForStorage() {
  const experiment = collectExperiment();

  return {
    experiment_id: experiment.experiment_id,
    title: experiment.title,
    raw_readings: experiment.raw_readings.map((r) => ({ ...r })),
    observations: [...experiment.observations]
  };
}

$("#save-button").addEventListener("click", async () => {
  const btn = $("#save-button");
  try {
    btn.disabled = true;
    btn.textContent = "Saving...";

    const experiment = currentExperimentForStorage();

    const response = await fetch("/api/experiments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(experiment)
    });
    
    if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.status}`);
    }

    // Keep localStorage as a lightweight index since there is no GET /api/experiments list endpoint
    const indexRecord = {
        experiment_id: experiment.experiment_id,
        title: experiment.title,
        readings_count: experiment.raw_readings.length
    };

    const records = readMemory();
    const existingIndex = records.findIndex(
      (r) => r.experiment_id === experiment.experiment_id
    );

    if (existingIndex >= 0) {
      records[existingIndex] = indexRecord;
    } else {
      records.unshift(indexRecord);
    }

    writeMemory(records);
    renderMemory();
    feedback(`Experiment ${experiment.experiment_id} saved to server.`, "success");
    notify("Experiment saved.");
  } catch (error) {
    feedback(error.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Save experiment";
  }
});

function renderMemory() {
  const container = $("#memory-list");
  container.replaceChildren();

  let records;

  try {
    records = readMemory();
  } catch (error) {
    container.append(element("p", "feedback error show", error.message));
    return;
  }

  const query = $("#memory-search").value.trim().toLowerCase();

  const filtered = records.filter((record) =>
    `${record.experiment_id} ${record.title}`.toLowerCase().includes(query)
  );

  $("#memory-count").textContent = `${records.length} record${records.length === 1 ? "" : "s"}`;

  if (!filtered.length) {
    container.append(element(
      "div",
      "empty-state",
      records.length ? "No matching experiments." : "No saved experiments yet. Save an experiment to see it here."
    ));
    return;
  }

  filtered.forEach((record) => {
    const card = element("div", "memory-item");
    const details = document.createElement("div");
    details.append(element("h3", "", record.title || record.experiment_id));
    
    const count = record.readings_count || (record.raw_readings || []).length;
    details.append(element(
      "p",
      "",
      `${record.experiment_id} · ${count} readings (Index)`
    ));

    const actions = element("div", "memory-actions");
    const load = element("button", "btn btn-secondary btn-small", "Load");
    load.addEventListener("click", () => loadSavedExperiment(record.experiment_id));

    const exportButton = element("button", "btn btn-secondary btn-small", "Export");
    exportButton.addEventListener("click", async () => {
      try {
        const res = await fetch(`/api/experiments/${record.experiment_id}`);
        if (!res.ok) throw new Error("Could not fetch data for export.");
        const data = await res.json();
        downloadJSON(data, `${record.experiment_id}.json`);
      } catch (e) {
        notify(e.message);
      }
    });

    const remove = element("button", "btn btn-quiet btn-small", "Delete Index");
    remove.addEventListener("click", () => {
      if (!confirm(`Delete index for ${record.experiment_id}? This only removes it from this browser.`)) return;

      writeMemory(readMemory().filter((r) => r.experiment_id !== record.experiment_id));
      renderMemory();
      notify("Browser record index deleted.");
    });

    actions.append(load, exportButton, remove);
    card.append(details, actions);
    container.append(card);
  });
}

async function loadSavedExperiment(id) {
  try {
    notify("Loading from server...");
    const response = await fetch(`/api/experiments/${id}`);
    
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error("Experiment not found on server.");
      }
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error: ${response.status}`);
    }
    
    const record = await response.json();

    $("#experiment-id").value = record.experiment_id;
    $("#experiment-title").value = record.title || "";
    $("#observations").value = (record.observations || []).join("\n");

    renderReadings(record.raw_readings || []);

    invalidateAnalysis();
    showPage("experiment");
    notify(`Loaded ${id} from server.`);
  } catch (error) {
    notify(`Load failed: ${error.message}`);
  }
}

$("#memory-search").addEventListener("input", renderMemory);

function downloadJSON(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json"
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

$("#export-all").addEventListener("click", () => {
  try {
    downloadJSON(readMemory(), "labtrace-experiments.json");
    notify("Export prepared.");
  } catch (error) {
    notify(error.message);
  }
});

$("#import-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  try {
    const imported = JSON.parse(await file.text());
    const incoming = Array.isArray(imported) ? imported : [imported];

    for (const record of incoming) {
      if (
        !record ||
        typeof record.experiment_id !== "string" ||
        !/^[A-Za-z0-9_-]+$/.test(record.experiment_id) ||
        !Array.isArray(record.raw_readings)
      ) {
        throw new Error("Import must contain experiment IDs and raw_readings lists.");
      }
    }

    const existing = readMemory();

    for (const record of incoming) {
      const index = existing.findIndex(
        (item) => item.experiment_id === record.experiment_id
      );

      if (index >= 0) existing[index] = record;
      else existing.unshift(record);
    }

    writeMemory(existing);
    renderMemory();
    notify(`${incoming.length} experiment record(s) imported.`);
  } catch (error) {
    notify(`Import failed: ${error.message}`);
  } finally {
    event.target.value = "";
  }
});

// ---------- Viva quiz ----------

function renderQuiz() {
  const question = quizQuestions[quizIndex];
  quizAnswered = false;

  $("#quiz-counter").textContent =
    `QUESTION ${String(quizIndex + 1).padStart(2, "0")} / ${String(quizQuestions.length).padStart(2, "0")}`;
  $("#quiz-score").textContent = `Score: ${quizScore}`;
  $("#quiz-progress-fill").style.width =
    `${(quizIndex / quizQuestions.length) * 100}%`;
  $("#quiz-question").textContent = question.question;
  $("#quiz-feedback").className = "feedback";
  $("#quiz-feedback").textContent = "";
  $("#quiz-options").replaceChildren();
  $("#quiz-next").disabled = true;
  $("#quiz-next").textContent =
    quizIndex === quizQuestions.length - 1 ? "Finish quiz ✓" : "Next question →";

  question.options.forEach((option, index) => {
    const button = element("button", "quiz-option");
    button.type = "button";

    button.append(element("span", "option-letter", String.fromCharCode(65 + index)));
    button.append(element("span", "", option));

    button.addEventListener("click", () => answerQuestion(index, button));
    $("#quiz-options").append(button);
  });
}

function answerQuestion(selectedIndex, selectedButton) {
  if (quizAnswered) return;

  quizAnswered = true;
  const question = quizQuestions[quizIndex];
  const buttons = $$("#quiz-options .quiz-option");

  buttons.forEach((button) => { button.disabled = true; });

  const correct = selectedIndex === question.answer;

  if (correct) {
    quizScore++;
    selectedButton.classList.add("correct");
  } else {
    selectedButton.classList.add("incorrect");
    buttons[question.answer].classList.add("correct");
  }

  $("#quiz-score").textContent = `Score: ${quizScore}`;
  $("#quiz-progress-fill").style.width =
    `${((quizIndex + 1) / quizQuestions.length) * 100}%`;

  const result = $("#quiz-feedback");
  result.textContent = `${correct ? "Correct!" : "Not quite."} ${question.explanation}`;
  result.className = `feedback show ${correct ? "success" : "info"}`;

  $("#quiz-next").disabled = false;
}

$("#quiz-next").addEventListener("click", () => {
  if (!quizAnswered) return;

  if (quizIndex < quizQuestions.length - 1) {
    quizIndex++;
    renderQuiz();
  } else {
    $("#quiz-question").textContent = `Quiz complete: ${quizScore}/${quizQuestions.length}`;
    $("#quiz-options").replaceChildren();
    $("#quiz-feedback").textContent =
      quizScore === quizQuestions.length
        ? "Perfect score! You understand the core concepts."
        : "Review the explanations and try again to improve your score.";
    $("#quiz-feedback").className = "feedback show info";
    $("#quiz-next").disabled = true;
    $("#quiz-next").textContent = "Completed";
  }
});

$("#quiz-restart").addEventListener("click", () => {
  quizIndex = 0;
  quizScore = 0;
  renderQuiz();
});

// ---------- Initial setup ----------

$("#theme-toggle").textContent = "☼";
renderReadings(sampleReadings);
renderMemory();
renderQuiz();

$("#results-table").className = "empty-state";
$("#results-table").textContent =
  "Run verification on the Experiment page to see results.";

// ---------- Chat AI Integration ----------

const chatForm = $("#chat-form");
const chatInput = $("#chat-input");
const chatMessages = $("#chat-messages");
const chatSubmitBtn = $("#chat-submit-btn");

function appendChatMessage(sender, text, isUser = false) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-message ${isUser ? "user" : "assistant"}`;
  
  const label = document.createElement("span");
  label.className = "chat-message-label";
  label.textContent = isUser ? "YOU" : "LABTRACE ASSISTANT";
  msgDiv.appendChild(label);

  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  paragraph.style.whiteSpace = "pre-wrap";
  msgDiv.appendChild(paragraph);

  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return paragraph;
}

if (chatForm && chatInput) {
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    appendChatMessage("user", query, true);
    chatInput.value = "";
    chatInput.disabled = true;
    chatSubmitBtn.disabled = true;
    chatSubmitBtn.textContent = "Thinking...";

    const pendingP = appendChatMessage("assistant", "Thinking...");

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: query,
          experiment_context: lastExperiment || { readings: sampleReadings }
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned ${response.status}`);
      }

      const data = await response.json();
      pendingP.textContent = data.reply || "(No response received)";
    } catch (err) {
      pendingP.textContent = `Error connecting to AI: ${err.message}. Make sure Ollama is running!`;
      pendingP.style.color = "#ef4444";
    } finally {
      chatInput.disabled = false;
      chatSubmitBtn.disabled = false;
      chatSubmitBtn.textContent = "Send ↗";
      chatInput.focus();
    }
  });

  // Allow sending with Enter (Shift+Enter for newline)
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });
}