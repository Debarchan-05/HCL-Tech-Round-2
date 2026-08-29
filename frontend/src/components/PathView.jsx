import React, { useState, useEffect } from "react";
import { api } from "../api.js";

export default function PathView({ learnerId, onProgressChange }) {
  const [path, setPath] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyCourse, setBusyCourse] = useState(null);
  const [question, setQuestion] = useState("");
  const [qaHistory, setQaHistory] = useState([]);
  const [asking, setAsking] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.getPath(learnerId);
      setPath(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [learnerId]);

  const updateStatus = async (courseId, status, feedback = null) => {
    setBusyCourse(courseId);
    try {
      const updated = await api.updateProgress(learnerId, courseId, status, feedback);
      setPath(updated);
      onProgressChange?.();
    } finally {
      setBusyCourse(null);
    }
  };

  const askQuestion = async () => {
    const q = question.trim();
    if (!q || asking) return;
    setQuestion("");
    setQaHistory((prev) => [...prev, { role: "user", content: q }]);
    setAsking(true);
    try {
      const res = await api.ask(learnerId, q);
      setQaHistory((prev) => [...prev, { role: "assistant", content: res.answer }]);
    } finally {
      setAsking(false);
    }
  };

  if (loading) return <div className="empty-state">Building your path…</div>;
  if (!path || path.steps.length === 0) {
    return <div className="empty-state">No path yet — set a goal in the Chat tab first.</div>;
  }

  return (
    <div>
      <div className="page-title">Your learning roadmap</div>
      <div className="page-subtitle">{path.explanation_summary}</div>

      <div style={{ marginBottom: 20 }}>
        <div className="chip gap">Skill gap: {path.skill_gap.join(", ").replace(/-/g, " ") || "none"}</div>
        <div className="chip skill">Already known: {path.already_known.join(", ").replace(/-/g, " ") || "none yet"}</div>
        <div className="chip">Total: {path.total_duration_hours}h across {path.steps.length} steps</div>
      </div>

      {path.steps.map((s) => (
        <div className={`path-step ${s.status}`} key={s.course.id}>
          <div className="step-num">{s.order}</div>
          <div style={{ flex: 1 }}>
            <div className="milestone-badge">{s.milestone}</div>
            <div style={{ fontWeight: 600, fontSize: 15, margin: "4px 0" }}>{s.course.title}</div>
            <div className="rec-meta">
              {s.course.domain} · {s.course.level} · {s.course.duration_hours}h
              {s.unlocked_by.length > 0 && ` · builds on: ${s.unlocked_by.join(", ").replace(/-/g, " ")}`}
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center" }}>
              <span className={`status-pill ${s.status}`}>{s.status.replace("_", " ")}</span>
              {s.status !== "completed" && (
                <>
                  <button
                    className="btn small"
                    disabled={busyCourse === s.course.id || s.status === "locked"}
                    onClick={() => updateStatus(s.course.id, "completed")}
                  >
                    Mark completed
                  </button>
                  <button
                    className="btn secondary small"
                    disabled={busyCourse === s.course.id}
                    onClick={() => updateStatus(s.course.id, "in_progress", "too_hard")}
                  >
                    Too hard 😓
                  </button>
                  <button
                    className="btn secondary small"
                    disabled={busyCourse === s.course.id}
                    onClick={() => updateStatus(s.course.id, "in_progress", "too_easy")}
                  >
                    Too easy 🚀
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      ))}

      <div className="card" style={{ marginTop: 24 }}>
        <div style={{ fontWeight: 700, marginBottom: 10 }}>Ask about your path</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 240, overflowY: "auto" }}>
          {qaHistory.map((m, i) => (
            <div className={`msg-row ${m.role}`} key={i}>
              <div className={`bubble ${m.role}`} style={{ maxWidth: "85%" }}>{m.content}</div>
            </div>
          ))}
        </div>
        <div className="ask-row">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && askQuestion()}
            placeholder="e.g. why do I need SQL? / how long will this take? / what's next?"
          />
          <button className="btn" onClick={askQuestion} disabled={asking || !question.trim()}>
            Ask
          </button>
        </div>
      </div>
    </div>
  );
}
