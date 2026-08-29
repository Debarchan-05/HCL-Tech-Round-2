import React, { useState, useEffect } from "react";
import ChatView from "./components/ChatView.jsx";
import RecommendationsView from "./components/RecommendationsView.jsx";
import PathView from "./components/PathView.jsx";
import DashboardView from "./components/DashboardView.jsx";
import SkillGraphView from "./components/SkillGraphView.jsx";
import { api } from "./api.js";

const LEARNER_ID_KEY = "learnpath_learner_id";

function getOrCreateLearnerId() {
  let id = localStorage.getItem(LEARNER_ID_KEY);
  if (!id) {
    id = "learner_" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem(LEARNER_ID_KEY, id);
  }
  return id;
}

export default function App() {
  const [view, setView] = useState("chat");
  const [learnerId] = useState(getOrCreateLearnerId);
  const [profile, setProfile] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refreshProfile = async () => {
    try {
      const p = await api.getProfile(learnerId);
      setProfile(p);
    } catch (e) {
      console.error("Failed to load profile", e);
    }
  };

  useEffect(() => {
    refreshProfile();
  }, [refreshKey]);

  const bumpRefresh = () => setRefreshKey((k) => k + 1);

  const hasGoal = !!profile?.matched_goal_id;

  const navItems = [
    { key: "chat", label: "💬 Chat with Assistant" },
    { key: "recommendations", label: "📚 Recommendations", disabled: !hasGoal },
    { key: "path", label: "🗺️ Learning Path", disabled: !hasGoal },
    { key: "graph", label: "🕸️ Skill Graph", disabled: !hasGoal },
    { key: "dashboard", label: "📊 Dashboard", disabled: !hasGoal },
  ];

  return (
    <div className="app-shell">
      <div className="sidebar">
        <div className="brand">
          <span className="brand-dot" />
          LearnPath AI
        </div>
        {navItems.map((item) => (
          <div
            key={item.key}
            className={`nav-item ${view === item.key ? "active" : ""}`}
            style={item.disabled ? { opacity: 0.4, cursor: "not-allowed" } : {}}
            onClick={() => !item.disabled && setView(item.key)}
            title={item.disabled ? "Set a goal in Chat first" : ""}
          >
            {item.label}
          </div>
        ))}
        <div style={{ marginTop: "auto", fontSize: 11, color: "#6b6f8f", paddingTop: 20 }}>
          {profile?.matched_goal_title ? (
            <>
              Goal: <strong style={{ color: "#e8e9f3" }}>{profile.matched_goal_title}</strong>
            </>
          ) : (
            "No goal set yet"
          )}
        </div>
      </div>

      <div className="main">
        {view === "chat" && (
          <ChatView learnerId={learnerId} onProfileChange={bumpRefresh} />
        )}
        {view === "recommendations" && (
          <RecommendationsView learnerId={learnerId} onProgressChange={bumpRefresh} />
        )}
        {view === "path" && (
          <PathView learnerId={learnerId} onProgressChange={bumpRefresh} />
        )}
        {view === "graph" && (
          <SkillGraphView learnerId={learnerId} />
        )}
        {view === "dashboard" && (
          <DashboardView learnerId={learnerId} refreshKey={refreshKey} />
        )}
      </div>
    </div>
  );
}
