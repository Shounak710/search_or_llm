export async function classifyQuery(query, apiBaseUrl) {
  const response = await fetch(`${apiBaseUrl}/classify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Classification failed (${response.status})`);
  }

  return response.json();
}

export async function submitFeedback(payload, apiBaseUrl) {
  const response = await fetch(`${apiBaseUrl}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Feedback failed (${response.status})`);
  }

  return response.json();
}
