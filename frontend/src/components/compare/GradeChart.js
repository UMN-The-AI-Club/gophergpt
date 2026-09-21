import React from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from "recharts";

const GRADE_ORDER = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F"];

const gradeColor = (grade) => {
    if (["A", "A-", "B+"].includes(grade)) return "#FFCC33";
    if (["B", "B-"].includes(grade))        return "#d4a900";
    if (["C+", "C"].includes(grade))        return "#b05030";
    if (["C-", "D+"].includes(grade))       return "#922010";
    return "#7A0019";
};

const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
        <div style={{
            background: "#252122", border: "1px solid rgba(255,255,255,.12)",
            borderRadius: 8, padding: "8px 12px", fontSize: 13,
            boxShadow: "0 8px 24px rgba(0,0,0,.5)",
        }}>
            <p style={{ fontWeight: 700, color: "#FFCC33", marginBottom: 2 }}>{label}</p>
            <p style={{ color: "#ddd6d8" }}>{payload[0].value.toLocaleString()} students</p>
        </div>
    );
};

const GradeChart = ({ grades, title = "Grade Distribution" }) => {
    if (!grades) return null;

    const chartData = GRADE_ORDER
        .filter(g => grades[g] !== undefined)
        .map(g => ({ grade: g, count: grades[g] }));

    const total = chartData.reduce((s, d) => s + d.count, 0);
    const aRate = chartData.filter(d => ["A", "A-"].includes(d.grade)).reduce((s, d) => s + d.count, 0);
    const aRatePct = total > 0 ? ((aRate / total) * 100).toFixed(0) : null;

    return (
        <div>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 14 }}>
                <h3 style={{ fontSize: 13.5, fontWeight: 700, color: "#fff", margin: 0 }}>{title}</h3>
                {aRatePct && (
                    <span style={{
                        fontSize: 11.5, fontWeight: 700, color: "#FFCC33",
                        background: "rgba(255,204,51,.1)", border: "1px solid rgba(255,204,51,.2)",
                        padding: "2px 8px", borderRadius: 999,
                    }}>
                        {aRatePct}% A/A−
                    </span>
                )}
            </div>

            <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                    <XAxis
                        dataKey="grade"
                        stroke="transparent"
                        tick={{ fill: "#9a9294", fontSize: 11, fontWeight: 600 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <YAxis
                        stroke="transparent"
                        tick={{ fill: "#6c6466", fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,.04)" }} />
                    <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                        {chartData.map((entry) => (
                            <Cell key={entry.grade} fill={gradeColor(entry.grade)} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>

            <div style={{
                display: "flex", gap: 18, marginTop: 10,
                paddingTop: 10, borderTop: "1px solid rgba(255,255,255,.06)",
                fontSize: 11.5, color: "#8f878a",
            }}>
                <span>W: <strong style={{ color: "#c9bfc1" }}>{grades["W"] ?? 0}</strong></span>
                <span>S: <strong style={{ color: "#c9bfc1" }}>{grades["S"] ?? 0}</strong></span>
                <span>N: <strong style={{ color: "#c9bfc1" }}>{grades["N"] ?? 0}</strong></span>
            </div>
        </div>
    );
};

export default GradeChart;
