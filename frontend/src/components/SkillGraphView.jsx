import React, { useState, useEffect, useMemo } from "react";
import { api } from "../api.js";

const MILESTONE_ORDER = ["Foundations", "Core Skills", "Applied Practice", "Mastery"];
const COL_WIDTH = 260;
const NODE_W = 200;
const NODE_H = 64;
const ROW_GAP = 26;
const TOP_PAD = 70;
const LEFT_PAD = 40;

const STATUS_COLOR = {
  completed: "#4ade80",
  available: "#7c5cff",
  in_progress: "#fbbf24",
  locked: "#9a9db8",
};

function layoutGraph(nodes) {
  // Group nodes into columns by milestone (fixed canonical order), stack
  // vertically within each column ordered by the path's own step order —
  // this is a deterministic layered layout (no physics simulation), so it
  // renders identically and reliably every time rather than depending on
  // a force simulation settling into a good position.
  const columns = {};
  MILESTONE_ORDER.forEach((m) => (columns[m] = []));
  nodes.forEach((n) => {
    if (!columns[n.milestone]) columns[n.milestone] = [];
    columns[n.milestone].push(n);
  });
  Object.values(columns).forEach((col) => col.sort((a, b) => a.order - b.order));

  const positions = {};
  const presentMilestones = MILESTONE_ORDER.filter((m) => columns[m].length > 0);
  presentMilestones.forEach((milestone, colIdx) => {
    columns[milestone].forEach((node, rowIdx) => {
      positions[node.id] = {
        x: LEFT_PAD + colIdx * COL_WIDTH,
        y: TOP_PAD + rowIdx * (NODE_H + ROW_GAP),
        milestone,
        colIdx,
      };
    });
  });

  const maxRows = Math.max(1, ...presentMilestones.map((m) => columns[m].length));
  const width = LEFT_PAD * 2 + presentMilestones.length * COL_WIDTH - (COL_WIDTH - NODE_W);
  const height = TOP_PAD + maxRows * (NODE_H + ROW_GAP) + 20;

  return { positions, presentMilestones, width: Math.max(width, 600), height: Math.max(height, 300) };
}

function edgePath(sx, sy, tx, ty) {
  const midX = (sx + tx) / 2;
  return `M ${sx} ${sy} C ${midX} ${sy}, ${midX} ${ty}, ${tx} ${ty}`;
}

export default function SkillGraphView({ learnerId }) {
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [explaining, setExplaining] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.getSkillGraph(learnerId).then(setGraph).catch(console.error).finally(() => setLoading(false));
  }, [learnerId]);

  const layout = useMemo(() => (graph ? layoutGraph(graph.nodes) : null), [graph]);

  const connectedEdges = useMemo(() => {
    if (!hoveredNode || !graph) return new Set();
    const set = new Set();
    graph.edges.forEach((e, i) => {
      if (e.source === hoveredNode || e.target === hoveredNode) set.add(i);
    });
    return set;
  }, [hoveredNode, graph]);

  const selectCourse = async (nodeId) => {
    setSelectedNode(nodeId);
    setExplanation(null);
    setExplaining(true);
    try {
      const res = await api.whyRecommended(learnerId, nodeId);
      setExplanation(res.explanation);
    } catch (e) {
      setExplanation("Couldn't load an explanation for this step.");
    } finally {
      setExplaining(false);
    }
  };

  if (loading) return <div className="empty-state">Building your skill graph…</div>;
  if (!graph || graph.nodes.length === 0) {
    return <div className="empty-state">No graph yet — set a goal in the Chat tab first.</div>;
  }

  const selected = graph.nodes.find((n) => n.id === selectedNode);

  return (
    <div>
      <div className="page-title">Skill dependency graph</div>
      <div className="page-subtitle">
        Every course as a node, every arrow a prerequisite. Hover to trace dependencies, click a node for the full explanation.
      </div>

      <div className="graph-shell">
        <div className="graph-legend">
          {Object.entries(STATUS_COLOR).map(([status, color]) => (
            <span key={status}>
              <span className="legend-dot" style={{ background: color }} />
              {status.replace("_", " ")}
            </span>
          ))}
        </div>

        <div style={{ position: "relative" }}>
          <svg
            viewBox={`0 0 ${layout.width} ${layout.height}`}
            width="100%"
            style={{ display: "block", minHeight: 320 }}
          >
            {layout.presentMilestones.map((m, i) => (
              <text key={m} x={LEFT_PAD + i * COL_WIDTH} y={30} className="graph-milestone-label">
                {m}
              </text>
            ))}

            {graph.edges.map((e, i) => {
              const s = layout.positions[e.source];
              const t = layout.positions[e.target];
              if (!s || !t) return null;
              const sx = s.x + NODE_W;
              const sy = s.y + NODE_H / 2;
              const tx = t.x;
              const ty = t.y + NODE_H / 2;
              const isHighlighted = connectedEdges.has(i);
              const isDimmed = hoveredNode && !isHighlighted;
              return (
                <path
                  key={i}
                  d={edgePath(sx, sy, tx, ty)}
                  className={`graph-edge ${isHighlighted ? "highlighted" : ""} ${isDimmed ? "dimmed" : ""}`}
                />
              );
            })}

            {graph.nodes.map((n) => {
              const pos = layout.positions[n.id];
              if (!pos) return null;
              const isHovered = hoveredNode === n.id;
              return (
                <g
                  key={n.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  onMouseEnter={() => setHoveredNode(n.id)}
                  onMouseLeave={() => setHoveredNode(null)}
                  onClick={() => selectCourse(n.id)}
                >
                  <rect
                    className={`graph-node-rect ${n.status} ${isHovered ? "hovered" : ""}`}
                    width={NODE_W}
                    height={NODE_H}
                    rx={10}
                  />
                  <circle cx={14} cy={14} r={4} className="graph-status-dot" fill={STATUS_COLOR[n.status]} />
                  <text x={26} y={19} className="graph-node-title">
                    {n.title.length > 24 ? n.title.slice(0, 23) + "…" : n.title}
                  </text>
                  <text x={14} y={40} className="graph-node-meta">
                    {n.level} · {n.duration_hours}h · {n.type}
                  </text>
                  <text x={14} y={56} className="graph-node-meta">
                    step {n.order}
                  </text>
                </g>
              );
            })}
          </svg>

          {hoveredNode && (() => {
            const pos = layout.positions[hoveredNode];
            const n = graph.nodes.find((x) => x.id === hoveredNode);
            const incoming = graph.edges.filter((e) => e.target === hoveredNode);
            const isLastColumn = pos.colIdx === layout.presentMilestones.length - 1;
            const left = isLastColumn
              ? Math.max(8, pos.x - 260)
              : Math.min(pos.x + NODE_W + 14, layout.width - 270);
            return (
              <div className="graph-tooltip" style={{ left, top: Math.max(8, pos.y - 10) }}>
                <div className="graph-tooltip-title">{n.title}</div>
                <div className="graph-tooltip-meta">
                  {n.milestone} · {n.level} · {n.duration_hours}h
                </div>
                {incoming.length > 0 && (
                  <div className="graph-tooltip-skill">
                    requires: {incoming.map((e) => e.via_skill).join(", ")}
                  </div>
                )}
                <div style={{ color: "#9a9db8", fontSize: 11, marginTop: 6 }}>Click for full explanation →</div>
              </div>
            );
          })()}
        </div>

        {selected && (
          <div className="graph-detail-panel">
            <div style={{ fontWeight: 700, marginBottom: 6 }}>{selected.title}</div>
            {explaining ? (
              <div style={{ color: "#9a9db8", fontSize: 13 }}>Loading explanation…</div>
            ) : (
              <div className="explain-box" style={{ marginTop: 0 }}>{explanation}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
