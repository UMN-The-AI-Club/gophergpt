import React, { useState } from "react";

const HistItem = ({ conversation, onLoad }) => {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onClick={() => onLoad(conversation)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: "100%", display: "block", textAlign: "left",
        padding: "8px 11px", borderRadius: 8, border: "none", cursor: "pointer",
        background: hovered ? "rgba(255,255,255,.05)" : "transparent",
        color: hovered ? "#e8e3e4" : "#a39b9d",
        fontSize: 13,
        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
        marginBottom: 2, transition: "background .15s, color .15s",
      }}
      title={conversation.title}
    >
      {conversation.title}
    </button>
  );
};

export const History = ({ conversations, onLoad }) => (
  <div>
    {conversations && conversations.map(conversation => (
      <HistItem key={conversation.id} conversation={conversation} onLoad={onLoad} />
    ))}
  </div>
);
