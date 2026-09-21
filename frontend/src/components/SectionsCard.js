import React, { useState } from "react";

function formatTime(raw) {
  if (raw === null || raw === undefined || raw === "") return "";
  const s = String(raw).replace(":", "").replace(/\D.*/, "");
  if (!s) return "";
  const padded = s.padStart(4, "0");
  const h = parseInt(padded.slice(0, 2), 10);
  const m = padded.slice(2, 4);
  if (isNaN(h)) return "";
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${h12}:${m} ${ampm}`;
}

function formatTimeRange(mp) {
  const start = formatTime(mp.start_time);
  const end = formatTime(mp.end_time);
  if (!start && !end) return null;
  if (!end) return start;
  return `${start} – ${end}`;
}

function formatDays(days) {
  if (!Array.isArray(days) || !days.length) return null;
  return days.join("");
}

function StatusPill({ isOpen, status }) {
  if (isOpen) {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, fontWeight: 600, color: "#5ad17f", flexShrink: 0 }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#5ad17f", boxShadow: "0 0 0 3px rgba(90,209,127,.16)", flexShrink: 0 }} />
        Open
      </span>
    );
  }
  // Waitlist check: if status code indicates waitlist
  if (status === "W") {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, fontWeight: 600, color: "#f59e0b", flexShrink: 0 }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#f59e0b", boxShadow: "0 0 0 3px rgba(245,158,11,.16)", flexShrink: 0 }} />
        Waitlist
      </span>
    );
  }
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, fontWeight: 600, color: "#9a7070", flexShrink: 0 }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#7a4040", flexShrink: 0 }} />
      Closed
    </span>
  );
}

const TypeTag = ({ component }) => {
  const isLec = component === "LEC";
  return (
    <span style={{
      fontSize: 9, fontWeight: 700, letterSpacing: ".04em",
      padding: "2px 5px", borderRadius: 5,
      color: isLec ? "#FFCC33" : "#e98aa0",
      background: isLec ? "rgba(255,204,51,.13)" : "rgba(122,0,25,.45)",
    }}>
      {component}
    </span>
  );
};

const SectionRow = ({ section }) => {
  const [hovered, setHovered] = useState(false);
  const instructor = section.instructors?.[0] || null;
  const mp = section.meeting_patterns?.[0] || null;
  const days = mp ? formatDays(mp.days) : null;
  const timeRange = mp ? formatTimeRange(mp) : null;
  const location = mp?.location || null;
  const dimmed = !section.is_open && section.status !== "W";

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: "11px 14px",
        borderTop: "1px solid rgba(255,255,255,.05)",
        background: hovered ? "rgba(255,255,255,.035)" : "transparent",
        opacity: dimmed ? 0.6 : 1,
        transition: "background .12s",
      }}
    >
      {/* Line 1: type tag + number · instructor · status */}
      <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
        <span style={{
          display: "flex", alignItems: "center", gap: 7,
          fontFamily: "'SF Mono', ui-monospace, Menlo, monospace",
          fontSize: 12.5, fontWeight: 700, color: "#fff", flexShrink: 0,
        }}>
          <TypeTag component={section.component} />
          {section.number}
        </span>
        <span style={{
          flex: 1, minWidth: 0, fontSize: 13,
          color: instructor ? "#ddd6d8" : "#7c7375",
          fontStyle: instructor ? "normal" : "italic",
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>
          {instructor || "TBA"}
        </span>
        <StatusPill isOpen={section.is_open} status={section.status} />
      </div>

      {/* Line 2: days chip · time · location */}
      {(days || timeRange || location) && (
        <div style={{
          display: "flex", alignItems: "center", flexWrap: "wrap",
          gap: 7, marginTop: 6, fontSize: 12, color: "#9a9294",
          fontVariantNumeric: "tabular-nums",
        }}>
          {days && (
            <span style={{
              fontFamily: "'SF Mono', ui-monospace, Menlo, monospace",
              fontSize: 11, fontWeight: 700, color: "#fff",
              background: "rgba(255,255,255,.07)", padding: "2px 6px",
              borderRadius: 5, letterSpacing: ".03em", flexShrink: 0,
            }}>
              {days}
            </span>
          )}
          {timeRange && <span>{timeRange}</span>}
          {location && (
            <>
              <span style={{ color: "#5a5254" }}>·</span>
              <span>{location}</span>
            </>
          )}
        </div>
      )}
    </div>
  );
};

const SectionGroup = ({ label, sections }) => (
  <div>
    <div style={{
      display: "flex", alignItems: "center", gap: 7,
      padding: "9px 14px 7px",
      fontSize: 10.5, fontWeight: 700, letterSpacing: ".07em",
      textTransform: "uppercase", color: "#FFCC33",
      background: "rgba(122,0,25,.16)",
    }}>
      {label}
      <span style={{ color: "#8f878a", fontWeight: 600 }}>· {sections.length}</span>
    </div>
    {sections.map((s) => (
      <SectionRow key={s.number || s.class_number} section={s} />
    ))}
  </div>
);

export default function SectionsCard({ course }) {
  const { code, term, sections = [] } = course;

  const grouped = {};
  sections.forEach((s) => {
    const key = s.component || "OTHER";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(s);
  });

  // Canonical order: LEC first, then DIS, LAB, then anything else
  const ORDER = ["LEC", "DIS", "LAB"];
  const keys = [
    ...ORDER.filter((k) => grouped[k]),
    ...Object.keys(grouped).filter((k) => !ORDER.includes(k)),
  ];

  const LABEL = { LEC: "Lectures", DIS: "Discussions", LAB: "Labs" };

  const lecCount = (grouped.LEC || []).length;
  const disCount = (grouped.DIS || []).length;
  const labCount = (grouped.LAB || []).length;
  const openCount = sections.filter((s) => s.is_open).length;

  const subParts = [
    lecCount > 0 && `${lecCount} lecture${lecCount !== 1 ? "s" : ""}`,
    disCount > 0 && `${disCount} discussion${disCount !== 1 ? "s" : ""}`,
    labCount > 0 && `${labCount} lab${labCount !== 1 ? "s" : ""}`,
  ].filter(Boolean);

  const termDisplay = term
    ? term.replace(/\b\w/g, (c) => c.toUpperCase())
    : "";

  return (
    <div style={{
      background: "#252122", border: "1px solid rgba(255,255,255,.08)",
      borderRadius: 14, padding: "16px 18px", marginBottom: 16,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 15 }}>
        <div>
          <div style={{ fontSize: 13.5, fontWeight: 700, color: "#fff" }}>
            {code} · {termDisplay} sections
          </div>
          {subParts.length > 0 && (
            <div style={{ fontSize: 11.5, color: "#8f878a", marginTop: 3 }}>
              {subParts.join(" · ")}
            </div>
          )}
        </div>
        <div style={{
          fontSize: 10, fontWeight: 700, color: "#8f878a",
          letterSpacing: ".07em", textTransform: "uppercase",
          display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap",
        }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#5ad17f", boxShadow: "0 0 0 3px rgba(90,209,127,.16)" }} />
          Live data
        </div>
      </div>

      {/* Section table */}
      <div style={{ border: "1px solid rgba(255,255,255,.07)", borderRadius: 12, overflow: "hidden", marginTop: 2 }}>
        {keys.map((key) => (
          <SectionGroup
            key={key}
            label={LABEL[key] || key}
            sections={grouped[key]}
          />
        ))}
        {sections.length === 0 && (
          <div style={{ padding: "16px 14px", fontSize: 13, color: "#7c7375" }}>
            No sections found for this term.
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{
        display: "flex", gap: 26, marginTop: 15,
        paddingTop: 14, borderTop: "1px solid rgba(255,255,255,.06)",
      }}>
        {[
          { label: "Sections", value: String(sections.length) },
          { label: "Open", value: openCount === sections.length ? "All" : String(openCount) },
          ...(lecCount > 0 ? [{ label: "Lectures", value: String(lecCount) }] : []),
          ...(disCount > 0 ? [{ label: "Discussions", value: String(disCount) }] : []),
          ...(labCount > 0 ? [{ label: "Labs", value: String(labCount) }] : []),
        ].map(({ label, value }) => (
          <div key={label}>
            <div style={{ fontSize: 10.5, color: "#8f878a", textTransform: "uppercase", letterSpacing: ".05em", fontWeight: 600, marginBottom: 4 }}>
              {label}
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#fff" }}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
