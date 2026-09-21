import React, { useRef } from "react";
import { BookOpen, ArrowLeftRight, User, FlaskConical, GraduationCap, MessageSquare, Calendar, Clock, LayoutGrid } from "lucide-react";
import ChatWindow from "../components/ChatWindow";
import ChatInput from "../components/ChatInput";

const STARTERS = [
  { label: "What is CSCI 4041 like?", sub: "Algorithms & Data Structures", Icon: BookOpen },
  { label: "Compare CSCI 1933 and CSCI 1913", sub: "Side-by-side grade breakdown", Icon: ArrowLeftRight },
  { label: "Who teaches MATH 1271?", sub: "Professors & ratings", Icon: User },
  { label: "Research opportunities in computer science", sub: "UMN research programs", Icon: FlaskConical },
];

function getCurrentTerm() {
  const month = new Date().getMonth() + 1;
  const year = new Date().getFullYear();
  if (month <= 5) return { label: "Spring", year };
  if (month <= 8) return { label: "Summer", year };
  return { label: "Fall", year };
}

const StatCard = ({ Icon, label, value, valueSuffix, valueSm, sub, progress, dim }) => (
  <div style={{
    background: "#252122", border: "1px solid rgba(255,255,255,.07)",
    borderRadius: 14, padding: "15px 17px",
  }}>
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
      <Icon size={13} style={{ color: "#FFCC33" }} />
      <span style={{ fontSize: 11.5, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".04em", color: "#9a9294" }}>{label}</span>
    </div>
    <div style={{
      fontSize: valueSm ? 17 : 22, fontWeight: 700,
      color: dim ? "#6c6466" : "#fff",
      letterSpacing: "-.02em", lineHeight: 1.15,
      marginBottom: sub || progress != null ? 6 : 0,
      whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
    }}>
      {value}
      {valueSuffix && <span style={{ fontSize: 14, fontWeight: 400, color: "#8f878a", marginLeft: 4 }}>{valueSuffix}</span>}
    </div>
    {progress != null && (
      <div style={{ height: 4, borderRadius: 999, background: "rgba(255,255,255,.09)", marginBottom: 6 }}>
        <div style={{ height: "100%", borderRadius: 999, background: "linear-gradient(90deg, #FFCC33, #e0a92a)", width: `${progress}%` }} />
      </div>
    )}
    {sub && <div style={{ fontSize: 12, color: "#8f878a" }}>{sub}</div>}
  </div>
);

const StarterCard = ({ label, sub, Icon, onFill }) => {
  const [hovered, setHovered] = React.useState(false);
  return (
    <button
      onClick={() => onFill(label)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex", alignItems: "flex-start", gap: 13, textAlign: "left",
        background: hovered ? "#2c2728" : "#252122",
        border: `1px solid ${hovered ? "rgba(255,204,51,.35)" : "rgba(255,255,255,.07)"}`,
        borderLeft: `2px solid ${hovered ? "#FFCC33" : "transparent"}`,
        borderRadius: 14, padding: "15px 16px", cursor: "pointer",
        transform: hovered ? "translateY(-1px)" : "none",
        transition: "background .15s, border-color .15s, transform .15s",
      }}
    >
      <div style={{
        width: 34, height: 34, borderRadius: 9, flexShrink: 0,
        background: "rgba(122,0,25,.35)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        <Icon size={17} style={{ color: "#FFCC33" }} />
      </div>
      <div>
        <div style={{ fontSize: 13.5, fontWeight: 600, color: "#fff", marginBottom: 3 }}>{label}</div>
        <div style={{ fontSize: 12, color: "#8f878a" }}>{sub}</div>
      </div>
    </button>
  );
};

const HomeView = ({ onFill, onNavigate, profile, conversationCount }) => {
  const term = getCurrentTerm();
  const major = profile?.major;
  const year = profile?.year;
  const level = profile?.level;

  const greetingSub = major && year
    ? `You're a ${year} in ${major} — ask about classes, grades, or what to take next.`
    : "Your AI guide to courses, professors, and research at the U of M. Ask about classes, grades, or what to take next.";

  const stats = [
    {
      Icon: GraduationCap, label: "Major",
      value: major || "Not set", valueSm: true,
      sub: major ? "Field of study" : "Set in profile →",
      dim: !major,
    },
    {
      Icon: User, label: "Year",
      value: year || "Not set", valueSm: true,
      sub: level || (year ? "Level" : "Set in profile →"),
      dim: !year,
    },
    {
      Icon: MessageSquare, label: "Conversations",
      value: String(conversationCount),
      sub: conversationCount === 1 ? "Chat saved" : "Chats saved",
    },
    {
      Icon: Calendar, label: "Current Term",
      value: term.label, valueSuffix: String(term.year),
      sub: "Active semester",
    },
  ];

  return (
  <div>
    {/* Greeting banner */}
    <div style={{
      position: "relative", overflow: "hidden",
      borderRadius: 18, border: "1px solid rgba(255,204,51,.14)",
      background: "linear-gradient(110deg, rgba(122,0,25,.5), rgba(122,0,25,.14) 52%, rgba(255,204,51,.05))",
      padding: "24px 28px", marginBottom: 22,
    }}>
      {/* Decorative ghost M */}
      <div style={{
        position: "absolute", right: -30, bottom: -70,
        fontSize: 200, fontWeight: 800, fontFamily: "Georgia, serif",
        color: "rgba(255,204,51,.05)", lineHeight: 1, pointerEvents: "none", userSelect: "none",
      }}>M</div>

      {/* Term chip */}
      <div style={{
        position: "absolute", top: 16, right: 20,
        display: "flex", alignItems: "center", gap: 6,
        background: "rgba(0,0,0,.28)", border: "1px solid rgba(255,255,255,.1)",
        padding: "6px 12px", borderRadius: 999, fontSize: 12, fontWeight: 600,
      }}>
        <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#5ad17f", boxShadow: "0 0 0 3px rgba(90,209,127,.18)" }} />
        {term.label} {term.year}
      </div>

      <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.02em", margin: "0 0 8px", lineHeight: 1.2 }}>
        Welcome back to <span style={{ color: "#FFCC33" }}>GopherGPT</span>
      </h1>
      <p style={{ fontSize: 14, color: "#c9bfc1", margin: 0, maxWidth: 560, lineHeight: 1.5 }}>
        {greetingSub}
      </p>
    </div>

    {/* Stats row */}
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 }}>
      {stats.map((s) => <StatCard key={s.label} {...s} />)}
    </div>

    {/* Jump back in */}
    <div style={{ marginBottom: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 13 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#fff" }}>Jump back in</span>
        <span style={{
          fontSize: 10, fontWeight: 700, color: "#FFCC33",
          background: "rgba(255,204,51,.1)", border: "1px solid rgba(255,204,51,.2)",
          padding: "2px 8px", borderRadius: 999, letterSpacing: ".04em", textTransform: "uppercase",
        }}>Suggested</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 13 }}>
        {STARTERS.map((s) => <StarterCard key={s.label} {...s} onFill={onFill} />)}
      </div>
    </div>

    {/* Open a tool */}
    <div>
      <div style={{ fontSize: 13, fontWeight: 700, color: "#fff", marginBottom: 13 }}>Open a tool</div>
      <DeptBanner onNavigate={onNavigate} />
    </div>
  </div>
  );
};

const DeptBanner = ({ onNavigate }) => {
  const [hovered, setHovered] = React.useState(false);
  return (
    <button
      onClick={() => onNavigate("department")}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: "100%", display: "flex", alignItems: "center", gap: 16, textAlign: "left",
        background: hovered ? "#2c2728" : "#252122",
        border: `1px solid ${hovered ? "rgba(255,204,51,.3)" : "rgba(255,255,255,.07)"}`,
        borderRadius: 14, padding: "17px 20px", cursor: "pointer",
        transition: "background .15s, border-color .15s",
      }}
    >
      <div style={{
        width: 42, height: 42, borderRadius: 10, flexShrink: 0,
        background: "rgba(122,0,25,.35)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        <LayoutGrid size={20} style={{ color: "#FFCC33" }} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "#fff", marginBottom: 4 }}>Department Explorer</div>
        <div style={{ fontSize: 12, color: "#8f878a", maxWidth: 520 }}>
          Browse every UMN department, course, and professor in one place. Comparisons, grade charts, and schedules all appear right inside your chat.
        </div>
      </div>
      <span style={{ fontSize: 13, fontWeight: 600, color: "#FFCC33", flexShrink: 0 }}>Open →</span>
    </button>
  );
};

const ChatPage = ({
  messages,
  isTyping,
  typingMessage,
  isLoading,
  loadingLabel,
  error,
  messagesEndRef,
  chatContainerRef,
  inputValue,
  setInputValue,
  onSend,
  onSendDirect,
  onNavigate,
  profile,
  conversationCount,
}) => {
  const isEmpty = messages.length === 0 && !isLoading && !isTyping;
  const textareaRef = useRef(null);

  const fillInput = (text) => {
    setInputValue(text);
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, overflow: "hidden" }}>

      {/* Scrollable content area */}
      <div
        ref={chatContainerRef}
        style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: isEmpty ? "34px 40px 24px" : "28px 40px 24px" }}
      >
        <div style={{ maxWidth: isEmpty ? 1040 : 768, margin: "0 auto" }}>
          {isEmpty ? (
            <HomeView onFill={fillInput} onNavigate={onNavigate} profile={profile} conversationCount={conversationCount} />
          ) : (
            <ChatWindow
              messages={messages}
              isTyping={isTyping}
              typingMessage={typingMessage}
              isLoading={isLoading}
              loadingLabel={loadingLabel}
              error={error}
              messagesEndRef={messagesEndRef}
              onSendDirect={onSendDirect}
            />
          )}
        </div>
      </div>

      {/* Composer dock */}
      <div style={{
        borderTop: "1px solid rgba(255,255,255,.06)",
        background: "#1c1a1b",
        padding: "14px 40px 18px",
        flexShrink: 0,
      }}>
        <div style={{ maxWidth: 760, margin: "0 auto" }}>
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSend={onSend}
            placeholder="Ask GopherGPT anything…"
            disabled={isLoading || isTyping}
            textareaRef={textareaRef}
          />
          <p style={{ textAlign: "center", fontSize: 11, color: "#6c6466", margin: "8px 0 0" }}>
            GopherGPT can make mistakes — verify course details on{" "}
            <strong style={{ fontWeight: 600 }}>onestop.umn.edu</strong>
          </p>
        </div>
      </div>

    </div>
  );
};

export default ChatPage;
