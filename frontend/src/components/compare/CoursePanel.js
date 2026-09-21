import React, { useState } from "react";
import { Search } from "lucide-react";
import GradeChart from "./GradeChart";
import SRTRatings from "./SRTRatings";

const CoursePanel = () => {
    const [input, setInput]       = useState("");
    const [courseData, setCourse]  = useState(null);
    const [error, setError]        = useState("");
    const [focused, setFocused]    = useState(false);

    const fetchCourse = async () => {
        const q = input.trim();
        if (!q) return;
        setError(""); setCourse(null);
        try {
            const res  = await fetch(`${process.env.REACT_APP_API_BASE}/umn/course`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: q }),
            });
            const data = await res.json();
            if (!data.ok || !data.search?.success) {
                setError("Can't find that course — double-check the code and try again.");
                return;
            }
            setCourse(data);
        } catch {
            setError("Something went wrong. Please try again.");
        }
    };

    return (
        <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "34px 40px", gap: 22, overflowY: "auto" }}>

            {/* Search */}
            <div>
                <h2 style={{ fontSize: 22, fontWeight: 700, color: "#fff", letterSpacing: "-.02em", margin: "0 0 6px" }}>
                    Course Lookup
                </h2>
                <p style={{ fontSize: 13, color: "#8f878a", margin: "0 0 16px" }}>
                    Pull grade distributions and student ratings for any UMN course.
                </p>

                <div style={{
                    display: "flex", gap: 10,
                    background: "#252122", border: "1px solid rgba(255,255,255,.08)",
                    borderRadius: 14, padding: "14px 16px",
                }}>
                    <div style={{ position: "relative", flex: 1 }}>
                        <Search size={15} style={{
                            position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)",
                            color: focused ? "#FFCC33" : "#6c6466", pointerEvents: "none", transition: "color .15s",
                        }} />
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => { setInput(e.target.value); setError(""); }}
                            onKeyDown={(e) => e.key === "Enter" && fetchCourse()}
                            onFocus={() => setFocused(true)}
                            onBlur={() => setFocused(false)}
                            placeholder="Enter course code (e.g. CSCI 4041)"
                            style={{
                                width: "100%", boxSizing: "border-box",
                                background: "#2c2829",
                                border: `1.5px solid ${error ? "rgba(248,113,113,.5)" : focused ? "rgba(255,204,51,.6)" : "rgba(255,255,255,.1)"}`,
                                boxShadow: focused ? "0 0 0 3px rgba(255,204,51,.08)" : "none",
                                borderRadius: 10, padding: "10px 14px 10px 36px",
                                color: "#fff", fontSize: 13.5, outline: "none",
                                transition: "border-color .15s, box-shadow .15s",
                            }}
                        />
                    </div>
                    <button
                        onClick={fetchCourse}
                        style={{
                            background: "#FFCC33", color: "#1a0810",
                            border: "none", borderRadius: 10, padding: "0 22px",
                            fontWeight: 700, fontSize: 13.5, cursor: "pointer", flexShrink: 0,
                        }}
                    >
                        Look up
                    </button>
                </div>

                {error && (
                    <p style={{ fontSize: 13, color: "#f87171", marginTop: 8 }}>{error}</p>
                )}
            </div>

            {/* Results */}
            {courseData?.["class"]?.data && (
                <div style={{
                    background: "#252122", border: "1px solid rgba(255,255,255,.08)",
                    borderRadius: 14, overflow: "hidden",
                }}>
                    {/* Course header */}
                    <div style={{
                        padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,.06)",
                        backgroundImage: "radial-gradient(ellipse at 0% 0%, rgba(122,0,25,.18) 0%, transparent 60%)",
                    }}>
                        <div style={{ fontSize: 10.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".07em", color: "#8f878a", marginBottom: 4 }}>
                            Grade Distribution & Ratings
                        </div>
                        <div style={{ fontSize: 20, fontWeight: 700, color: "#fff", letterSpacing: "-.02em" }}>
                            {courseData.class?.course_num || input.toUpperCase()}
                        </div>
                        {courseData.class?.title && (
                            <div style={{ fontSize: 13, color: "#9a9294", marginTop: 3 }}>{courseData.class.title}</div>
                        )}
                    </div>

                    <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: 28 }}>
                        <GradeChart grades={courseData["class"].data.total_grades} />
                        <div style={{ borderTop: "1px solid rgba(255,255,255,.06)", paddingTop: 24 }}>
                            <SRTRatings srtVals={courseData["class"].data.srt_vals} />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CoursePanel;
