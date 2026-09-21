import React from "react";

const SRT_LABELS = {
    DEEP_UND:  "Deep Understanding",
    STIM_INT:  "Stimulating Interest",
    TECH_EFF:  "Technical Effectiveness",
    ACC_SUP:   "Accessible & Supportive",
    EFFORT:    "Effort Required",
    GRAD_STAND:"Grading Standards",
    RECC:      "Would Recommend",
};

// maroon (#7A0019) → gold (#FFCC33) on a 0–6 scale
const ratingColor = (value) => {
    if (value == null) return "#3a3336";
    const t = Math.min(value / 6, 1);
    const r = Math.round(122 + (255 - 122) * t);
    const g = Math.round(0   + (204 - 0)   * t);
    const b = Math.round(25  + (51  - 25)  * t);
    return `rgb(${r},${g},${b})`;
};

const SRTRatings = ({ srtVals, title = "Course Ratings" }) => {
    if (!srtVals) return null;
    const ratings = typeof srtVals === "string" ? JSON.parse(srtVals) : srtVals;

    return (
        <div>
            <h3 style={{ fontSize: 13.5, fontWeight: 700, color: "#fff", margin: "0 0 14px" }}>{title}</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {Object.entries(SRT_LABELS).map(([key, label]) => {
                    const raw   = ratings[key];
                    const value = raw != null ? Number(raw) : null;
                    const pct   = value != null ? `${((value / 6) * 100).toFixed(1)}%` : "0%";
                    const color = ratingColor(value);

                    return (
                        <div key={key}>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5, fontSize: 12.5 }}>
                                <span style={{ color: "#c9bfc1" }}>{label}</span>
                                <span style={{ fontWeight: 700, color }}>
                                    {value != null ? `${value.toFixed(2)} / 6` : "N/A"}
                                </span>
                            </div>
                            <div style={{
                                height: 5, width: "100%", borderRadius: 999,
                                background: "rgba(255,255,255,.07)", overflow: "hidden",
                            }}>
                                <div style={{
                                    height: "100%", borderRadius: 999,
                                    width: pct,
                                    background: `linear-gradient(90deg, #7A0019, ${color})`,
                                    transition: "width .5s",
                                }} />
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default SRTRatings;
