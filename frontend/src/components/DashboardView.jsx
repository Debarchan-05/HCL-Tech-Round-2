import React, { useState, useEffect } from "react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { api } from "../api.js";

const COLORS = ["#7c5cff", "#22d3ee", "#4ade80", "#fbbf24"];

export default function DashboardView({ learnerId, refreshKey }) {
  const [dash, setDash] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .getDashboard(learnerId)
      .then(setDash)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [learnerId, refreshKey]);

  if (loading) return <div className="empty-state">Loading dashboard…</div>;
  if (!dash) return <div className="empty-state">No data yet — set a goal in the Chat tab first.</div>;

  const pieData = [
    { name: "Completed", value: dash.completed_courses },
    { name: "Remaining", value: Math.max(dash.total_courses - dash.completed_courses, 0) },
  ];

  const barData = dash.milestone_timeline.map((m) => ({
    name: m.milestone,
    hours: m.hours,
    courses: m.course_count,
  }));

  return (
    <div>
      <div className="page-title">Your progress dashboard</div>
      <div className="page-subtitle">
        Goal: <strong>{dash.goal_title || "Not set"}</strong>
      </div>

      <div className="grid-3" style={{ marginBottom: 20 }}>
        <div className="stat-box">
          <div className="stat-value">{dash.completion_pct}%</div>
          <div className="stat-label">Path completion</div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${dash.completion_pct}%` }} />
          </div>
        </div>
        <div className="stat-box">
          <div className="stat-value">{dash.completed_courses}/{dash.total_courses}</div>
          <div className="stat-label">Courses completed</div>
        </div>
        <div className="stat-box">
          <div className="stat-value">{dash.hours_completed}h</div>
          <div className="stat-label">Hours invested ({dash.hours_remaining}h remaining)</div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div style={{ fontWeight: 700, marginBottom: 10 }}>Completion breakdown</div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={4}>
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "#171b2e", border: "1px solid #2a2f4a", borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div style={{ fontWeight: 700, marginBottom: 10 }}>Hours by milestone stage</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2f4a" />
              <XAxis dataKey="name" stroke="#9a9db8" fontSize={11} />
              <YAxis stroke="#9a9db8" fontSize={11} />
              <Tooltip contentStyle={{ background: "#171b2e", border: "1px solid #2a2f4a", borderRadius: 8 }} />
              <Bar dataKey="hours" fill="#7c5cff" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div style={{ fontWeight: 700, marginBottom: 10 }}>Skills acquired ({dash.skills_acquired.length})</div>
          <div>
            {dash.skills_acquired.length ? (
              dash.skills_acquired.map((s) => (
                <span className="chip skill" key={s}>{s.replace(/-/g, " ")}</span>
              ))
            ) : (
              <span style={{ color: "#9a9db8", fontSize: 13 }}>None yet — complete a course to get started.</span>
            )}
          </div>
        </div>
        <div className="card">
          <div style={{ fontWeight: 700, marginBottom: 10 }}>Skills remaining ({dash.skills_remaining.length})</div>
          <div>
            {dash.skills_remaining.length ? (
              dash.skills_remaining.map((s) => (
                <span className="chip gap" key={s}>{s.replace(/-/g, " ")}</span>
              ))
            ) : (
              <span style={{ color: "#4ade80", fontSize: 13 }}>🎉 All target skills acquired!</span>
            )}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div style={{ fontWeight: 700, marginBottom: 10 }}>Next recommended actions</div>
        {dash.next_actions.length === 0 && (
          <div style={{ color: "#9a9db8", fontSize: 13 }}>No pending actions right now.</div>
        )}
        {dash.next_actions.map((c) => (
          <div key={c.id} style={{ padding: "8px 0", borderBottom: "1px solid #2a2f4a", fontSize: 14 }}>
            <strong>{c.title}</strong>
            <span style={{ color: "#9a9db8" }}> — {c.level}, {c.duration_hours}h</span>
          </div>
        ))}
      </div>
    </div>
  );
}
