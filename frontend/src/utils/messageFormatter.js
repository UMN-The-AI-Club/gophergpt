export function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function processInline(text) {
    const LINKS = [];
    let t = text.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, (_, label, url) => {
        const i = LINKS.length;
        LINKS.push({ label, url });
        return `\x00LINK${i}\x00`;
    });

    const BOLDS = [];
    t = t.replace(/\*\*(.*?)\*\*/g, (_, inner) => {
        const i = BOLDS.length;
        BOLDS.push(inner);
        return `\x00BOLD${i}\x00`;
    });

    t = escapeHtml(t);

    t = t.replace(/\x00BOLD(\d+)\x00/g, (_, i) =>
        `<strong>${escapeHtml(BOLDS[i])}</strong>`
    );

    t = t.replace(/\x00LINK(\d+)\x00/g, (_, i) => {
        const { label, url } = LINKS[i];
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
    });

    t = t.replace(/(?<!href=")(?<!">)(https?:\/\/[^\s<>"]+)/g, (url) => {
        const m = url.match(/^(.*?)([)\].,;:!?]*)$/);
        const clean = m ? m[1] : url;
        const trail = m ? m[2] : "";
        return `<a href="${clean}" target="_blank" rel="noopener noreferrer">${clean}</a>${trail}`;
    });

    return t;
}

function normalizeLine(line) {
    const openCount = (line.match(/\*\*/g) || []).length;
    if (openCount % 2 !== 0 && line.startsWith("**") && openCount === 1) {
        line = line + "**";
    }
    return line;
}

// Detect line types
function classify(raw) {
    const line = normalizeLine(raw);
    const trimmed = line.trim();

    if (!trimmed) return { type: "blank", raw: line };

    const hMatch = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (hMatch) return { type: "heading", level: hMatch[1].length, text: hMatch[2], raw: line };

    const olMatch = trimmed.match(/^(\d+)[\.\)]\s+(.+)$/);
    if (olMatch) return { type: "ol", num: parseInt(olMatch[1]), text: olMatch[2], indent: raw.match(/^(\s*)/)[1].length, raw: line };

    const ulMatch = trimmed.match(/^[-*\u2022]\s+(.+)$/);
    if (ulMatch) {
        const content = ulMatch[1];
        // Bold-only bullet with no trailing text → sub-section header inside a list
        const isBoldHeader = /^\*\*(.+?)\*\*:?\s*$/.test(content);
        if (isBoldHeader) return { type: "ul-header", text: content.replace(/^\*\*(.+?)\*\*:?\s*$/, "$1"), indent: raw.match(/^(\s*)/)[1].length, raw: line };
        return { type: "ul", text: content, indent: raw.match(/^(\s*)/)[1].length, raw: line };
    }

    const boldOnly = trimmed.match(/^\*\*(.+?)\*\*:?\s*$/);
    if (boldOnly) return { type: "section", text: boldOnly[1], raw: line };

    return { type: "p", text: trimmed, raw: line };
}

export function formatBotMessage(raw) {
    try {
        return _formatBotMessage(raw);
    } catch (e) {
        // A formatting bug must never blank the whole app. Degrade to safe,
        // escaped plain text (newlines preserved) instead of crashing render.
        return String(raw)
            .split(/\r?\n/)
            .map(line => `<p class="msg-p">${escapeHtml(line)}</p>`)
            .join("");
    }
}

function _formatBotMessage(raw) {
    const rawLines = String(raw).split(/\r?\n/);
    const tokens = rawLines.map(l => classify(l));

    const parts = [];
    let i = 0;

    while (i < tokens.length) {
        const tok = tokens[i];

        if (tok.type === "blank") {
            parts.push('<div class="msg-gap"></div>');
            i++;
            continue;
        }

        if (tok.type === "heading") {
            const cls = tok.level === 1 ? "msg-h1" : tok.level === 2 ? "msg-h2" : "msg-h3";
            parts.push(`<div class="${cls}">${processInline(tok.text)}</div>`);
            i++;
            continue;
        }

        if (tok.type === "section") {
            parts.push(`<div class="msg-section">${escapeHtml(tok.text)}</div>`);
            i++;
            continue;
        }

        // Ordered list — collect items and their sub-bullets
        if (tok.type === "ol") {
            parts.push('<ol class="msg-ol">');
            while (i < tokens.length && tokens[i].type === "ol") {
                const item = tokens[i];
                i++;

                // Check if next lines are sub-bullets (ul items with deeper indent, or just ul after ol item)
                const subBullets = [];
                while (
                    i < tokens.length &&
                    tokens[i].type === "ul" &&
                    (tokens[i].indent > item.indent || item.indent === 0)
                ) {
                    subBullets.push(tokens[i]);
                    i++;
                }

                if (subBullets.length > 0) {
                    const subHtml = subBullets
                        .map(b => {
                            const boldLabel = b.text.match(/^\*\*(.+?)\*\*[:\s]*(.*)/);
                            if (boldLabel) {
                                const label = escapeHtml(boldLabel[1]);
                                const rest = processInline(boldLabel[2]);
                                return `<li><strong>${label}</strong>${rest ? `: ${rest}` : ""}</li>`;
                            }
                            return `<li>${processInline(b.text)}</li>`;
                        })
                        .join("");
                    parts.push(`<li class="msg-ol-item">${processInline(item.text)}<ul class="msg-sub-ul">${subHtml}</ul></li>`);
                } else {
                    parts.push(`<li class="msg-ol-item">${processInline(item.text)}</li>`);
                }

                // Skip blank lines between ol items
                while (i < tokens.length && tokens[i].type === "blank") i++;
            }
            parts.push('</ol>');
            continue;
        }

        // Standalone unordered list
        if (tok.type === "ul" || tok.type === "ul-header") {
            // Collect all consecutive ul/ul-header tokens into a flat array first
            const allItems = [];
            while (i < tokens.length && (tokens[i].type === "ul" || tokens[i].type === "ul-header")) {
                allItems.push(tokens[i]);
                i++;
            }

            // Detect if this list uses bold-label grouping:
            // any item is a bold-label bullet like "**X**: text" or "**X**"
            const isBoldLabel = (t) => /^\*\*/.test(t.text);
            const hasBoldLabels = allItems.some(t => t.type === "ul-header" || (t.type === "ul" && isBoldLabel(t)));

            if (hasBoldLabels) {
                // Group: each bold-label or ul-header item is a parent; following plain items are children
                parts.push('<ul class="msg-ul">');
                let j = 0;
                while (j < allItems.length) {
                    const b = allItems[j];
                    const isHeader = b.type === "ul-header" || (b.type === "ul" && isBoldLabel(b));

                    if (isHeader) {
                        // Collect following plain (non-bold) items as sub-items
                        const subs = [];
                        j++;
                        while (j < allItems.length && allItems[j].type === "ul" && !isBoldLabel(allItems[j])) {
                            subs.push(allItems[j]);
                            j++;
                        }

                        let headerHtml;
                        if (b.type === "ul-header") {
                            headerHtml = `<strong class="msg-group-label">${escapeHtml(b.text)}</strong>`;
                        } else {
                            // b starts with "**" but may not have a closing "**" yet
                            // (e.g. mid-typewriter, or malformed markdown). Guard the
                            // match — a null here used to crash the whole app.
                            const bl = b.text.match(/^\*\*(.+?)\*\*[:\s]*(.*)/);
                            if (bl) {
                                const label = escapeHtml(bl[1]);
                                const rest = bl[2] ? processInline(bl[2]) : "";
                                headerHtml = `<strong>${label}</strong>${rest ? `: ${rest}` : ""}`;
                            } else {
                                headerHtml = processInline(b.text);
                            }
                        }

                        if (subs.length > 0) {
                            const subHtml = subs.map(s => `<li>${processInline(s.text)}</li>`).join("");
                            parts.push(`<li class="msg-ol-item">${headerHtml}<ul class="msg-sub-ul">${subHtml}</ul></li>`);
                        } else {
                            parts.push(`<li>${headerHtml}</li>`);
                        }
                    } else {
                        // Plain item with no bold parent — render as-is
                        parts.push(`<li>${processInline(b.text)}</li>`);
                        j++;
                    }
                }
                parts.push('</ul>');
            } else {
                // Simple flat list — no grouping needed
                parts.push('<ul class="msg-ul">');
                for (const b of allItems) {
                    parts.push(`<li>${processInline(b.text)}</li>`);
                }
                parts.push('</ul>');
            }
            continue;
        }

        if (tok.type === "p") {
            parts.push(`<p class="msg-p">${processInline(tok.text)}</p>`);
            i++;
            continue;
        }

        i++;
    }

    return parts.join("");
}
