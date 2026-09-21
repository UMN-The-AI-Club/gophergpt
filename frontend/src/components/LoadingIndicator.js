import React from "react";

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

export const LoadingIndicator = ({ label = "Thinking" }) => (
  <div style={{ display: "flex", alignItems: "flex-start", gap: 14, marginBottom: 24 }}>
    <BotAvatar />
    <div style={{ display: "flex", alignItems: "center", gap: 8, paddingTop: 8 }}>
      <span style={{ fontSize: 13.5, color: "#8f878a" }}>{label}</span>
      <div style={{ display: "flex", gap: 4 }}>
        {[0, 150, 300].map((delay) => (
          <div
            key={delay}
            style={{
              width: 6, height: 6, borderRadius: "50%", background: "#FFCC33",
              animation: "bounce 1.2s ease-in-out infinite",
              animationDelay: `${delay}ms`,
            }}
          />
        ))}
      </div>
    </div>
  </div>
);
