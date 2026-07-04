export const DEFAULT_SETTINGS = {
  apiBaseUrl: "http://127.0.0.1:5000",
  searchEngine: "google",
  llm: "openai",
  customSearchUrl: "",
  customLlmUrl: "",
  feedbackDelayMinutes: 3,
};

export async function loadSettings() {
  if (typeof chrome === "undefined" || !chrome.storage?.sync) {
    return { ...DEFAULT_SETTINGS };
  }

  const data = await chrome.storage.sync.get("routingSettings");
  return { ...DEFAULT_SETTINGS, ...(data.routingSettings || {}) };
}

export async function saveSettings(settings) {
  if (typeof chrome === "undefined" || !chrome.storage?.sync) {
    return;
  }

  await chrome.storage.sync.set({ routingSettings: settings });
}

export function getSearchUrl(query, settings) {
  const encoded = encodeURIComponent(query);

  switch (settings.searchEngine) {
    case "duckduckgo":
      return `https://duckduckgo.com/?q=${encoded}`;
    case "bing":
      return `https://www.bing.com/search?q=${encoded}`;
    case "custom":
      return (
        (settings.customSearchUrl || "").replace("{q}", encoded) ||
        `${settings.customSearchUrl || ""}${encoded}`
      );
    case "google":
    default:
      return `https://www.google.com/search?q=${encoded}`;
  }
}

export function getLlmUrl(query, settings) {
  const encoded = encodeURIComponent(query);

  switch (settings.llm) {
    case "claude":
      return "https://claude.ai/new";
    case "localhost":
      return `http://localhost:8000/?q=${encoded}`;
    case "custom":
      return (
        (settings.customLlmUrl || "").replace("{q}", encoded) ||
        `${settings.customLlmUrl || ""}${encoded}`
      );
    case "openai":
    default:
      return "https://chat.openai.com/";
  }
}
