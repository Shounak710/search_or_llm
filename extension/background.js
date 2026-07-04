const FEEDBACK_ALARM_PREFIX = "feedback:";
const PENDING_FEEDBACK_KEY = "pendingFeedback";

async function getPendingFeedback() {
  const data = await chrome.storage.local.get(PENDING_FEEDBACK_KEY);
  return data[PENDING_FEEDBACK_KEY] || [];
}

async function setPendingFeedback(items) {
  await chrome.storage.local.set({ [PENDING_FEEDBACK_KEY]: items });
}

async function scheduleFeedback(session, delayMinutes) {
  const alarmName = `${FEEDBACK_ALARM_PREFIX}${session.id}`;
  const dueAt = Date.now() + delayMinutes * 60 * 1000;

  const pending = await getPendingFeedback();
  pending.push({ ...session, feedbackDueAt: dueAt });
  await setPendingFeedback(pending);

  await chrome.alarms.create(alarmName, { when: dueAt });
}

async function removePendingFeedback(sessionId) {
  const pending = await getPendingFeedback();
  await setPendingFeedback(pending.filter((item) => item.id !== sessionId));
}

async function showFeedbackNotification(session) {
  const snippet =
    session.query.length > 80
      ? `${session.query.slice(0, 77)}...`
      : session.query;

  await chrome.notifications.create(session.id, {
    type: "basic",
    iconUrl: "icon.png",
    title: "How did routing work?",
    message: `Which was more useful for "${snippet}"?`,
    buttons: [
      { title: "Search" },
      { title: "LLM" },
      { title: "Skip" },
    ],
    requireInteraction: true,
  });
}

async function submitFeedbackFromBackground(session, usefulRoute) {
  const data = await chrome.storage.sync.get("routingSettings");
  const apiBaseUrl = data.routingSettings?.apiBaseUrl || "http://127.0.0.1:5000";

  const response = await fetch(`${apiBaseUrl}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: session.query,
      predicted_route: session.predictedRoute,
      chosen_route: session.chosenRoute,
      useful_route: usefulRoute,
      manual_override: session.manualOverride,
      classified_at: session.classifiedAt,
    }),
  });

  if (!response.ok) {
    throw new Error(`Feedback failed (${response.status})`);
  }
}

async function handleFeedbackChoice(sessionId, usefulRoute) {
  const pending = await getPendingFeedback();
  const session = pending.find((item) => item.id === sessionId);
  if (!session) {
    return;
  }

  if (usefulRoute !== "skip") {
    try {
      await submitFeedbackFromBackground(session, usefulRoute);
    } catch (error) {
      console.error("Failed to submit feedback:", error);
    }
  }

  await removePendingFeedback(sessionId);
  await chrome.alarms.clear(`${FEEDBACK_ALARM_PREFIX}${sessionId}`);
  await chrome.notifications.clear(sessionId);
}

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (!alarm.name.startsWith(FEEDBACK_ALARM_PREFIX)) {
    return;
  }

  const sessionId = alarm.name.slice(FEEDBACK_ALARM_PREFIX.length);
  const pending = await getPendingFeedback();
  const session = pending.find((item) => item.id === sessionId);

  if (session) {
    await showFeedbackNotification(session);
  }
});

chrome.notifications.onButtonClicked.addListener(async (notificationId, buttonIndex) => {
  if (buttonIndex === 0) {
    await handleFeedbackChoice(notificationId, "search");
  } else if (buttonIndex === 1) {
    await handleFeedbackChoice(notificationId, "llm");
  } else {
    await handleFeedbackChoice(notificationId, "skip");
  }
});

chrome.notifications.onClicked.addListener(async (notificationId) => {
  await chrome.action.openPopup();
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "scheduleFeedback") {
    scheduleFeedback(message.session, message.delayMinutes)
      .then(() => sendResponse({ ok: true }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message.type === "submitFeedback") {
    handleFeedbackChoice(message.sessionId, message.usefulRoute)
      .then(() => sendResponse({ ok: true }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message.type === "getPendingFeedback") {
    getPendingFeedback()
      .then((items) => sendResponse({ items }))
      .catch((error) => sendResponse({ items: [], error: error.message }));
    return true;
  }
});
