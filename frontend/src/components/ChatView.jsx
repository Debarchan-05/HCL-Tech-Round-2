import React, { useState, useRef, useEffect } from "react";
import { api } from "../api.js";

export default function ChatView({ learnerId, onProfileChange }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! I'm your AI learning path assistant. Tell me what you're hoping to achieve — for example, \"I want to become a data scientist, I know some Python but I'm new to ML, and I have about 6 hours a week.\"",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    const newMessages = [...messages, { role: "user", content: text }, { role: "assistant", content: "" }];
    setMessages(newMessages);
    setLoading(true);

    try {
      const history = newMessages.slice(0, -2).map((m) => ({ role: m.role, content: m.content }));

      await api.streamChat(
        learnerId,
        text,
        history,
        // onChunk — append streamed text into the last (assistant) bubble live
        (chunk) => {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: updated[updated.length - 1].content + chunk,
            };
            return updated;
          });
        },
        // onDone — stream finished; profile is now updated server-side
        () => {
          onProfileChange?.();
        }
      );
    } catch (e) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: "Sorry, I hit an error reaching the backend. Is it running on port 8000?",
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div>
      <div className="page-title">Tell me about your learning goals</div>
      <div className="page-subtitle">
        Describe your goal, experience level, and time availability in plain language — I'll build your profile as we talk.
      </div>

      <div className="chat-window">
        <div className="chat-messages" ref={scrollRef}>
          {messages.map((m, i) => {
            const isStreamingBubble = loading && i === messages.length - 1 && m.role === "assistant";
            return (
              <div className={`msg-row ${m.role}`} key={i}>
                <div className={`bubble ${m.role}`}>
                  {m.content}
                  {isStreamingBubble && <span className="stream-cursor">▍</span>}
                </div>
              </div>
            );
          })}
        </div>
        <div className="chat-input-row">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Type your message…"
            disabled={loading}
          />
          <button className="btn" onClick={send} disabled={loading || !input.trim()}>
            Send
          </button>
        </div>
      </div>

      <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
        {[
          "I want to become a full-stack web developer, I know HTML and CSS but no JavaScript frameworks yet, 8 hours a week",
          "I'd like to become a data scientist, complete beginner, 5 hours a week",
          "I want to become a devops engineer, I know some Docker, intensive pace",
        ].map((example, i) => (
          <button
            key={i}
            className="btn secondary small"
            onClick={() => setInput(example)}
          >
            Try example {i + 1}
          </button>
        ))}
      </div>
    </div>
  );
}
