document.getElementById("submit").addEventListener("click", async () => {
  const query = document.getElementById("query").value;

  const response = await fetch("http://localhost:8000/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query })
  });

  const data = await response.json();

  document.getElementById("result").innerHTML =
    `Routed to: <b>${data.route}</b><br>
     Confidence: ${data.confidence.toFixed(2)}<br>
     Energy Saved: ${data.energy_saved_estimate} kWh`;

  if (data.route === "search") {
    window.open(`https://www.google.com/search?q=${encodeURIComponent(query)}`);
  } else {
    window.open(`https://your-llm-page.com?q=${encodeURIComponent(query)}`);
  }
});