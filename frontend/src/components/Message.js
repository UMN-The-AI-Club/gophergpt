import React, { useState } from "react";
import { formatBotMessage } from "../utils/messageFormatter";
import RichContent from "./RichContent";

const BotAvatar = () => (
  <div style={{
    width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
    background: "#fff",
    boxShadow: "0 2px 10px rgba(0,0,0,.32)",
    display: "flex", alignItems: "center", justifyContent: "center",
    marginTop: 2,
  }}>
    <span style={{ color: "#7A0019", fontFamily: "Georgia, serif", fontSize: 16, fontWeight: 800, lineHeight: 1, userSelect: "none" }}>M</span>
  </div>
);

const FollowUpChip = ({ text, onSend }) => {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onClick={() => onSend(text)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        fontSize: 12.5, color: hovered ? "#fff" : "#c9bfc1",
        background: hovered ? "#2c2728" : "rgba(37,33,34,.9)",
        border: `1px solid ${hovered ? "rgba(255,204,51,.35)" : "rgba(255,255,255,.1)"}`,
        borderRadius: 20, padding: "6px 13px", cursor: "pointer",
        transition: "background .13s, border-color .13s, color .13s",
        lineHeight: 1.3,
      }}
    >
      <span style={{ color: hovered ? "#FFCC33" : "#7c7375", fontSize: 11, flexShrink: 0 }}>↑</span>
      {text}
    </button>
  );
};

const CONTENT_TAGS = {
  schedule: "CLASS SECTIONS",
  compare: "COURSE COMPARE",
  prof_compare: "PROF COMPARE",
  research: "RESEARCH",
};

function getTag(content) {
  if (!content || !content.length) return null;
  for (const item of content) {
    if (CONTENT_TAGS[item.type]) return CONTENT_TAGS[item.type];
  }
  return null;
}

export const Message = ({ message, isUser, content = [], followUps, onSendDirect }) => {
  if (isUser) {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }} className="message-bubble">
        <div style={{
          background: "rgba(122,0,25,.45)",
          border: "1px solid rgba(255,204,51,.15)",
          borderRadius: "16px 16px 4px 16px",
          padding: "12px 17px",
          maxWidth: "78%",
          color: "#f3eff0", fontSize: 14.5, lineHeight: 1.5,
        }}>
          {message}
        </div>
      </div>
    );
  }

  const hasFollowUps = followUps && followUps.length > 0 && onSendDirect;
  const tag = getTag(content);

  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 14, marginBottom: 24 }} className="message-bubble">
      <BotAvatar />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: 12.5, fontWeight: 700, color: "#fff" }}>GopherGPT</span>
          {tag && (
            <span style={{
              fontSize: 9.5, fontWeight: 700, color: "#FFCC33",
              background: "rgba(255,204,51,.1)", border: "1px solid rgba(255,204,51,.2)",
              padding: "2px 7px", borderRadius: 999, letterSpacing: ".05em",
            }}>
              {tag}
            </span>
          )}
        </div>
        {message && (
          <div
            className={`bot-message${content.length || hasFollowUps ? " mb-3" : ""}`}
            dangerouslySetInnerHTML={{ __html: formatBotMessage(message) }}
          />
        )}
        {content.length > 0 && <RichContent content={content} />}
        {hasFollowUps && (
          <div style={{ marginTop: content.length > 0 ? 14 : 10 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
              {followUps.map((q) => (
                <FollowUpChip key={q} text={q} onSend={onSendDirect} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
