import React, { useState } from "react";
import { History } from "./History";
import { LayoutGrid, Plus } from "lucide-react";

const BrandMark = () => (
  <div style={{
    width: 38, height: 38, borderRadius: 11, flexShrink: 0,
    background: "linear-gradient(145deg, #8c0a20, #5e0014)",
    boxShadow: "0 4px 14px rgba(122,0,25,.45), inset 0 1px 0 rgba(255,255,255,.14), inset 0 0 0 1px rgba(255,204,51,.22)",
    display: "flex", alignItems: "center", justifyContent: "center",
  }}>
    <span style={{ color: "#FFCC33", fontFamily: "Georgia, serif", fontSize: 20, fontWeight: 700, lineHeight: 1, userSelect: "none" }}>M</span>
  </div>
);

const NavRow = ({ onClick, active, icon: Icon, label }) => {
  const [hovered, setHovered] = useState(false);
  const isHighlighted = active || hovered;
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: "100%", display: "flex", alignItems: "center", gap: 10,
        padding: "9px 11px", borderRadius: 9, cursor: "pointer",
        background: active ? "rgba(122,0,25,.42)" : hovered ? "rgba(255,255,255,.05)" : "transparent",
        color: isHighlighted ? "#fff" : "#b8b0b2",
        fontSize: 13.5, fontWeight: 500, border: "none", textAlign: "left",
        transition: "background .15s, color .15s",
      }}
    >
      {Icon && <Icon size={16} style={{ color: active ? "#FFCC33" : hovered ? "#fff" : "#8a8285", flexShrink: 0, transition: "color .15s" }} />}
      {label}
    </button>
  );
};

const Sidebar = ({ onNewChat, onNavigate, currentPage, conversations, onLoad, onClearHistory }) => {
  const [confirming, setConfirming] = useState(false);
  const [newChatHovered, setNewChatHovered] = useState(false);
  const [profileHovered, setProfileHovered] = useState(false);

  const handleClear = () => {
    if (confirming) {
      onClearHistory();
      setConfirming(false);
    } else {
      setConfirming(true);
      setTimeout(() => setConfirming(false), 3000);
    }
  };

  return (
    <div style={{
      width: 260, flexShrink: 0, height: "100vh",
      background: "#211e1f",
      borderRight: "1px solid rgba(255,255,255,.06)",
      display: "flex", flexDirection: "column",
      padding: "14px 12px",
    }}>

      {/* Brand lockup */}
      <div style={{ display: "flex", alignItems: "center", gap: 11, padding: "8px 6px 4px", marginBottom: 16 }}>
        <BrandMark />
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-.02em", color: "#fff", lineHeight: 1.25 }}>
            Gopher<span style={{ color: "#FFCC33" }}>GPT</span>
          </div>
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".13em", color: "#7c7375", marginTop: 2 }}>
            U of M
          </div>
        </div>
      </div>

      {/* New Chat button */}
      <button
        onClick={() => { onNewChat(); onNavigate("chat"); }}
        onMouseEnter={() => setNewChatHovered(true)}
        onMouseLeave={() => setNewChatHovered(false)}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: 9,
          padding: "10px 12px", borderRadius: 10,
          border: `1px solid ${newChatHovered ? "rgba(255,204,51,.5)" : "rgba(255,204,51,.28)"}`,
          background: newChatHovered ? "rgba(255,204,51,.13)" : "rgba(255,204,51,.06)",
          color: "#fff", fontSize: 14, fontWeight: 600,
          marginBottom: 22, cursor: "pointer",
          transition: "background .15s, border-color .15s",
        }}
      >
        <Plus size={16} style={{ color: "#FFCC33", flexShrink: 0 }} />
        New Chat
      </button>

      {/* Apps section */}
      <div style={{ marginBottom: 22 }}>
        <div style={{ fontSize: 10.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".11em", color: "#7c7375", padding: "0 6px", marginBottom: 8 }}>
          Apps
        </div>
        <NavRow
          onClick={() => onNavigate("department")}
          active={currentPage === "department"}
          icon={LayoutGrid}
          label="Department Explorer"
        />
      </div>

      {/* History section */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column", minHeight: 0 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 6px", marginBottom: 8 }}>
          <span style={{ fontSize: 10.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".11em", color: "#7c7375" }}>History</span>
          {conversations && conversations.length > 0 && (
            <button
              onClick={handleClear}
              style={{
                fontSize: 11, background: "none", border: "none", cursor: "pointer",
                color: confirming ? "#f87171" : "#6c6466",
                transition: "color .15s", padding: 0,
              }}
              onMouseEnter={e => { if (!confirming) e.currentTarget.style.color = "#a39b9d"; }}
              onMouseLeave={e => { if (!confirming) e.currentTarget.style.color = "#6c6466"; }}
            >
              {confirming ? "Confirm?" : "Clear"}
            </button>
          )}
        </div>
        <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
          <History conversations={conversations} onLoad={onLoad} />
        </div>
      </div>

      {/* Profile — pinned bottom */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,.06)", paddingTop: 10, marginTop: 8 }}>
        <button
          onClick={() => onNavigate("profile")}
          onMouseEnter={() => setProfileHovered(true)}
          onMouseLeave={() => setProfileHovered(false)}
          style={{
            width: "100%", display: "flex", alignItems: "center", gap: 10,
            padding: "9px 11px", borderRadius: 9, cursor: "pointer",
            background: currentPage === "profile" ? "rgba(122,0,25,.42)" : profileHovered ? "rgba(255,255,255,.05)" : "transparent",
            color: (currentPage === "profile" || profileHovered) ? "#fff" : "#b8b0b2",
            fontSize: 13.5, border: "none", textAlign: "left",
            transition: "background .15s, color .15s",
          }}
        >
          <div style={{
            width: 26, height: 26, borderRadius: "50%", flexShrink: 0,
            background: "linear-gradient(135deg, #7A0019, #a01530)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 11, fontWeight: 700, color: "#fff",
          }}>
            M
          </div>
          Profile
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
