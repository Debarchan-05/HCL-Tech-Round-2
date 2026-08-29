import React, { useState, useEffect } from "react";
import { api } from "../api.js";

export default function RecommendationsView({ learnerId, onProgressChange }) {
  const [recs, setRecs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedWhy, setExpandedWhy] = useState({});
  const [busyCourse, setBusyCourse] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.getRecommendations(learnerId, 8);
      setRecs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [learnerId]);

  const toggleWhy = async (courseId) => {
    if (expandedWhy[courseId]) {
      setExpandedWhy((prev) => ({ ...prev, [courseId]: null }));
      return;
    }
    try {
      const res = await api.whyRecommended(learnerId, courseId);
      setExpandedWhy((prev) => ({ ...prev, [courseId]: res.explanation }));
    } catch (e) {
      console.error(e);
    }
  };

  const markCompleted = async (courseId) => {
    setBusyCourse(courseId);
    try {
      await api.updateProgress(learnerId, courseId, "completed", null);
      await load();
      onProgressChange?.();
    } finally {
      setBusyCourse(null);
    }
  };

  if (loading) return <div className="empty-state">Loading recommendations…</div>;

  return (
    <div>
      <div className="page-title">Recommended for you</div>
      <div className="page-subtitle">
        Ranked by skill-gap coverage, prerequisite readiness, level fit, and popularity. Tap "Why this?" for the reasoning.
      </div>

      {recs.length === 0 && (
        <div className="empty-state">No recommendations yet — set a goal in the Chat tab first.</div>
      )}

      {recs.map((r) => (
        <div className="rec-card" key={r.course.id}>
          <div className="rec-header">
            <div>
              <div className="rec-title">{r.course.title}</div>
              <div className="rec-meta">
                {r.course.domain} · {r.course.level} · {r.course.type} · {r.course.duration_hours}h
              </div>
            </div>
            <div className="score-badge">{Math.round(r.score * 100)}% match</div>
          </div>

          <div style={{ fontSize: 13, color: "#c3c5da" }}>{r.course.description}</div>

          <ul className="reason-list">
            {r.reasons.map((reason, i) => (
              <li key={i}>{reason}</li>
            ))}
          </ul>

          {expandedWhy[r.course.id] && (
            <div className="explain-box">{expandedWhy[r.course.id]}</div>
          )}

          <div className="rec-actions">
            <button className="btn secondary small" onClick={() => toggleWhy(r.course.id)}>
              {expandedWhy[r.course.id] ? "Hide explanation" : "Why this?"}
            </button>
            <a href={r.course.resource_url} target="_blank" rel="noreferrer">
              <button className="btn secondary small">Open resource ↗</button>
            </a>
            <button
              className="btn small"
              disabled={busyCourse === r.course.id}
              onClick={() => markCompleted(r.course.id)}
            >
              {busyCourse === r.course.id ? "Saving…" : "Mark completed"}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
