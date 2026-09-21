import React, { useRef } from "react";
import { Send } from "lucide-react";

const ChatInput = ({ value, onChange, onSend, placeholder, disabled = false, textareaRef }) => {
  const [focused, setFocused] = React.useState(false);
  const internalRef = useRef(null);
  const ref = textareaRef || internalRef;

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSend();
    }
  };

  const handleInput = (e) => {
    onChange(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  };

  const isEmpty = !value.trim();

  return (
    <div style={{
      display: "flex", alignItems: "flex-end", gap: 8,
      background: "#2c2829",
      border: `1.5px solid ${focused ? "rgba(255,204,51,.7)" : "rgba(255,255,255,.1)"}`,
      borderRadius: 16, padding: "8px 8px 8px 16px",
      boxShadow: focused ? "0 0 0 4px rgba(255,204,51,.1)" : "none",
      transition: "border-color .15s, box-shadow .15s",
    }}>
      <textarea
        ref={ref}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        rows={1}
        style={{
          flex: 1, background: "transparent", border: "none", outline: "none", resize: "none",
          color: "#f3eff0", fontSize: 14.5, lineHeight: 1.5,
          maxHeight: 160, overflowY: "auto", padding: "4px 0",
          fontFamily: "inherit",
        }}
        className="placeholder-muted"
      />
      <button
        onClick={() => { if (!disabled && !isEmpty) onSend(); }}
        disabled={disabled || isEmpty}
        style={{
          width: 38, height: 38, borderRadius: 11, flexShrink: 0,
          background: "#FFCC33", border: "none", cursor: disabled || isEmpty ? "default" : "pointer",
          display: "flex", alignItems: "center", justifyContent: "center",
          opacity: disabled || isEmpty ? 0.4 : 1,
          transition: "opacity .15s, filter .15s",
        }}
        onMouseEnter={e => { if (!disabled && !isEmpty) e.currentTarget.style.filter = "brightness(1.08)"; }}
        onMouseLeave={e => { e.currentTarget.style.filter = "none"; }}
      >
        <Send size={16} style={{ color: "#7A0019" }} />
      </button>
    </div>
  );
};

export default ChatInput;
