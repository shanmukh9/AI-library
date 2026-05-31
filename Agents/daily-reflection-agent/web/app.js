const domains = {
  "Fitness and Energy": {
    keywords: ["walk", "gym", "workout", "exercise", "run", "steps", "sleep", "water", "food", "diet", "health", "fitness", "meditation", "yoga"],
    nextRep: "Take a 10-minute walk or mobility session before the day gets noisy."
  },
  "AI Career and Building": {
    keywords: ["ai", "agent", "agents", "python", "project", "build", "code", "github", "career", "resume", "learn", "podcast", "course", "model"],
    nextRep: "Ship one small artifact: a script, prompt, README, demo, or commit."
  },
  "Discipline and Deep Work": {
    keywords: ["focus", "deep", "work", "study", "procrastination", "scroll", "phone", "routine", "task", "tasks", "deadline", "planned"],
    nextRep: "Do one 25-minute block with the phone away and one written outcome."
  },
  "Mental Strength and Emotion": {
    keywords: ["stress", "anxiety", "fear", "confidence", "comfort", "zone", "mood", "emotion", "grateful", "gratitude", "satisfied", "sad", "happy", "tired", "mental"],
    nextRep: "Name the feeling, choose the smallest courageous action, then do it for five minutes."
  },
  "Communication and Relationships": {
    keywords: ["call", "message", "talk", "meeting", "communicate", "communication", "friend", "family", "colleague", "share", "write", "speaking"],
    nextRep: "Send one clear message or speak one honest sentence you would normally avoid."
  }
};

const comfortWords = ["watched", "scroll", "scrolled", "thinking", "thought", "planning", "plan", "maybe", "later", "course", "video", "podcast"];
const actionWords = ["built", "created", "finished", "completed", "shipped", "wrote", "coded", "practiced", "exercised", "walked", "ran", "read", "called", "shared", "cleaned", "prepared"];
const $ = (id) => document.getElementById(id);
const sessionToken = window.__REFLECTION_AGENT_TOKEN__ || "";
let currentReflection = null;
let currentReflectionId = null;
let currentGoals = [];

function hasServer() {
  return window.location.protocol !== "file:";
}

function wordsFor(text) {
  return new Set((text.toLowerCase().match(/[a-z]+/g) || []));
}

function splitPoints(text) {
  const lines = text
    .split(/\n+/)
    .map((line) => line.trim().replace(/^[-*\d.)\s]+/, ""))
    .filter(Boolean);

  if (lines.length > 1) return lines;
  return text
    .split(/(?<=[.!?])\s+|,\s+(?=(?:and\s+)?i\b)/i)
    .map((line) => line.trim().replace(/^[-*\d.)\s]+/, ""))
    .filter(Boolean);
}

function classify(points) {
  const buckets = Object.fromEntries(Object.keys(domains).map((domain) => [domain, []]));
  points.forEach((point) => {
    const pointWords = wordsFor(point);
    Object.entries(domains).forEach(([domain, config]) => {
      if (config.keywords.some((word) => pointWords.has(word))) {
        buckets[domain].push(point);
      }
    });
  });
  return buckets;
}

function scoreDay(points, buckets) {
  const allWords = wordsFor(points.join(" "));
  const actionHits = actionWords.filter((word) => allWords.has(word)).length;
  const comfortHits = comfortWords.filter((word) => allWords.has(word)).length;
  const coveredDomains = Object.values(buckets).filter((items) => items.length).length;

  let score = 35;
  score += Math.min(25, coveredDomains * 5);
  score += Math.min(20, actionHits * 4);
  score += Math.min(10, points.length * 2);
  score -= Math.min(15, Math.max(0, comfortHits - actionHits) * 3);

  return {
    score: Math.max(20, Math.min(95, score)),
    actionHits,
    comfortHits,
    coveredDomains
  };
}

function scoreLabel(score) {
  if (score >= 85) return "Strong day";
  if (score >= 70) return "Solid day";
  if (score >= 55) return "Mixed but useful day";
  return "Comfort-zone day";
}

function makeSummary(points, buckets) {
  const activeDomains = Object.entries(buckets)
    .filter(([, items]) => items.length)
    .map(([domain]) => domain);

  if (!activeDomains.length) {
    return {
      title: "You created the first signal.",
      text: "The notes are light, but the act of reflecting is already a rep. Tomorrow needs one clearer action that your future self can point to."
    };
  }

  const focus = activeDomains.slice(0, 2).join(" and ");
  return {
    title: `Today was mainly about ${focus}.`,
    text: "Under the surface, you are not only asking for productivity. You are asking for evidence that you are becoming stronger, calmer, and more consistent. The move is to turn one piece of awareness into one visible action."
  };
}

function keyPattern(buckets, details) {
  if (buckets["AI Career and Building"].length && details.comfortHits >= details.actionHits) {
    return "Your AI ambition is alive, but some of it is still sitting in consumption mode. The next identity rep is simple: learner becomes builder on the same day.";
  }
  if (!buckets["Fitness and Energy"].length) {
    return "Your mind wants progress, but the body did not get a clear vote. Fitness is not separate from ambition; it is the battery for ambition.";
  }
  if (!buckets["Discipline and Deep Work"].length) {
    return "There was movement, but the deep-work signal is weak. One protected focus block would make tomorrow feel more owned.";
  }
  return "You are touching multiple growth areas. The next level is consistency: fewer intentions, more repeated small reps.";
}

function gratitude(points) {
  const text = points.join(" ").toLowerCase();
  if (text.includes("holiday") || text.includes("free")) {
    return "Be grateful for free time today. It is not empty space; it is raw material for becoming.";
  }
  if (/(completed|done|finished|task)/.test(text)) {
    return "Be grateful that you kept some promises today. Small responsibilities protect self-trust.";
  }
  if (/(learn|podcast|ai|read|watched)/.test(text)) {
    return "Be grateful for curiosity. It is one of the strongest assets in a changing career.";
  }
  return "Be grateful for the record itself. A noticed day is easier to improve than a forgotten one.";
}

function challenge(buckets, details) {
  if (details.comfortHits > details.actionHits) {
    return "Tomorrow, earn your content. Build or practice for 25 minutes before watching anything educational.";
  }
  if (!buckets["Fitness and Energy"].length) {
    return "Do not negotiate with mood tomorrow. Move your body for 10 minutes before the first long screen session.";
  }
  return "Keep the standard small but real. One visible output beats a large plan that stays private.";
}

function tomorrowAction(buckets) {
  if (buckets["AI Career and Building"].length) {
    return domains["AI Career and Building"].nextRep;
  }
  if (!buckets["Fitness and Energy"].length) {
    return domains["Fitness and Energy"].nextRep;
  }
  if (!buckets["Discipline and Deep Work"].length) {
    return domains["Discipline and Deep Work"].nextRep;
  }
  return "Pick one useful uncomfortable task and finish the smallest version before noon.";
}

function habitCue(buckets, details) {
  if (details.actionHits >= 3) {
    return "Habit seed: attach your action energy to a fixed time. Keep the first version under 10 minutes so it repeats.";
  }
  if (buckets["AI Career and Building"].length) {
    return "Habit seed: every AI input must produce one artifact, even if it is tiny.";
  }
  return "Habit seed: close each day with two minutes of reflection and one next rep.";
}

function buildReflection(text) {
  const points = splitPoints(text);
  const buckets = classify(points);
  const details = scoreDay(points, buckets);
  const summary = makeSummary(points, buckets);

  return {
    score: details.score,
    label: scoreLabel(details.score),
    title: summary.title,
    summary: `${summary.text} ${gratitude(points)}`,
    pattern: keyPattern(buckets, details),
    challenge: `${challenge(buckets, details)} ${habitCue(buckets, details)}`,
    tomorrow: tomorrowAction(buckets),
    scoreReason: `Score reflects ${details.coveredDomains} growth areas, ${details.actionHits} action signals, and ${details.comfortHits} comfort-zone signals.`,
    builderSignal: Boolean(buckets["AI Career and Building"].length),
    fitnessSignal: Boolean(buckets["Fitness and Energy"].length),
    comfortSignal: details.comfortHits > details.actionHits,
    emotionalSignal: Boolean(buckets["Mental Strength and Emotion"].length),
    source: "offline"
  };
}

function normalizeReflection(reflection) {
  return {
    notes: reflection.notes || "",
    score: Number(reflection.score) || 60,
    label: reflection.label || "Reflection ready",
    title: reflection.title || "Today has a useful signal.",
    summary: reflection.summary || "",
    pattern: reflection.pattern || "",
    challenge: reflection.challenge || "",
    tomorrow: reflection.tomorrow || "Choose one small promise for tomorrow.",
    scoreReason: reflection.scoreReason || "Score reflects effort, output, recovery, consistency, and promise follow-through.",
    source: reflection.source || "lm-studio",
    model: reflection.model || "",
    reflectionDepth: reflection.reflectionDepth || getSelectedReflectionDepth(),
    ragMode: reflection.ragMode || getSelectedRagMode(),
    ragUsed: Boolean(reflection.ragUsed),
    ragDebug: Array.isArray(reflection.ragDebug) ? reflection.ragDebug : [],
    builderSignal: Boolean(reflection.builderSignal),
    fitnessSignal: Boolean(reflection.fitnessSignal),
    comfortSignal: Boolean(reflection.comfortSignal),
    emotionalSignal: Boolean(reflection.emotionalSignal)
  };
}

function render(reflection) {
  currentReflection = normalizeReflection(reflection);
  setActiveTab("reflect");
  $("scoreValue").textContent = currentReflection.score;
  $("scoreLabel").textContent = currentReflection.label;
  $("scoreReason").textContent = currentReflection.scoreReason;
  $("summaryTitle").textContent = currentReflection.title;
  $("summaryText").textContent = currentReflection.summary;
  $("patternText").textContent = currentReflection.pattern;
  $("challengeText").textContent = currentReflection.challenge;
  $("tomorrowText").textContent = currentReflection.tomorrow;
  $("scoreRing").style.background = `conic-gradient(var(--sage) ${currentReflection.score * 3.6}deg, #dff5eb 0deg)`;
  $("reviewPanel").hidden = false;
  $("reviewAnswer").hidden = true;
  updateLocalStatus(currentReflection);
  renderRagDebug(currentReflection.ragDebug);
}

function notesHash(text) {
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) {
    hash = (hash << 5) - hash + text.charCodeAt(index);
    hash |= 0;
  }
  return String(hash);
}

function getCache() {
  return JSON.parse(localStorage.getItem("reflectionCache") || "{}");
}

function setCache(hash, reflection) {
  const cache = getCache();
  cache[hash] = reflection;
  const entries = Object.entries(cache).slice(-10);
  localStorage.setItem("reflectionCache", JSON.stringify(Object.fromEntries(entries)));
}

async function apiGet(path) {
  const response = await fetch(path, {
    headers: {
      "X-Reflection-Agent-Token": sessionToken
    }
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function apiPost(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Reflection-Agent-Token": sessionToken
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error || `Request failed: ${response.status}`);
  }
  return response.json();
}

async function buildAiReflection(text) {
  const previous = previousReflectionForPromise();
  const promiseStatus = previous ? getPromiseStatus()[previous.id] || "" : "";
  const includeRagDebug = $("ragDebugToggle").checked;
  const ragMode = getSelectedRagMode();
  const reflectionDepth = getSelectedReflectionDepth();
  const hash = notesHash(`${text}|${previous?.tomorrow || ""}|${promiseStatus}|${ragMode}|${reflectionDepth}`);
  const cache = getCache();
  if (!includeRagDebug && cache[hash]) {
    return { ...cache[hash], label: `${cache[hash].label} · cached` };
  }

  const response = await fetch("/api/reflect", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Reflection-Agent-Token": sessionToken
    },
    body: JSON.stringify({
      notes: text,
      previousPromise: previous?.tomorrow || "",
      previousPromiseStatus: promiseStatus,
      includeRagDebug,
      ragMode,
      reflectionDepth,
      goals: currentGoals
    })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const detail = error.detail ? ` ${error.detail}` : "";
    throw new Error(`${error.error || "Local AI reflection failed."}${detail}`);
  }

  const reflection = await response.json();
  if (!includeRagDebug) {
    setCache(hash, reflection);
  }
  return reflection;
}

async function buildWeeklyReview() {
  const history = getHistory().slice(-7);
  if (history.length < 2) {
    throw new Error("Save at least two reflections before running a weekly review.");
  }

  const response = await fetch("/api/weekly", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Reflection-Agent-Token": sessionToken
    },
    body: JSON.stringify({
      reflections: history,
      promiseStatus: getPromiseStatus()
    })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const detail = error.detail ? ` ${error.detail}` : "";
    throw new Error(`${error.error || "Weekly review failed."}${detail}`);
  }

  return response.json();
}

function getHistory() {
  return JSON.parse(localStorage.getItem("reflectionHistory") || "[]");
}

function setHistory(history) {
  localStorage.setItem("reflectionHistory", JSON.stringify(history.slice(-60)));
}

function getPromiseStatus() {
  return JSON.parse(localStorage.getItem("promiseStatus") || "{}");
}

function setPromiseStatus(status) {
  localStorage.setItem("promiseStatus", JSON.stringify(status));
}

function todayKey(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}

async function saveReflection(options = {}) {
  if (!currentReflection || $("scoreValue").textContent === "--") {
    $("notes").focus();
    return;
  }

  const payload = {
    id: currentReflectionId || (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}`),
    date: new Date().toISOString(),
    day: todayKey(),
    ...currentReflection,
    notes: $("notes").value
  };
  $("saveBtn").disabled = true;
  try {
    if (hasServer()) {
      const saved = await apiPost("/api/reflections", payload);
      const history = getHistory();
      const savedReflection = saved.reflection || payload;
      currentReflectionId = savedReflection.id;
      const existingIndex = history.findIndex((item) => item.id === savedReflection.id);
      if (existingIndex >= 0) {
        history[existingIndex] = savedReflection;
      } else {
        history.push(savedReflection);
      }
      setHistory(history);
      await loadAnalytics();
    } else {
      const history = getHistory();
      currentReflectionId = payload.id;
      const existingIndex = history.findIndex((item) => item.id === payload.id);
      if (existingIndex >= 0) {
        history[existingIndex] = payload;
      } else {
        history.push(payload);
      }
      setHistory(history);
    }
    renderHistory();
    renderPromiseCheck();
    $("saveBtn").textContent = options.automatic ? "Auto-saved" : "Saved";
  } catch (error) {
    $("saveBtn").textContent = "Save failed";
  } finally {
    $("saveBtn").disabled = false;
    window.setTimeout(() => ($("saveBtn").textContent = "Save"), 1200);
  }
}

function renderHistory() {
  const history = getHistory().slice().reverse();
  const list = $("historyList");
  list.innerHTML = "";

  if (!history.length) {
    $("historySummary").textContent = "No saved reflections yet. Save one to start building memory.";
    return;
  }

  const average = Math.round(history.reduce((sum, item) => sum + Number(item.score || 0), 0) / history.length);
  const latestPromise = history[0].tomorrow || "No promise saved yet.";
  $("historySummary").textContent = `${history.length} saved · average score ${average}/100 · next promise: ${latestPromise}`;

  history.slice(0, 6).forEach((item) => {
    const card = document.createElement("article");
    card.className = "history-item";
    card.innerHTML = `
      <div class="history-topline">
        <span>${formatDate(item.date)}</span>
        <strong>${item.score}/100</strong>
      </div>
      <h3>${escapeHtml(item.title || "Reflection")}</h3>
      <p>${escapeHtml(item.pattern || item.summary || "")}</p>
    `;
    card.addEventListener("click", () => render(item));
    list.appendChild(card);
  });
}

function renderPromiseCheck() {
  const history = getHistory();
  const previous = previousReflectionForPromise();
  if (!previous || !previous.tomorrow) {
    $("promiseCheck").hidden = true;
    return;
  }

  const status = getPromiseStatus()[previous.id];
  $("promiseCheck").hidden = false;
  $("previousPromise").textContent = previous.tomorrow;
  $("keptPromiseBtn").classList.toggle("selected", status === "kept");
  $("missedPromiseBtn").classList.toggle("selected", status === "missed");
}

async function markPromise(status) {
  const previous = previousReflectionForPromise();
  if (!previous) return;
  const promiseStatus = getPromiseStatus();
  promiseStatus[previous.id] = status;
  setPromiseStatus(promiseStatus);
  if (hasServer()) {
    try {
      await apiPost("/api/promise", { reflectionId: previous.id, status });
      await loadAnalytics();
    } catch (error) {
      $("localStatus").textContent = "Promise saved in browser only";
    }
  }
  renderPromiseCheck();
}

function previousReflectionForPromise() {
  const history = getHistory();
  const today = todayKey();
  for (let index = history.length - 1; index >= 0; index -= 1) {
    if (history[index].day !== today) {
      return history[index];
    }
  }
  return null;
}

function exportHistory() {
  const payload = {
    exportedAt: new Date().toISOString(),
    reflections: getHistory(),
    promiseStatus: getPromiseStatus()
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `daily-reflections-${todayKey()}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

async function exportAllData() {
  if (hasServer()) {
    const payload = await apiGet("/api/privacy/export");
    downloadJson(payload, `daily-reflection-agent-export-${todayKey()}.json`);
    return;
  }
  exportHistory();
}

function downloadJson(payload, filename) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

async function importHistory(file) {
  if (!file) return;
  const text = await file.text();
  const payload = JSON.parse(text);
  const imported = Array.isArray(payload) ? payload : payload.reflections || [];
  if (!Array.isArray(imported)) return;
  setHistory([...getHistory(), ...imported]);
  if (payload.promiseStatus) {
    setPromiseStatus({ ...getPromiseStatus(), ...payload.promiseStatus });
  }
  renderHistory();
  renderPromiseCheck();
}

function clearHistory() {
  const confirmed = window.confirm("Clear saved reflections from this browser?");
  if (!confirmed) return;
  localStorage.removeItem("reflectionHistory");
  localStorage.removeItem("promiseStatus");
  localStorage.removeItem("reflectionCache");
  renderHistory();
  renderPromiseCheck();
  renderWeeklyPlaceholder();
}

async function clearAllData() {
  const confirmed = window.confirm("Delete all local reflections, goals, promise status, and cache for this app?");
  if (!confirmed) return;
  if (hasServer()) {
    await apiPost("/api/privacy/clear", {});
  }
  localStorage.removeItem("reflectionHistory");
  localStorage.removeItem("promiseStatus");
  localStorage.removeItem("reflectionCache");
  currentGoals = [];
  renderHistory();
  renderPromiseCheck();
  renderGoals();
  renderWeeklyPlaceholder();
  renderAnalyticsPlaceholder();
}

function buildWeeklyFallback(history) {
  const recent = history.slice(-7);
  if (!recent.length) {
    return {
      title: "Weekly review needs a little more signal.",
      summary: "Save a few reflections first. Pattern analysis becomes useful when the app can compare days.",
      repeatedPattern: "No repeated pattern yet.",
      builderSignal: "No builder signal yet.",
      comfortZone: "No comfort-zone signal yet.",
      experiment: "Save one reflection today and one tomorrow.",
      scoreTrend: "Not enough data yet."
    };
  }

  const average = Math.round(recent.reduce((sum, item) => sum + Number(item.score || 0), 0) / recent.length);
  const text = recent
    .map((item) => `${item.title} ${item.summary} ${item.pattern} ${item.challenge} ${item.tomorrow}`)
    .join(" ")
    .toLowerCase();
  const aiMentions = (text.match(/\b(ai|agent|build|project|code|artifact|github)\b/g) || []).length;
  const comfortMentions = (text.match(/\b(watched|course|video|later|comfort|stuck|avoid|procrastination)\b/g) || []).length;
  const fitnessMentions = (text.match(/\b(workout|walk|gym|fitness|exercise|sleep|energy)\b/g) || []).length;

  return {
    title: "Your week has a useful pattern.",
    summary: `Across ${recent.length} saved reflections, your average score is ${average}/100. The useful question is not whether the week was perfect, but which small behavior deserves repetition.`,
    repeatedPattern: fitnessMentions >= 2 ? "Health and energy are showing up as a foundation. Keep treating the body as the battery for ambition." : "The repeated signal is still forming. Save more reflections and make one anchor habit visible every day.",
    builderSignal: aiMentions >= 2 ? "AI builder energy is present. The next step is turning that energy into proof: tiny artifacts, commits, prompts, or demos." : "AI builder proof is still light in the saved reflections. Add one small artifact to the next week.",
    comfortZone: comfortMentions >= 2 ? "Comfort-zone language appears enough to pay attention. Watch for learning that feels productive but avoids shipping." : "Avoidance is not dominating the saved reflections, but keep the standard honest: visible output over private intention.",
    experiment: "For 7 days, create one tiny proof before consuming AI content: a note, script, prompt, README, or 20-minute build rep.",
    scoreTrend: `Current saved average: ${average}/100.`
  };
}

function renderWeeklyReview(review) {
  $("weeklyTitle").textContent = review.title || "This week has a pattern worth noticing.";
  $("weeklySummary").textContent = review.summary || "";
  $("weeklyPattern").textContent = review.repeatedPattern || "";
  $("weeklyBuilder").textContent = review.builderSignal || "";
  $("weeklyComfort").textContent = review.comfortZone || "";
  $("weeklyExperiment").textContent = review.experiment || "";
}

function renderWeeklyPlaceholder() {
  $("weeklyTitle").textContent = "Understand who you are becoming.";
  $("weeklySummary").textContent = "Save at least two reflections, then generate a weekly pattern review.";
  $("weeklyPattern").textContent = "Your strongest repeated signal will appear here.";
  $("weeklyBuilder").textContent = "Your AI builder proof will appear here.";
  $("weeklyComfort").textContent = "Avoidance or friction will appear here.";
  $("weeklyExperiment").textContent = "One small experiment will appear here.";
}

function renderAnalyticsPlaceholder() {
  $("metricAverage").textContent = "--";
  $("metricPromise").textContent = "--";
  $("metricBuilder").textContent = "--";
  $("metricComfort").textContent = "--";
}

function renderAnalytics(analytics) {
  $("metricAverage").textContent = analytics.reflectionCount ? `${analytics.averageScore}/100` : "--";
  $("metricPromise").textContent = analytics.promiseRate ? `${analytics.promiseRate}%` : "--";
  $("metricBuilder").textContent = analytics.reflectionCount ? String(analytics.builderDays) : "--";
  $("metricComfort").textContent = analytics.reflectionCount ? String(analytics.comfortDays) : "--";
}

async function loadAnalytics() {
  if (!hasServer()) {
    renderAnalytics(buildLocalAnalytics());
    return;
  }
  try {
    const payload = await apiGet("/api/analytics");
    renderAnalytics(payload.analytics);
  } catch (error) {
    renderAnalytics(buildLocalAnalytics());
  }
}

function buildLocalAnalytics() {
  const history = getHistory().slice(-14);
  if (!history.length) {
    return { reflectionCount: 0, averageScore: 0, promiseRate: 0, builderDays: 0, comfortDays: 0 };
  }
  const textItems = history.map((item) => `${item.notes || ""} ${item.summary || ""} ${item.pattern || ""}`.toLowerCase());
  return {
    reflectionCount: history.length,
    averageScore: Math.round(history.reduce((sum, item) => sum + Number(item.score || 0), 0) / history.length),
    promiseRate: 0,
    builderDays: textItems.filter((text) => /\b(ai|agent|code|github|project|build)\b/.test(text)).length,
    comfortDays: textItems.filter((text) => /\b(comfort|avoid|later|scroll|watched|video|course)\b/.test(text)).length
  };
}

function buildFollowupFallback(followupType) {
  const tomorrow = currentReflection?.tomorrow || "Choose one small action tomorrow.";
  if (followupType === "challenge_excuse") {
    return {
      title: "Name the negotiation",
      answer: "The likely excuse is that the task needs a perfect mood, long time block, or more clarity before starting. Treat that as the comfort-zone story, not the truth. Your job is to begin badly and briefly, then let momentum decide.",
      nextStep: "Set a 5-minute timer and start the smallest visible version."
    };
  }
  if (followupType === "watch_pattern") {
    return {
      title: "Watch the first avoidance move",
      answer: "Tomorrow, pay attention to the moment you switch from action into preparation, scrolling, or learning about the work instead of touching the work. That first switch is the pattern worth catching.",
      nextStep: "Write one sentence before opening any learning content."
    };
  }
  return {
    title: "Make it tiny enough to start",
    answer: `Do not treat tomorrow's promise as a project. Treat it as a starting ritual: open the place where the work happens, remove one friction point, and complete the first visible move.`,
    nextStep: tomorrow.length > 120 ? "Do the first 5 minutes of tomorrow's promise." : tomorrow
  };
}

async function runFollowup(followupType) {
  if (!currentReflection) {
    $("notes").focus();
    return;
  }

  const buttons = document.querySelectorAll("[data-followup]");
  buttons.forEach((button) => {
    button.disabled = true;
  });
  $("reviewPanel").hidden = false;
  $("reviewAnswer").hidden = false;
  $("reviewTitle").textContent = "Thinking with today's reflection...";
  $("reviewText").innerHTML = skeletonLines(["", "medium"]);
  $("reviewNextStep").textContent = "";

  try {
    const result = hasServer()
      ? await apiPost("/api/followup", {
          notes: currentReflection.notes || $("notes").value,
          reflection: currentReflection,
          followupType,
          goals: currentGoals
        })
      : buildFollowupFallback(followupType);
    renderFollowup(result);
  } catch (error) {
    renderFollowup(buildFollowupFallback(followupType));
  } finally {
    buttons.forEach((button) => {
      button.disabled = false;
    });
  }
}

function renderFollowup(result) {
  $("reviewAnswer").hidden = false;
  $("reviewTitle").textContent = result.title || "Make it actionable";
  $("reviewText").textContent = result.answer || "";
  $("reviewNextStep").textContent = result.nextStep ? `Next step: ${result.nextStep}` : "";
}

function renderGoals() {
  const list = $("goalList");
  list.innerHTML = "";
  if (!currentGoals.length) {
    currentGoals = [
      { area: "AI career", target: "Create visible AI project proof every week." },
      { area: "Fitness", target: "Protect energy with simple movement and recovery." },
      { area: "Discipline", target: "Turn intentions into small finished reps." }
    ];
  }
  currentGoals.forEach((goal, index) => {
    const item = document.createElement("article");
    item.className = "goal-item";
    item.innerHTML = `
      <label>Area
        <input data-goal-area="${index}" value="${escapeHtml(goal.area || "")}" maxlength="80">
      </label>
      <label>Target
        <input data-goal-target="${index}" value="${escapeHtml(goal.target || "")}" maxlength="300">
      </label>
      <button class="secondary compact danger" data-remove-goal="${index}" type="button">Remove</button>
    `;
    list.appendChild(item);
  });
}

function readGoalsFromUi() {
  return currentGoals
    .map((goal, index) => ({
      id: goal.id,
      area: document.querySelector(`[data-goal-area="${index}"]`)?.value.trim() || "",
      target: document.querySelector(`[data-goal-target="${index}"]`)?.value.trim() || ""
    }))
    .filter((goal) => goal.area && goal.target);
}

async function loadGoals() {
  if (hasServer()) {
    try {
      const payload = await apiGet("/api/goals");
      currentGoals = payload.goals || [];
    } catch (error) {
      currentGoals = JSON.parse(localStorage.getItem("reflectionGoals") || "[]");
    }
  } else {
    currentGoals = JSON.parse(localStorage.getItem("reflectionGoals") || "[]");
  }
  renderGoals();
}

async function saveGoals() {
  currentGoals = readGoalsFromUi();
  if (hasServer()) {
    try {
      const payload = await apiPost("/api/goals", { goals: currentGoals });
      currentGoals = payload.goals || currentGoals;
    } catch (error) {
      $("localStatus").textContent = "Goals saved in browser only";
    }
  }
  localStorage.setItem("reflectionGoals", JSON.stringify(currentGoals));
  renderGoals();
  $("saveGoalsBtn").textContent = "Saved";
  window.setTimeout(() => ($("saveGoalsBtn").textContent = "Save goals"), 1100);
}

async function loadServerMemory() {
  if (!hasServer()) {
    renderHistory();
    renderPromiseCheck();
    await loadGoals();
    await loadAnalytics();
    return;
  }
  try {
    const payload = await apiGet("/api/reflections");
    if (Array.isArray(payload.reflections)) {
      setHistory(payload.reflections.slice().reverse());
    }
    if (payload.promiseStatus) {
      setPromiseStatus(payload.promiseStatus);
    }
  } catch (error) {
    $("localStatus").textContent = "Browser memory only";
  }
  renderHistory();
  renderPromiseCheck();
  await loadGoals();
  await loadAnalytics();
}

function renderRagDebug(chunks) {
  const panel = $("ragDebugPanel");
  const list = $("ragDebugList");
  list.innerHTML = "";

  if (!$("ragDebugToggle").checked || !chunks.length) {
    panel.hidden = true;
    return;
  }

  const mode = currentReflection?.ragMode || getSelectedRagMode();
  $("ragDebugTitle").textContent = mode === "vector" ? "Knowledge used by Vector RAG" : "Knowledge used by Keyword RAG";

  chunks.forEach((chunk, index) => {
    const scoreLabel = mode === "vector" ? "similarity" : "score";
    const item = document.createElement("article");
    item.className = "rag-debug-item";
    item.innerHTML = `
      <div class="rag-debug-topline">
        <span>${index + 1}. ${escapeHtml(chunk.source || "knowledge")}</span>
        <strong>${scoreLabel}: ${Number(chunk.score || 0).toFixed(mode === "vector" ? 4 : 2)}</strong>
      </div>
      <h3>${escapeHtml(chunk.heading || "General")}</h3>
      <p>${escapeHtml(chunk.excerpt || "")}</p>
    `;
    list.appendChild(item);
  });

  panel.hidden = false;
}

function updateLocalStatus(reflection) {
  if (window.location.protocol === "file:") {
    $("localStatus").textContent = "Offline fallback";
    return;
  }
  if (reflection.source === "lm-studio") {
    if (reflection.ragUsed) {
      const mode = reflection.ragMode === "vector" ? "Vector RAG" : "Keyword RAG";
      const depth = reflection.reflectionDepth === "fast" ? "Fast" : "Deep";
      $("localStatus").textContent = reflection.model ? `${depth} local AI + ${mode}: ${reflection.model}` : `${depth} local AI + ${mode} connected`;
      return;
    }
    const depth = reflection.reflectionDepth === "fast" ? "Fast" : "Deep";
    $("localStatus").textContent = reflection.model ? `${depth} local AI: ${reflection.model}` : `${depth} local AI connected`;
    return;
  }
  $("localStatus").textContent = "Offline fallback";
}

function getSelectedRagMode() {
  return document.querySelector('input[name="ragMode"]:checked')?.value || "keyword";
}

function getSelectedReflectionDepth() {
  return document.querySelector('input[name="reflectionDepth"]:checked')?.value || "fast";
}

function updateRagModeHint() {
  const mode = getSelectedRagMode();
  $("ragModeHint").textContent =
    mode === "vector"
      ? "Vector uses local embeddings to match meaning. Build data/vector_index.json before using it."
      : "Keyword matches exact terms and headings. It is fast and transparent.";
}

function updateReflectionDepthHint() {
  const mode = getSelectedReflectionDepth();
  $("reflectionDepthHint").textContent =
    mode === "fast"
      ? "Fast skips extra context and asks for a tighter answer. Use it for daily logging."
      : "Deep uses RAG, goals, and recent history. Better insight, slower generation.";
  syncAdvancedControls();
}

function syncAdvancedControls() {
  const isFast = getSelectedReflectionDepth() === "fast";
  document.querySelectorAll('input[name="ragMode"]').forEach((input) => {
    input.disabled = isFast;
  });
  $("ragDebugToggle").disabled = isFast;
  if (isFast) {
    $("ragModeHint").textContent = "RAG is paused in Fast mode. Choose Deep when you want personal knowledge retrieval.";
    $("ragDebugToggle").checked = false;
    $("ragDebugPanel").hidden = true;
  } else {
    updateRagModeHint();
  }
}

function setActiveTab(tabName) {
  document.querySelectorAll(".tab-button").forEach((button) => {
    const isActive = button.dataset.tab === tabName;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });

  document.querySelectorAll(".tab-panel").forEach((panel) => {
    const isActive = panel.dataset.panel === tabName;
    panel.classList.toggle("active", isActive);
    panel.hidden = !isActive;
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function reflect() {
  const text = $("notes").value.trim();
  if (!text) {
    $("notes").focus();
    return;
  }

  $("reflectBtn").disabled = true;
  $("reflectBtn").textContent = "Reflecting...";
  currentReflectionId = null;
  setLoadingState(true);

  try {
    if (window.location.protocol === "file:") {
      render(buildReflection(text));
    } else {
      render(await buildAiReflection(text));
    }
    await saveReflection({ automatic: true });
  } catch (error) {
    const fallback = buildReflection(text);
    fallback.label = "Offline fallback";
    fallback.title = "Local AI was not reachable, so I used the built-in reflection.";
    fallback.summary = `${fallback.summary} The local model call failed, but your notes were still converted into a basic local reflection.`;
    render(fallback);
    await saveReflection({ automatic: true });
  } finally {
    setLoadingState(false);
    $("reflectBtn").disabled = false;
    $("reflectBtn").textContent = "Reflect";
  }
}

function setLoadingState(isLoading) {
  document.body.classList.toggle("is-reflecting", isLoading);
  $("loadingBanner").hidden = !isLoading;
  if (isLoading) {
    $("scoreLabel").textContent = "Local model is thinking...";
    $("scoreReason").textContent =
      getSelectedReflectionDepth() === "fast"
        ? "Using a compact prompt for a faster daily reflection."
        : "Retrieving memory, reading goals, and preparing the reflection.";
    $("summaryTitle").textContent = "Building your reflection...";
    $("summaryText").innerHTML = skeletonLines(["medium", "", "short"]);
    $("patternText").innerHTML = skeletonLines(["", "medium"]);
    $("challengeText").innerHTML = skeletonLines(["", "short"]);
    $("tomorrowText").innerHTML = skeletonLines(["medium"]);
  }
}

function skeletonLines(widths) {
  return `
    <span class="skeleton-lines" aria-hidden="true">
      ${widths.map((width) => `<span class="skeleton-line ${width}"></span>`).join("")}
    </span>
  `;
}

async function reviewWeek() {
  const history = getHistory().slice(-7);
  if (history.length < 2) {
    const fallback = buildWeeklyFallback(history);
    if (!history.length) {
      renderWeeklyReview(fallback);
      return;
    }
    renderWeeklyReview(fallback);
    $("weeklySummary").textContent = "Save at least two reflections before the weekly analyst has enough signal.";
    return;
  }

  $("weeklyBtn").disabled = true;
  $("weeklyBtn").textContent = "Reviewing...";

  try {
    if (window.location.protocol === "file:") {
      renderWeeklyReview(buildWeeklyFallback(history));
    } else {
      renderWeeklyReview(await buildWeeklyReview());
    }
  } catch (error) {
    const fallback = buildWeeklyFallback(history);
    fallback.summary = `${fallback.summary} Local AI weekly review was unavailable, so this is a built-in pattern review. Reason: ${error.message}`;
    renderWeeklyReview(fallback);
  } finally {
    $("weeklyBtn").disabled = false;
    $("weeklyBtn").textContent = "Review week";
  }
}

$("todayLabel").textContent = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric"
}).format(new Date());

$("reflectBtn").addEventListener("click", reflect);
$("clearBtn").addEventListener("click", () => {
  $("notes").value = "";
  localStorage.removeItem("draftNotes");
  $("notes").focus();
});
$("saveBtn").addEventListener("click", saveReflection);
$("weeklyBtn").addEventListener("click", reviewWeek);
$("refreshAnalyticsBtn").addEventListener("click", loadAnalytics);
$("hideRagDebugBtn").addEventListener("click", () => {
  $("ragDebugPanel").hidden = true;
  $("ragDebugToggle").checked = false;
});
$("exportBtn").addEventListener("click", exportHistory);
$("exportAllBtn").addEventListener("click", exportAllData);
$("clearAllBtn").addEventListener("click", clearAllData);
$("saveGoalsBtn").addEventListener("click", saveGoals);
$("addGoalBtn").addEventListener("click", () => {
  currentGoals = readGoalsFromUi();
  currentGoals.push({ area: "", target: "" });
  renderGoals();
});
$("goalList").addEventListener("click", (event) => {
  const removeIndex = event.target.dataset.removeGoal;
  if (removeIndex === undefined) return;
  currentGoals = readGoalsFromUi().filter((_, index) => index !== Number(removeIndex));
  renderGoals();
});
$("reviewPanel").addEventListener("click", (event) => {
  const followupType = event.target.dataset.followup;
  if (!followupType) return;
  runFollowup(followupType);
});
$("importFile").addEventListener("change", (event) => importHistory(event.target.files[0]));
$("clearHistoryBtn").addEventListener("click", clearHistory);
$("keptPromiseBtn").addEventListener("click", () => markPromise("kept"));
$("missedPromiseBtn").addEventListener("click", () => markPromise("missed"));
document.querySelectorAll(".tab-button").forEach((button) => {
  button.addEventListener("click", () => setActiveTab(button.dataset.tab));
});
document.querySelectorAll('input[name="ragMode"]').forEach((input) => {
  input.addEventListener("change", updateRagModeHint);
});
document.querySelectorAll('input[name="reflectionDepth"]').forEach((input) => {
  input.addEventListener("change", updateReflectionDepthHint);
});
$("notes").addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.key === "Enter") {
    reflect();
  }
});

$("notes").value = localStorage.getItem("draftNotes") || "";
$("notes").addEventListener("input", () => localStorage.setItem("draftNotes", $("notes").value));
updateRagModeHint();
updateReflectionDepthHint();
loadServerMemory();

