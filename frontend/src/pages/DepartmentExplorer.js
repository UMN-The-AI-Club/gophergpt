import React, { useState, useEffect } from "react";
import { Search, TrendingUp, Star, BookOpen, ChevronDown, ChevronRight } from "lucide-react";

// ─── formatters ────────────────────────────────────────────────────────────────

const fmt = (v) => (v == null ? "N/A" : new Intl.NumberFormat("en-US").format(v));
const fmtDec = (v) => (v == null ? "N/A" : Number(v).toFixed(2));
const fmtPct = (v) => (v == null ? "N/A" : `${(v * 100).toFixed(1)}%`);
const fmtCredits = (c) => {
  if (!c || c.min == null) return "N/A";
  return c.max == null || c.min === c.max ? `${c.min}` : `${c.min}–${c.max}`;
};

// ─── course classification ─────────────────────────────────────────────────────

const getCourseLevel = (courseNum) => {
  const n = parseInt(String(courseNum).match(/(\d+)/)?.[1]);
  if (n >= 8000) return "phd";
  if (n >= 5000) return "graduate";
  if (n >= 1000) return "undergraduate";
  return "unknown";
};

const getCourseGroup = (courseNum) => {
  const n = parseInt(String(courseNum).match(/(\d+)/)?.[1]);
  if (!n) return null;
  return Math.min(Math.floor(n / 1000), 9);
};

// ─── design tokens per level-group ─────────────────────────────────────────────

const GROUP_META = {
  1: { label: "1000 Level", color: "rgba(255,204,51,.6)",  border: "rgba(255,204,51,.1)",  bg: "rgba(255,204,51,.03)" },
  2: { label: "2000 Level", color: "rgba(255,204,51,.6)",  border: "rgba(255,204,51,.1)",  bg: "rgba(255,204,51,.03)" },
  3: { label: "3000 Level", color: "rgba(255,204,51,.75)", border: "rgba(255,204,51,.14)", bg: "rgba(255,204,51,.05)" },
  4: { label: "4000 Level", color: "#FFCC33",              border: "rgba(255,204,51,.22)", bg: "rgba(255,204,51,.07)" },
  5: { label: "5000 Level", color: "#e98aa0",              border: "rgba(122,0,25,.22)",   bg: "rgba(122,0,25,.07)"   },
  6: { label: "6000 Level", color: "#e98aa0",              border: "rgba(122,0,25,.22)",   bg: "rgba(122,0,25,.07)"   },
  7: { label: "7000 Level", color: "#e98aa0",              border: "rgba(122,0,25,.22)",   bg: "rgba(122,0,25,.07)"   },
  8: { label: "8000 Level", color: "#9a9294",              border: "rgba(255,255,255,.07)", bg: "rgba(255,255,255,.02)" },
  9: { label: "9000 Level", color: "#9a9294",              border: "rgba(255,255,255,.07)", bg: "rgba(255,255,255,.02)" },
};

const LEVEL_GROUPS = {
  undergraduate: [1, 2, 3, 4],
  graduate:      [5, 6, 7],
  phd:           [8, 9],
  all:           [1, 2, 3, 4, 5, 6, 7, 8, 9],
};

const LEVEL_TABS = [
  { key: "all",           label: "All Courses"   },
  { key: "undergraduate", label: "Undergraduate" },
  { key: "graduate",      label: "Graduate"      },
  { key: "phd",          label: "PhD"            },
];

const INTRO_HINTS = ["introduction to", "intro to", "foundations", "fundamentals", "elementary", "principles", "basic "];
const KNOWN_REQUIRED_COURSES = {
  CSCI: new Set(["1133", "1913", "1933", "2011", "2021", "2033", "2041", "4041"]),
  MATH: new Set(["1271", "1272", "1371", "1372", "1571", "1572", "2243", "2263", "2373", "2374", "3283W"]),
  STAT: new Set(["3011", "3021", "3032", "5101"]),
  BIOL: new Set(["1951", "1961", "2003", "2004"]),
  CHEM: new Set(["1015", "1061", "1062", "2301", "2302"]),
  PHYS: new Set(["1301W", "1302W", "1401V", "1402V"]),
};

const computeFeatured = (courses, level, deptCode = "") => {
  const pool = level === "all" ? courses : courses.filter((c) => getCourseLevel(c.course_num) === level);
  const popular = [...pool].sort((a, b) => (b.total_students ?? 0) - (a.total_students ?? 0)).slice(0, 8);
  const bestRated = [...pool]
    .filter((c) => (c.metrics.responses ?? 0) >= 50 && c.metrics.recommend != null)
    .sort((a, b) => b.metrics.recommend - a.metrics.recommend)
    .slice(0, 8);
  const electivePool = pool.filter((c) => {
    const rawNum = String(c.course_num).trim();
    const n = parseInt(rawNum.match(/(\d+)/)?.[1]);
    if (!n) return false;
    const minLevel = level === "undergraduate" ? 3000 : level === "graduate" ? 5000 : level === "phd" ? 8000 : 3000;
    if (n < minLevel) return false;
    const req = KNOWN_REQUIRED_COURSES[deptCode.toUpperCase()];
    if (req?.has(rawNum)) return false;
    return !INTRO_HINTS.some((h) => `${c.title} ${c.description || ""}`.toLowerCase().includes(h));
  });
  const popularElectives = [...electivePool].sort((a, b) => (b.total_students ?? 0) - (a.total_students ?? 0)).slice(0, 8);
  return { popular, bestRated, popularElectives };
};

// ─── small reusable pieces ─────────────────────────────────────────────────────

const SummaryCard = ({ label, value }) => (
  <div style={{
    background: "#252122", border: "1px solid rgba(255,255,255,.07)",
    borderRadius: 14, padding: "15px 17px",
  }}>
    <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".05em", color: "#9a9294", marginBottom: 8 }}>
      {label}
    </div>
    <div style={{ fontSize: 22, fontWeight: 700, color: "#FFCC33", letterSpacing: "-.02em", lineHeight: 1.15 }}>
      {value}
    </div>
  </div>
);

const FeaturedItem = ({ course, metricLabel, renderMetric }) => {
  const [hov, setHov] = useState(false);
  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        borderRadius: 10, padding: "10px 12px",
        background: hov ? "rgba(255,255,255,.04)" : "transparent",
        borderBottom: "1px solid rgba(255,255,255,.05)",
        transition: "background .12s", cursor: "default",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#FFCC33", marginBottom: 2 }}>{course.course_num}</div>
          <div style={{ fontSize: 13, color: "#ddd6d8", lineHeight: 1.35, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 200 }}>{course.title}</div>
        </div>
        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <div style={{ fontSize: 10.5, color: "#8f878a", marginBottom: 2 }}>{metricLabel}</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#fff" }}>{renderMetric(course)}</div>
        </div>
      </div>
      <div style={{ fontSize: 11, color: "#6c6466", marginTop: 4 }}>{fmt(course.total_students)} students</div>
    </div>
  );
};

const FeaturedList = ({ Icon, title, subtitle, items, metricLabel, renderMetric }) => (
  <div style={{
    background: "#252122", border: "1px solid rgba(255,255,255,.08)",
    borderRadius: 14, overflow: "hidden",
  }}>
    <div style={{
      padding: "14px 16px 12px",
      borderBottom: "1px solid rgba(255,255,255,.06)",
      background: "linear-gradient(180deg, rgba(255,255,255,.02) 0%, transparent 100%)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 3 }}>
        <Icon size={13} style={{ color: "#FFCC33" }} />
        <span style={{ fontSize: 13, fontWeight: 700, color: "#fff" }}>{title}</span>
      </div>
      <p style={{ fontSize: 11.5, color: "#8f878a", margin: 0 }}>{subtitle}</p>
    </div>
    <div style={{ padding: "6px 4px" }}>
      {items.map((course) => (
        <FeaturedItem key={`${title}-${course.id}`} course={course} metricLabel={metricLabel} renderMetric={renderMetric} />
      ))}
      {items.length === 0 && (
        <p style={{ fontSize: 13, color: "#6c6466", padding: "12px 12px" }}>No courses matched this view.</p>
      )}
    </div>
  </div>
);

const CourseRow = ({ course }) => {
  const [hov, setHov] = useState(false);
  return (
    <tr
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{ borderBottom: "1px solid rgba(255,255,255,.05)", background: hov ? "rgba(255,255,255,.03)" : "transparent", transition: "background .1s" }}
    >
      <td style={{ padding: "12px 14px", fontWeight: 700, color: "#FFCC33", fontSize: 13, whiteSpace: "nowrap" }}>{course.course_num}</td>
      <td style={{ padding: "12px 14px" }}>
        <div style={{ fontWeight: 600, color: "#ddd6d8", fontSize: 13.5 }}>{course.title}</div>
        {course.description && (
          <div style={{ marginTop: 3, fontSize: 12, color: "#8f878a", lineHeight: 1.45, maxWidth: 480 }}>
            {course.description.slice(0, 160)}{course.description.length > 160 ? "…" : ""}
          </div>
        )}
        {course.catalog_url && (
          <a href={course.catalog_url} target="_blank" rel="noreferrer"
            style={{ display: "inline-block", marginTop: 4, fontSize: 11.5, color: "#FFCC33", textDecoration: "none", opacity: 0.75 }}
            onMouseOver={e => e.target.style.opacity = 1}
            onMouseOut={e => e.target.style.opacity = 0.75}
          >
            View catalog →
          </a>
        )}
      </td>
      <td style={{ padding: "12px 14px", fontSize: 13, color: "#c9bfc1", whiteSpace: "nowrap" }}>{fmtCredits(course.credits)}</td>
      <td style={{ padding: "12px 14px", fontSize: 13, color: "#c9bfc1", whiteSpace: "nowrap" }}>{fmt(course.total_students)}</td>
      <td style={{ padding: "12px 14px", fontSize: 13, color: "#c9bfc1", whiteSpace: "nowrap" }}>{fmtDec(course.metrics.recommend)}</td>
      <td style={{ padding: "12px 14px", fontSize: 13, color: "#c9bfc1", whiteSpace: "nowrap" }}>{fmt(course.metrics.responses)}</td>
      <td style={{ padding: "12px 14px", fontSize: 13, color: "#c9bfc1", whiteSpace: "nowrap" }}>{fmtPct(course.metrics.challenge_rate)}</td>
    </tr>
  );
};

const CourseTableHead = () => (
  <thead>
    <tr style={{ borderBottom: "1px solid rgba(255,255,255,.08)" }}>
      {["Course", "Title", "Credits", "Students", "Recommend", "Responses", "Challenge"].map((h) => (
        <th key={h} style={{ padding: "10px 14px", fontSize: 11, fontWeight: 700, color: "#8f878a", textTransform: "uppercase", letterSpacing: ".05em", textAlign: "left" }}>
          {h}
        </th>
      ))}
    </tr>
  </thead>
);

// ─── main component ─────────────────────────────────────────────────────────────

const DepartmentExplorer = () => {
  const [inputValue, setInputValue]       = useState("");
  const [deptData, setDeptData]           = useState(null);
  const [loading, setLoading]             = useState(false);
  const [error, setError]                 = useState("");
  const [filterText, setFilterText]       = useState("");
  const [sortKey, setSortKey]             = useState("total_students");
  const [sortDir, setSortDir]             = useState("desc");
  const [activeLevel, setActiveLevel]     = useState("all");
  const [collapsed, setCollapsed]         = useState({});
  const [inputFocused, setInputFocused]   = useState(false);

  useEffect(() => {
    const userId = localStorage.getItem("gopher_user_id");
    if (!userId) return;
    fetch(`${process.env.REACT_APP_API_BASE}/profile?user_id=${encodeURIComponent(userId)}`)
      .then((r) => r.json())
      .then((d) => {
        const l = d?.profile?.level?.toLowerCase();
        if (["undergraduate", "graduate", "phd"].includes(l)) setActiveLevel(l);
      })
      .catch(() => {});
  }, []);

  const fetchDepartment = async () => {
    const dept = inputValue.trim();
    if (!dept || loading) return;
    setLoading(true); setError(""); setDeptData(null); setCollapsed({});
    try {
      const res = await fetch(`${process.env.REACT_APP_API_BASE}/umn/dept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dept }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) { setError(data.error || "Unable to load department data."); return; }
      setDeptData(data);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const applySort = (courses) =>
    [...courses].sort((a, b) => {
      if (sortKey === "course_num") {
        const cmp = a.course_num.localeCompare(b.course_num, undefined, { numeric: true, sensitivity: "base" });
        return sortDir === "asc" ? cmp : -cmp;
      }
      let av = a[sortKey], bv = b[sortKey];
      if (sortKey === "recommend")      { av = a.metrics.recommend ?? -1;      bv = b.metrics.recommend ?? -1; }
      if (sortKey === "challenge_rate") { av = a.metrics.challenge_rate ?? -1; bv = b.metrics.challenge_rate ?? -1; }
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

  const filterByText  = (cs) => {
    const q = filterText.trim().toLowerCase();
    return q ? cs.filter((c) => c.course_num.toLowerCase().includes(q) || c.title.toLowerCase().includes(q)) : cs;
  };
  const filterByLevel = (cs, lvl) => lvl === "all" ? cs : cs.filter((c) => getCourseLevel(c.course_num) === lvl);

  const levelCounts = deptData ? {
    undergraduate: deptData.courses.filter((c) => getCourseLevel(c.course_num) === "undergraduate").length,
    graduate:      deptData.courses.filter((c) => getCourseLevel(c.course_num) === "graduate").length,
    phd:           deptData.courses.filter((c) => getCourseLevel(c.course_num) === "phd").length,
  } : {};

  const filteredSorted = deptData ? applySort(filterByText(filterByLevel(deptData.courses, activeLevel))) : [];
  const levelGroups    = (LEVEL_GROUPS[activeLevel] || []).map((g) => ({
    group: g, meta: GROUP_META[g],
    courses: filteredSorted.filter((c) => getCourseGroup(c.course_num) === g),
  }));
  const featured = deptData ? computeFeatured(deptData.courses, activeLevel, deptData.dept.code) : { popular: [], bestRated: [], popularElectives: [] };

  // ── shared input style ────────────────────────────────────────────────────────
  const inputStyle = (focused = false) => ({
    background: "#2c2829",
    border: `1.5px solid ${focused ? "rgba(255,204,51,.6)" : "rgba(255,255,255,.1)"}`,
    boxShadow: focused ? "0 0 0 3px rgba(255,204,51,.08)" : "none",
    borderRadius: 10, padding: "10px 14px",
    color: "#fff", fontSize: 13.5, outline: "none",
    transition: "border-color .15s, box-shadow .15s",
  });

  const selectStyle = {
    background: "#2c2829",
    border: "1.5px solid rgba(255,255,255,.1)",
    borderRadius: 10, padding: "10px 12px",
    color: "#fff", fontSize: 13, outline: "none",
    cursor: "pointer",
  };

  return (
    <div style={{ flex: 1, overflowY: "auto", background: "#1a1718", padding: "34px 40px 40px" }}>
      <div style={{ maxWidth: 1120, margin: "0 auto", display: "flex", flexDirection: "column", gap: 24 }}>

        {/* Page header */}
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <div style={{
              width: 34, height: 34, borderRadius: 9, flexShrink: 0,
              background: "rgba(122,0,25,.35)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <BookOpen size={17} style={{ color: "#FFCC33" }} />
            </div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: "#fff", letterSpacing: "-.02em", margin: 0 }}>
              Department Explorer
            </h2>
          </div>
          <p style={{ fontSize: 13.5, color: "#8f878a", margin: 0, maxWidth: 560, lineHeight: 1.5 }}>
            Explore any UMN department — course volume, grade patterns, and student ratings all in one place.
          </p>
        </div>

        {/* Search bar */}
        <div style={{
          display: "flex", gap: 10, alignItems: "stretch",
          background: "#252122", border: "1px solid rgba(255,255,255,.08)",
          borderRadius: 14, padding: "14px 16px",
        }}>
          <div style={{ position: "relative", flex: 1 }}>
            <Search size={15} style={{
              position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)",
              color: inputFocused ? "#FFCC33" : "#6c6466", pointerEvents: "none", transition: "color .15s",
            }} />
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === "Enter" && fetchDepartment()}
              onFocus={() => setInputFocused(true)}
              onBlur={() => setInputFocused(false)}
              placeholder="Enter department code (e.g. CSCI, MATH, BIOL)"
              style={{ ...inputStyle(inputFocused), width: "100%", boxSizing: "border-box", paddingLeft: 36 }}
            />
          </div>
          <button
            onClick={fetchDepartment}
            disabled={loading}
            style={{
              background: loading ? "rgba(255,204,51,.4)" : "#FFCC33",
              color: "#1a0810", border: "none",
              borderRadius: 10, padding: "0 22px",
              fontWeight: 700, fontSize: 13.5, cursor: loading ? "not-allowed" : "pointer",
              flexShrink: 0, transition: "background .15s",
            }}
          >
            {loading ? "Loading…" : "Explore"}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: "rgba(122,0,25,.18)", border: "1px solid rgba(122,0,25,.4)",
            borderRadius: 12, padding: "13px 16px", fontSize: 13.5, color: "#f4b8c0",
          }}>
            {error}
          </div>
        )}

        {/* Empty state */}
        {!deptData && !loading && !error && (
          <div style={{
            border: "1.5px dashed rgba(255,255,255,.1)", borderRadius: 14,
            padding: "52px 32px", textAlign: "center",
            color: "#6c6466", fontSize: 13.5, lineHeight: 1.6,
          }}>
            Search for a department to see summary metrics, featured course views,<br />and a sortable course explorer.
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div style={{ textAlign: "center", color: "#8f878a", fontSize: 13, padding: "48px 0" }}>
            <div style={{ fontSize: 28, marginBottom: 12, opacity: 0.5 }}>⬤</div>
            Fetching department data…
          </div>
        )}

        {/* ── Department results ── */}
        {deptData && (
          <>
            {/* Dept header */}
            <div style={{
              background: "#252122",
              border: "1px solid rgba(255,255,255,.08)",
              borderRadius: 14, padding: "20px 22px",
              backgroundImage: "radial-gradient(ellipse at 0% 0%, rgba(122,0,25,.18) 0%, transparent 55%)",
            }}>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", justifyContent: "space-between", gap: 10, marginBottom: 18 }}>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".07em", color: "#8f878a", marginBottom: 4 }}>
                    {deptData.dept.campus}
                  </div>
                  <h3 style={{ fontSize: 22, fontWeight: 700, color: "#fff", margin: 0, letterSpacing: "-.02em" }}>
                    {deptData.dept.name}{" "}
                    <span style={{ color: "#FFCC33" }}>({deptData.dept.code})</span>
                  </h3>
                </div>
                <span style={{ fontSize: 12, color: "#6c6466" }}>
                  Based on historical GopherGrades & SRT data
                </span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
                <SummaryCard label="Courses"        value={fmt(deptData.summary.course_count)}        />
                <SummaryCard label="Total Students" value={fmt(deptData.summary.total_students)}       />
                <SummaryCard label="Median Size"    value={fmt(deptData.summary.median_course_size)}  />
                <SummaryCard label="Avg Recommend"  value={fmtDec(deptData.summary.avg_recommend)}    />
              </div>
            </div>

            {/* Level tabs */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {LEVEL_TABS.map(({ key, label }) => {
                const count  = key === "all" ? deptData.courses.length : levelCounts[key] ?? 0;
                const active = activeLevel === key;
                return (
                  <button
                    key={key}
                    onClick={() => setActiveLevel(key)}
                    style={{
                      display: "inline-flex", alignItems: "center", gap: 7,
                      borderRadius: 999, padding: "7px 16px",
                      fontSize: 13, fontWeight: 600, cursor: "pointer",
                      border: active ? "1.5px solid #FFCC33" : "1.5px solid rgba(255,255,255,.1)",
                      background: active ? "#FFCC33" : "#252122",
                      color: active ? "#1a0810" : "#9a9294",
                      transition: "background .15s, color .15s, border-color .15s",
                    }}
                  >
                    {label}
                    <span style={{
                      fontSize: 11, borderRadius: 999, padding: "1px 7px",
                      background: active ? "rgba(26,8,16,.25)" : "rgba(255,255,255,.07)",
                      color: active ? "#1a0810" : "#6c6466",
                    }}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Featured 3-up */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
              <FeaturedList
                Icon={TrendingUp} title="Popular Courses"
                subtitle="Highest total enrollment"
                items={featured.popular}
                metricLabel="Students"
                renderMetric={(c) => fmt(c.total_students)}
              />
              <FeaturedList
                Icon={Star} title="Best Rated"
                subtitle="Highest recommend score (50+ responses)"
                items={featured.bestRated}
                metricLabel="Recommend"
                renderMetric={(c) => fmtDec(c.metrics.recommend)}
              />
              <FeaturedList
                Icon={BookOpen} title="Popular Electives"
                subtitle="Upper-division high-enrollment picks"
                items={featured.popularElectives}
                metricLabel="Students"
                renderMetric={(c) => fmt(c.total_students)}
              />
            </div>

            {/* Course Explorer */}
            <div style={{
              background: "#252122", border: "1px solid rgba(255,255,255,.08)",
              borderRadius: 14, padding: "20px 22px",
            }}>
              {/* Explorer header + controls */}
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", justifyContent: "space-between", gap: 14, marginBottom: 18 }}>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 700, color: "#fff", margin: "0 0 4px" }}>
                    {activeLevel === "undergraduate" ? "Course Catalog"
                     : activeLevel === "graduate"    ? "Graduate Courses"
                     : activeLevel === "phd"         ? "PhD Courses"
                     : "Course Explorer"}
                  </h3>
                  <p style={{ fontSize: 12, color: "#8f878a", margin: 0 }}>
                    {activeLevel === "undergraduate" ? "Undergraduate courses grouped by level."
                     : activeLevel === "graduate"    ? "Graduate-level courses (5xxx–7xxx)."
                     : activeLevel === "phd"         ? "PhD-level courses (8xxx+)."
                     : "Full department catalog. Switch tabs to filter by academic level."}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <input
                    type="text"
                    value={filterText}
                    onChange={(e) => setFilterText(e.target.value)}
                    placeholder="Filter by number or title"
                    style={{ ...inputStyle(false), width: 220 }}
                  />
                  <select value={sortKey} onChange={(e) => setSortKey(e.target.value)} style={selectStyle}>
                    <option value="total_students">Students</option>
                    <option value="course_num">Course Number</option>
                    <option value="recommend">Recommend</option>
                    <option value="challenge_rate">Challenge Rate</option>
                  </select>
                  <select value={sortDir} onChange={(e) => setSortDir(e.target.value)} style={selectStyle}>
                    <option value="desc">Descending</option>
                    <option value="asc">Ascending</option>
                  </select>
                </div>
              </div>

              {/* Grouped collapsible course tables */}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {levelGroups.map(({ group, meta, courses }) =>
                  courses.length === 0 ? null : (
                    <div key={group}>
                      <button
                        onClick={() => setCollapsed((prev) => ({ ...prev, [group]: !prev[group] }))}
                        style={{
                          width: "100%", display: "flex", alignItems: "center", gap: 10,
                          padding: "9px 14px", borderRadius: 9, cursor: "pointer", textAlign: "left",
                          background: meta.bg,
                          border: `1px solid ${meta.border}`,
                          transition: "background .12s",
                        }}
                      >
                        {collapsed[group]
                          ? <ChevronRight size={13} style={{ color: meta.color, flexShrink: 0 }} />
                          : <ChevronDown  size={13} style={{ color: meta.color, flexShrink: 0 }} />
                        }
                        <span style={{ fontSize: 12, fontWeight: 700, color: meta.color }}>{meta.label}</span>
                        <span style={{ fontSize: 12, color: "#6c6466" }}>· {courses.length} courses</span>
                      </button>
                      {!collapsed[group] && (
                        <div style={{ overflowX: "auto", marginTop: 2 }}>
                          <table style={{ minWidth: "100%", borderCollapse: "collapse" }}>
                            <CourseTableHead />
                            <tbody>
                              {courses.map((c) => <CourseRow key={c.id} course={c} />)}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )
                )}
                {filteredSorted.length === 0 && (
                  <p style={{ fontSize: 13, color: "#6c6466", padding: "12px 0" }}>No courses matched your current filter.</p>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default DepartmentExplorer;
