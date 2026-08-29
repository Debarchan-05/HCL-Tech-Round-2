const BASE = "/api";

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}

export const api = {
  sendChat: (learner_id, message, history) =>
    req("/chat", { method: "POST", body: JSON.stringify({ learner_id, message, history }) }),

  // Real-time streaming chat over Server-Sent Events. Calls onChunk(text)
  // as each piece arrives, then onDone(payload) once the stream ends with
  // the full structured response (profile, ready_for_path, etc.).
  streamChat: async (learner_id, message, history, onChunk, onDone) => {
    const res = await fetch(`${BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ learner_id, message, history }),
    });
    if (!res.ok || !res.body) {
      throw new Error(`${res.status} ${res.statusText}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop(); // last piece may be incomplete; keep for next read
      for (const frame of frames) {
        const line = frame.trim();
        if (!line.startsWith("data: ")) continue;
        const payload = JSON.parse(line.slice(6));
        if (payload.type === "chunk") {
          onChunk(payload.text);
        } else if (payload.type === "done") {
          onDone(payload);
        }
      }
    }
  },

  getProfile: (learnerId) => req(`/profile/${learnerId}`),
  resetProfile: (learnerId) => req(`/profile/${learnerId}/reset`, { method: "POST" }),

  getRecommendations: (learnerId, topK = 8) => req(`/recommendations/${learnerId}?top_k=${topK}`),
  getCatalog: () => req("/recommendations/catalog/all"),

  getPath: (learnerId) => req(`/path/${learnerId}`),
  updateProgress: (learner_id, course_id, status, feedback) =>
    req("/path/progress", {
      method: "POST",
      body: JSON.stringify({ learner_id, course_id, status, feedback }),
    }),

  getDashboard: (learnerId) => req(`/dashboard/${learnerId}`),

  getSkillGraph: (learnerId) => req(`/graph/${learnerId}`),

  whyRecommended: (learner_id, course_id) =>
    req("/explain/why", { method: "POST", body: JSON.stringify({ learner_id, course_id }) }),
  ask: (learner_id, question) =>
    req("/explain/ask", { method: "POST", body: JSON.stringify({ learner_id, question }) }),
};
