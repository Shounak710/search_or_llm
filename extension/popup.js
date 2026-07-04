import { classifyQuery } from "./api.js";
import {
  DEFAULT_SETTINGS,
  getLlmUrl,
  getSearchUrl,
  loadSettings,
  saveSettings,
} from "./settings.js";

const queryInput = document.getElementById("query");
const classifyBtn = document.getElementById("classify-btn");
const statusEl = document.getElementById("status");
const resultSection = document.getElementById("result-section");
const routeBadge = document.getElementById("route-badge");
const resultMeta = document.getElementById("result-meta");
const openSearchBtn = document.getElementById("open-search");
const openLlmBtn = document.getElementById("open-llm");
const feedbackSection = document.getElementById("feedback-section");
const feedbackQuery = document.getElementById("feedback-query");

const apiUrlInput = document.getElementById("api-url");
const feedbackDelayInput = document.getElementById("feedback-delay");
const browserSelect = document.getElementById("browser-select");
const browserCustomInput = document.getElementById("browser-custom");
const llmSelect = document.getElementById("llm-select");
const llmCustomInput = document.getElementById("llm-custom");

let settings = { ...DEFAULT_SETTINGS };
let currentClassification = null;
let activeFeedbackSession = null;

function createSessionId() {
  return crypto.randomUUID();
}

function setStatus(message, type = "") {
  statusEl.textContent = message;
  statusEl.className = `status${type ? ` ${type}` : ""}`;
}

function autoResizeTextarea() {
  queryInput.style.height = "auto";
  queryInput.style.height = `${queryInput.scrollHeight}px`;
}

function applySettingsToUI() {
  apiUrlInput.value = settings.apiBaseUrl;
  feedbackDelayInput.value = settings.feedbackDelayMinutes;
  browserSelect.value = settings.searchEngine;
  llmSelect.value = settings.llm;
  browserCustomInput.value = settings.customSearchUrl || "";
  llmCustomInput.value = settings.customLlmUrl || "";

  browserCustomInput.classList.toggle(
    "hidden",
    browserSelect.value !== "custom"
  );
  llmCustomInput.classList.toggle("hidden", llmSelect.value !== "custom");
}

function readSettingsFromUI() {
  settings = {
    apiBaseUrl: apiUrlInput.value.trim() || DEFAULT_SETTINGS.apiBaseUrl,
    feedbackDelayMinutes: Math.max(
      1,
      Number(feedbackDelayInput.value) || DEFAULT_SETTINGS.feedbackDelayMinutes
    ),
    searchEngine: browserSelect.value,
    llm: llmSelect.value,
    customSearchUrl: browserCustomInput.value.trim(),
    customLlmUrl: llmCustomInput.value.trim(),
  };
}

async function persistSettings() {
  readSettingsFromUI();
  await saveSettings(settings);
}

function renderClassification(result) {
  currentClassification = {
    ...result,
    classifiedAt: new Date().toISOString(),
  };

  resultSection.classList.remove("hidden");
  routeBadge.textContent = result.route;
  routeBadge.className = `route-badge ${result.route}`;

  const confidenceText =
    typeof result.confidence === "number"
      ? `Confidence: ${(result.confidence * 100).toFixed(0)}%`
      : "Matched by heuristic rules";
  const reasonText = result.reason ? `Reason: ${result.reason}` : "";
  const sourceText = `Source: ${result.source}`;
  resultMeta.textContent = [confidenceText, reasonText, sourceText]
    .filter(Boolean)
    .join(" · ");

  openSearchBtn.classList.toggle(
    "recommended",
    result.route === "search"
  );
  openLlmBtn.classList.toggle("recommended", result.route === "llm");
}

async function copyToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

async function openRoute(route) {
  if (!currentClassification) {
    return;
  }

  const query = currentClassification.query;
  const url =
    route === "search"
      ? getSearchUrl(query, settings)
      : getLlmUrl(query, settings);

  const session = {
    id: createSessionId(),
    query,
    predictedRoute: currentClassification.route,
    chosenRoute: route,
    manualOverride: route !== currentClassification.route,
    classifiedAt: currentClassification.classifiedAt,
  };

  if (route === "llm") {
    try {
      await copyToClipboard(query);
    } catch (error) {
      setStatus("Could not copy query to clipboard.", "error");
      return;
    }
  }

  window.open(url, "_blank", "noopener");

  chrome.runtime.sendMessage(
    {
      type: "scheduleFeedback",
      session,
      delayMinutes: settings.feedbackDelayMinutes,
    },
    (response) => {
      if (chrome.runtime.lastError || !response?.ok) {
        setStatus(
          route === "llm"
            ? "Copied to clipboard, but feedback reminder could not be scheduled."
            : "Opened, but feedback reminder could not be scheduled.",
          "error"
        );
        return;
      }

      if (route === "llm") {
        setStatus(
          `Copied to clipboard — paste with ⌘V / Ctrl+V. Feedback in ${settings.feedbackDelayMinutes} min.`,
          "success"
        );
        return;
      }

      setStatus(
        `Opened search. We'll ask for feedback in ${settings.feedbackDelayMinutes} min.`,
        "success"
      );
    }
  );
}

async function loadPendingFeedback() {
  chrome.runtime.sendMessage({ type: "getPendingFeedback" }, (response) => {
    const items = response?.items || [];
    const dueItems = items.filter(
      (item) => Date.now() >= item.feedbackDueAt
    );

    if (dueItems.length === 0) {
      feedbackSection.classList.add("hidden");
      activeFeedbackSession = null;
      return;
    }

    activeFeedbackSession = dueItems[0];
    feedbackQuery.textContent = activeFeedbackSession.query;
    feedbackSection.classList.remove("hidden");
  });
}

async function handleFeedback(usefulRoute) {
  if (!activeFeedbackSession) {
    return;
  }

  chrome.runtime.sendMessage(
    {
      type: "submitFeedback",
      sessionId: activeFeedbackSession.id,
      usefulRoute,
    },
    (response) => {
      if (chrome.runtime.lastError || !response?.ok) {
        setStatus("Could not save feedback.", "error");
        return;
      }

      setStatus("Thanks for the feedback!", "success");
      feedbackSection.classList.add("hidden");
      activeFeedbackSession = null;
      loadPendingFeedback();
    }
  );
}

queryInput.addEventListener("input", autoResizeTextarea);

queryInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    classifyBtn.click();
  }
});

classifyBtn.addEventListener("click", async () => {
  readSettingsFromUI();
  await persistSettings();

  const query = queryInput.value.trim();
  if (!query) {
    setStatus("Enter a query to classify.", "error");
    return;
  }

  classifyBtn.disabled = true;
  setStatus("Classifying…");

  try {
    const result = await classifyQuery(query, settings.apiBaseUrl);
    renderClassification(result);
    setStatus("Choose Search or LLM to continue.", "success");
  } catch (error) {
    resultSection.classList.add("hidden");
    currentClassification = null;
    setStatus(`Could not reach API: ${error.message}`, "error");
  } finally {
    classifyBtn.disabled = false;
  }
});

openSearchBtn.addEventListener("click", () => openRoute("search"));
openLlmBtn.addEventListener("click", () => openRoute("llm"));

document.querySelectorAll("[data-useful]").forEach((button) => {
  button.addEventListener("click", () => {
    handleFeedback(button.dataset.useful);
  });
});

[
  apiUrlInput,
  feedbackDelayInput,
  browserSelect,
  browserCustomInput,
  llmSelect,
  llmCustomInput,
].forEach((element) => {
  element.addEventListener("change", persistSettings);
  element.addEventListener("input", persistSettings);
});

browserSelect.addEventListener("change", () => {
  browserCustomInput.classList.toggle(
    "hidden",
    browserSelect.value !== "custom"
  );
});

llmSelect.addEventListener("change", () => {
  llmCustomInput.classList.toggle("hidden", llmSelect.value !== "custom");
});

async function init() {
  settings = await loadSettings();
  applySettingsToUI();
  autoResizeTextarea();
  loadPendingFeedback();
}

init();
