import { classify, loadModel } from "./model_browser.js";

const textarea = document.getElementById("query");

textarea.addEventListener("input", () => {
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + "px";
});

document.getElementById("submit").addEventListener("click", async () => {
  const queryInput = document.getElementById("query");
  const resultContainer = document.getElementById("result");

  const query = queryInput.value.trim();
  if (!query) {
    resultContainer.innerHTML = "Please enter a query.";
    return;
  }

  try {
    // Ensure the model is loaded before classifying
    await loadModel();

    const result = classify(query);
    console.log("classification result", result);

    if (!result || typeof result.route !== "string" || typeof result.confidence !== "number") {
      resultContainer.innerHTML = "Error: Invalid classification result.";
      return;
    }

    resultContainer.innerHTML =
      `Routed to: <b>${result.route}</b><br>` +
      `Confidence: ${result.confidence.toFixed(2)}<br>`;
      // Energy Saved: ${result.energy_saved_estimate} kWh`;

    const encodedQuery = encodeURIComponent(query);
    // if (result.route === "search") {
    //   window.open(`https://www.google.com/search?q=${encodedQuery}`);
    // } else {
    //   window.open(`https://your-llm-page.com?q=${encodedQuery}`);
    // }
  } catch (error) {
    console.error("Error during classification:", error);
    resultContainer.innerHTML = "An error occurred while routing your query." + error;
  }
});