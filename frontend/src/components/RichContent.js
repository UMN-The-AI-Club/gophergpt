import React, { useState } from "react";
import { ExternalLink, TrendingUp } from "lucide-react";
import GradeChart from "./compare/GradeChart";
import SRTRatings from "./compare/SRTRatings";
import SectionsCard from "./SectionsCard";

// ─── helpers ───────────────────────────────────────────────────────────────────

function shorten(text, max = 220) {
    if (!text) return "";
    const s = String(text).replace(/\s+/g, " ").trim();
    return s.length > max ? `${s.slice(0, max).trim()}…` : s;
}

// ─── shell shared by all cards ─────────────────────────────────────────────────

const CardShell = ({ children, accent = false }) => (
    <div style={{
        background: "#252122",
        border: "1px solid rgba(255,255,255,.08)",
        borderRadius: 14,
        overflow: "hidden",
        ...(accent ? { backgroundImage: "radial-gradient(ellipse at 0% 0%, rgba(122,0,25,.14) 0%, transparent 55%)" } : {}),
    }}>
        {children}
    </div>
);

const CardHeader = ({ eyebrow, title, badge, right }) => (
    <div style={{
        padding: "15px 18px 13px",
        borderBottom: "1px solid rgba(255,255,255,.06)",
    }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
            <div>
                {eyebrow && (
                    <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".08em", color: "#8f878a", marginBottom: 4 }}>
                        {eyebrow}
                    </div>
                )}
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 700, color: "#fff", margin: 0, letterSpacing: "-.01em" }}>
                        {title}
                    </h3>
                    {badge && (
                        <span style={{
                            fontSize: 9.5, fontWeight: 700, letterSpacing: ".05em",
                            color: "#FFCC33", background: "rgba(255,204,51,.1)",
                            border: "1px solid rgba(255,204,51,.2)",
                            padding: "2px 7px", borderRadius: 999,
                        }}>
                            {badge}
                        </span>
                    )}
                </div>
            </div>
            {right}
        </div>
    </div>
);

// ─── Research card ──────────────────────────────────────────────────────────────

function ResearchCard({ item }) {
    const results = Array.isArray(item.results) ? item.results.slice(0, 6) : [];
    const summary = shorten(item.summary, 160);

    return (
        <CardShell accent>
            <CardHeader
                eyebrow="Research Explorer"
                title="UMN Research Snapshot"
                badge={`${results.length} result${results.length === 1 ? "" : "s"}`}
            />
            {summary && (
                <div style={{ padding: "10px 18px 0", fontSize: 12.5, color: "#9a9294", lineHeight: 1.55 }}>
                    {summary}
                </div>
            )}
            <div style={{ padding: "10px 12px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
                {results.map((result, i) => (
                    <ResultRow key={`${result.url || result.title}-${i}`} result={result} />
                ))}
            </div>
        </CardShell>
    );
}

const ResultRow = ({ result }) => {
    const [hov, setHov] = useState(false);
    return (
        <a
            href={result.url}
            target="_blank"
            rel="noreferrer"
            onMouseEnter={() => setHov(true)}
            onMouseLeave={() => setHov(false)}
            style={{
                display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12,
                borderRadius: 10, border: `1px solid ${hov ? "rgba(255,204,51,.25)" : "rgba(255,255,255,.06)"}`,
                background: hov ? "rgba(255,255,255,.04)" : "transparent",
                padding: "10px 12px",
                textDecoration: "none",
                transition: "background .12s, border-color .12s",
            }}
        >
            <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{
                    fontSize: 13, fontWeight: 600, color: hov ? "#ffd966" : "#FFCC33",
                    marginBottom: 3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>
                    {shorten(result.title, 72) || "Untitled result"}
                </div>
                <div style={{ fontSize: 12, color: "#8f878a", lineHeight: 1.45, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                    {shorten(result.snippet, 130)}
                </div>
                {result.url && (
                    <div style={{ fontSize: 10.5, color: "#6c6466", marginTop: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {result.url.replace(/^https?:\/\//, "")}
                    </div>
                )}
            </div>
            <div style={{ flexShrink: 0, marginTop: 1 }}>
                <ExternalLink size={13} style={{ color: hov ? "#FFCC33" : "#6c6466", transition: "color .12s" }} />
            </div>
        </a>
    );
};

// ─── Course compare card ────────────────────────────────────────────────────────

function CourseCompareCard({ item }) {
    const courses = Array.isArray(item.courses) ? item.courses : [];
    const summary = item.summary || "";

    return (
        <CardShell accent>
            <CardHeader
                eyebrow="Course Compare"
                title={courses.map(c => c.code).join(" vs ")}
            />
            {summary && (
                <div style={{ padding: "10px 18px 14px", fontSize: 13, color: "#c9bfc1", lineHeight: 1.6 }}>
                    {summary}
                </div>
            )}
            <div style={{
                display: "grid",
                gridTemplateColumns: courses.length >= 2 ? "1fr 1fr" : "1fr",
                gap: 1,
                background: "rgba(255,255,255,.05)",
            }}>
                {courses.map((course) => (
                    <CoursePanelBlock key={course.code} course={course} />
                ))}
            </div>
        </CardShell>
    );
}

const CoursePanelBlock = ({ course }) => (
    <div style={{ background: "#1e1b1c", padding: "18px 18px 20px" }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: "#FFCC33", marginBottom: 16 }}>{course.code}</div>
        {course.data?.total_grades && (
            <GradeChart grades={course.data.total_grades} />
        )}
        {course.data?.srt_vals && (
            <div style={{ marginTop: 22 }}>
                <SRTRatings srtVals={course.data.srt_vals} />
            </div>
        )}
    </div>
);

// ─── Prof compare card ──────────────────────────────────────────────────────────

function ProfCompareCard({ item }) {
    const profs   = Array.isArray(item.profs) ? item.profs : [];
    const summary = item.summary || "";

    return (
        <CardShell accent>
            <CardHeader
                eyebrow="Professor Compare"
                title={profs.map(p => p.name).join(" vs ")}
            />
            {summary && (
                <div style={{ padding: "10px 18px 14px", fontSize: 13, color: "#c9bfc1", lineHeight: 1.6 }}>
                    {summary}
                </div>
            )}
            <div style={{
                display: "grid",
                gridTemplateColumns: profs.length >= 2 ? "1fr 1fr" : "1fr",
                gap: 1,
                background: "rgba(255,255,255,.05)",
            }}>
                {profs.map((prof) => (
                    <ProfPanelBlock key={prof.code} prof={prof} />
                ))}
            </div>
        </CardShell>
    );
}

const ProfPanelBlock = ({ prof }) => {
    const data          = prof.data || {};
    const distributions = Array.isArray(data.distributions) ? data.distributions : [];
    const rmpScore      = data.RMP_score ?? null;
    const rmpLink       = data.RMP_link  ?? null;

    const aggregatedGrades = {};
    distributions.forEach(dist => {
        Object.entries(dist.grades || {}).forEach(([grade, count]) => {
            aggregatedGrades[grade] = (aggregatedGrades[grade] || 0) + count;
        });
    });

    let bestSRT = null, maxResp = 0;
    distributions.forEach(dist => {
        if (!dist.srt_vals) return;
        try {
            const srt = typeof dist.srt_vals === "string" ? JSON.parse(dist.srt_vals) : dist.srt_vals;
            if ((srt.RESP || 0) > maxResp) { maxResp = srt.RESP; bestSRT = srt; }
        } catch {}
    });

    const seen = new Set();
    const courses = distributions.filter(d => {
        if (seen.has(d.course_num)) return false;
        seen.add(d.course_num); return true;
    });

    return (
        <div style={{ background: "#1e1b1c", padding: "18px 18px 20px" }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#FFCC33", marginBottom: 6 }}>{prof.name}</div>

            {rmpScore != null && (
                <div style={{ fontSize: 12.5, color: "#9a9294", marginBottom: 14 }}>
                    RateMyProfessors:{" "}
                    {rmpLink
                        ? <a href={rmpLink} target="_blank" rel="noreferrer" style={{ color: "#fff", fontWeight: 600, textDecoration: "none" }}>
                              {Number(rmpScore).toFixed(1)} / 5
                              <TrendingUp size={11} style={{ marginLeft: 4, verticalAlign: "middle", opacity: 0.6 }} />
                          </a>
                        : <span style={{ color: "#fff", fontWeight: 600 }}>{Number(rmpScore).toFixed(1)} / 5</span>
                    }
                </div>
            )}

            {courses.length > 0 && (
                <div style={{ marginBottom: 18 }}>
                    <div style={{ fontSize: 10.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "#6c6466", marginBottom: 8 }}>
                        Courses Taught
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                        {courses.slice(0, 8).map(d => (
                            <span key={d.course_num} title={d.class_desc} style={{
                                fontSize: 11.5, fontWeight: 600, color: "#FFCC33",
                                background: "rgba(255,204,51,.08)", border: "1px solid rgba(255,204,51,.15)",
                                borderRadius: 6, padding: "2px 8px",
                            }}>
                                {d.course_num}
                            </span>
                        ))}
                        {courses.length > 8 && (
                            <span style={{
                                fontSize: 11.5, color: "#6c6466",
                                background: "rgba(255,255,255,.05)", border: "1px solid rgba(255,255,255,.07)",
                                borderRadius: 6, padding: "2px 8px",
                            }}>
                                +{courses.length - 8} more
                            </span>
                        )}
                    </div>
                </div>
            )}

            {Object.keys(aggregatedGrades).length > 0 && (
                <GradeChart grades={aggregatedGrades} title="Grade Distribution (All Courses)" />
            )}

            {bestSRT && (
                <div style={{ marginTop: 22 }}>
                    <SRTRatings srtVals={bestSRT} title="Teaching Ratings" />
                </div>
            )}
        </div>
    );
};

// ─── Single-course grades card ─────────────────────────────────────────────────

function GradesCard({ item }) {
    const courses = Array.isArray(item.courses) ? item.courses : [];
    if (!courses.length) return null;

    // Multiple courses go side-by-side (same panel layout as compare)
    if (courses.length > 1) {
        return (
            <CardShell accent>
                <CardHeader eyebrow="Grade Distributions" title={courses.map(c => c.code).join(" & ")} />
                <div style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 1,
                    background: "rgba(255,255,255,.05)",
                }}>
                    {courses.map(c => <CoursePanelBlock key={c.code} course={c} />)}
                </div>
            </CardShell>
        );
    }

    // Single course — full-width, no panel boxing
    const course = courses[0];
    return (
        <CardShell accent>
            <CardHeader eyebrow="Grade Distribution" title={course.code} />
            <div style={{ padding: "18px 20px 22px" }}>
                {course.data?.total_grades && (
                    <GradeChart grades={course.data.total_grades} />
                )}
                {course.data?.srt_vals && (
                    <div style={{ marginTop: 24, borderTop: "1px solid rgba(255,255,255,.06)", paddingTop: 22 }}>
                        <SRTRatings srtVals={course.data.srt_vals} />
                    </div>
                )}
            </div>
        </CardShell>
    );
}

// ─── Schedule card ──────────────────────────────────────────────────────────────

function ScheduleContent({ item }) {
    const courses = Array.isArray(item.courses) ? item.courses : [];
    return (
        <div>
            {courses.map((course, i) => (
                <SectionsCard key={course.code || i} course={course} />
            ))}
        </div>
    );
}

// ─── dispatcher ────────────────────────────────────────────────────────────────

export default function RichContent({ content = [] }) {
    if (!content.length) return null;
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 6 }}>
            {content.map((item, index) => {
                if (item.type === "research")     return <ResearchCard      key={index} item={item} />;
                if (item.type === "grades")       return <GradesCard        key={index} item={item} />;
                if (item.type === "compare")      return <CourseCompareCard key={index} item={item} />;
                if (item.type === "prof_compare") return <ProfCompareCard   key={index} item={item} />;
                if (item.type === "schedule")     return <ScheduleContent   key={index} item={item} />;
                return null;
            })}
        </div>
    );
}
