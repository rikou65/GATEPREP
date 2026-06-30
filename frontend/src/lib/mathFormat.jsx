import React from "react";

/**
 * Process a raw math/text string for subscripts, superscripts, bars, fracs.
 * Called on content inside/outside $...$ delimiters.
 */
const processMathContent = (text) => {
  if (!text) return [text];

  // Regex handles in priority order:
  // 1. \bar{...}  2. \overline{...}  3. \text{...}
  // 4. \frac{num}{den}  5. _{...}  6. ^{...}  7. _x  8. ^x
  const regex =
    /\\bar\{([^}]+)\}|\\overline\{([^}]+)\}|\\text\{([^}]+)\}|\\frac\{([^}]+)\}\{([^}]+)\}|_\{([^}]+)\}|\^\{([^}]+)\}|_([A-Za-z0-9]+)|\^([A-Za-z0-9]+)/g;

  const parts = [];
  let lastIdx = 0;
  let k = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push(text.slice(lastIdx, match.index));
    }

    if (match[1] !== undefined) {
      // \bar{X}
      parts.push(
        <span key={k++} style={{ textDecoration: "overline" }}>
          {match[1]}
        </span>
      );
    } else if (match[2] !== undefined) {
      // \overline{X}
      parts.push(
        <span key={k++} style={{ textDecoration: "overline" }}>
          {match[2]}
        </span>
      );
    } else if (match[3] !== undefined) {
      // \text{...} → plain text
      parts.push(match[3]);
    } else if (match[4] !== undefined && match[5] !== undefined) {
      // \frac{num}{den}
      parts.push(
        <span key={k++} className="inline-flex items-center gap-0.5">
          <span>{match[4]}</span>
          <span className="text-muted-foreground">/</span>
          <span>{match[5]}</span>
        </span>
      );
    } else if (match[6] !== undefined) {
      // _{text}
      parts.push(<sub key={k++}>{match[6]}</sub>);
    } else if (match[7] !== undefined) {
      // ^{text}
      parts.push(<sup key={k++}>{match[7]}</sup>);
    } else if (match[8] !== undefined) {
      // _x (single or multi char, no braces)
      parts.push(<sub key={k++}>{match[8]}</sub>);
    } else if (match[9] !== undefined) {
      // ^x
      parts.push(<sup key={k++}>{match[9]}</sup>);
    }

    lastIdx = regex.lastIndex;
  }

  if (lastIdx < text.length) {
    parts.push(text.slice(lastIdx));
  }

  return parts.length === 0 ? [text] : parts;
};

/**
 * Full math text formatter.
 * Handles: symbol replacements, $inline$, $$display$$, ![image](), bars, sub/superscripts.
 */
export const formatMathText = (rawText) => {
  if (!rawText) return "";

  // ── 1. String-level symbol replacements ──────────────────────────────────
  let text = rawText
    .replaceAll("\\Sigma", "Σ")
    .replaceAll("\\sum", "Σ")
    .replaceAll("\\sigma", "σ")
    .replaceAll("\\Pi", "Π")
    .replaceAll("\\prod", "Π")
    .replaceAll("\\oplus", "⊕")
    .replaceAll("\\odot", "⊙")
    .replaceAll("\\otimes", "⊗")
    .replaceAll("\\cdot", "·")
    .replaceAll("\\times", "×")
    .replaceAll("\\div", "÷")
    .replaceAll("\\sqrt", "√")
    .replaceAll("\\leq", "≤")
    .replaceAll("\\le", "≤")
    .replaceAll("\\geq", "≥")
    .replaceAll("\\ge", "≥")
    .replaceAll("\\neq", "≠")
    .replaceAll("\\ne", "≠")
    .replaceAll("\\approx", "≈")
    .replaceAll("\\equiv", "≡")
    .replaceAll("\\notin", "∉")
    .replaceAll("\\in", "∈")
    .replaceAll("\\subset", "⊂")
    .replaceAll("\\subseteq", "⊆")
    .replaceAll("\\cap", "∩")
    .replaceAll("\\cup", "∪")
    .replaceAll("\\land", "∧")
    .replaceAll("\\lor", "∨")
    .replaceAll("\\lnot", "¬")
    .replaceAll("\\neg", "¬")
    .replaceAll("\\implies", "⇒")
    .replaceAll("\\Rightarrow", "⇒")
    .replaceAll("\\iff", "⇔")
    .replaceAll("\\Leftrightarrow", "⇔")
    .replaceAll("\\rightarrow", "→")
    .replaceAll("\\leftarrow", "←")
    .replaceAll("\\leftrightarrow", "↔")
    .replaceAll("\\pm", "±")
    .replaceAll("\\mp", "∓")
    .replaceAll("\\infty", "∞")
    .replaceAll("\\alpha", "α")
    .replaceAll("\\beta", "β")
    .replaceAll("\\gamma", "γ")
    .replaceAll("\\delta", "δ")
    .replaceAll("\\epsilon", "ε")
    .replaceAll("\\lambda", "λ")
    .replaceAll("\\mu", "μ")
    .replaceAll("\\pi", "π")
    .replaceAll("\\rho", "ρ")
    .replaceAll("\\theta", "θ")
    .replaceAll("\\omega", "ω")
    .replaceAll("\\hline", "")
    .replaceAll("\\ldots", "…")
    .replaceAll("\\dots", "…")
    .replaceAll("\\cdots", "…");

  // ── 2. Segment-by-segment parsing ────────────────────────────────────────
  const parts = [];
  let i = 0;
  let keyCounter = 0;
  const k = () => `mf-${keyCounter++}`;

  while (i < text.length) {
    // ── Image markdown: ![alt](src)
    if (text[i] === "!" && text[i + 1] === "[") {
      const altEnd = text.indexOf("]", i + 2);
      if (altEnd !== -1 && text[altEnd + 1] === "(") {
        const srcEnd = text.indexOf(")", altEnd + 2);
        if (srcEnd !== -1) {
          const alt = text.slice(i + 2, altEnd) || "Figure";
          parts.push(
            <span
              key={k()}
              className="inline-flex items-center gap-1.5 px-2 py-0.5 my-0.5 rounded border border-border bg-secondary/50 text-muted-foreground text-xs italic"
            >
              <span>📐</span>
              <span>[{alt}]</span>
            </span>
          );
          i = srcEnd + 1;
          continue;
        }
      }
    }

    // ── Display math: $$...$$
    if (text[i] === "$" && text[i + 1] === "$") {
      const end = text.indexOf("$$", i + 2);
      if (end !== -1) {
        const inner = text.slice(i + 2, end);
        parts.push(
          <span key={k()} className="block text-center my-2 font-mono text-sm">
            {processMathContent(inner)}
          </span>
        );
        i = end + 2;
        continue;
      }
    }

    // ── Inline math: $...$
    if (text[i] === "$") {
      const end = text.indexOf("$", i + 1);
      if (end !== -1) {
        const inner = text.slice(i + 1, end);
        parts.push(
          <span key={k()} className="font-mono">
            {processMathContent(inner)}
          </span>
        );
        i = end + 1;
        continue;
      }
    }

    // ── Collect plain text until next special marker
    let j = i + 1;
    while (j < text.length) {
      if (text[j] === "$") break;
      if (text[j] === "!" && text[j + 1] === "[") break;
      j++;
    }

    const segment = text.slice(i, j);
    const processed = processMathContent(segment);
    parts.push(<React.Fragment key={k()}>{processed}</React.Fragment>);
    i = j;
  }

  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0];
  return parts;
};

/**
 * Renders markdown-style content with embedded tables as structured HTML.
 * Applies formatMathText to all text and table cells.
 */
export const renderContentWithTables = (text) => {
  if (!text) return "";

  const lines = text.split("\n");
  const elements = [];
  let currentTable = null;
  let textBuffer = [];
  let elemKey = 0;
  const k = () => `rct-${elemKey++}`;

  const flushTextBuffer = () => {
    if (textBuffer.length === 0) return;
    const joined = textBuffer.join("\n");
    elements.push(
      <div key={k()} className="whitespace-pre-wrap leading-relaxed">
        {formatMathText(joined)}
      </div>
    );
    textBuffer = [];
  };

  const flushTable = () => {
    if (!currentTable) return;
    elements.push(
      <div key={k()} className="overflow-x-auto my-3 max-w-full">
        <table className="min-w-[200px] border-collapse border border-border text-xs font-mono">
          <thead>
            <tr className="bg-secondary">
              {currentTable.headers.map((h, idx) => (
                <th
                  key={idx}
                  className="border border-border px-3 py-1.5 text-center font-bold"
                >
                  {formatMathText(h)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {currentTable.rows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-secondary/30 transition-colors">
                {row.map((cell, cIdx) => (
                  <td
                    key={cIdx}
                    className="border border-border px-3 py-1.5 text-center"
                  >
                    {formatMathText(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    currentTable = null;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (line.startsWith("|") && line.endsWith("|")) {
      flushTextBuffer();
      const cells = line
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim());
      const isDivider = cells.every((c) => /^:?-+:?$/.test(c) || c === "");
      if (!currentTable) {
        currentTable = { headers: cells, rows: [] };
      } else if (!isDivider) {
        currentTable.rows.push(cells);
      }
    } else {
      flushTable();
      textBuffer.push(lines[i]);
    }
  }

  flushTable();
  flushTextBuffer();

  return <div className="space-y-2">{elements}</div>;
};

/**
 * Returns a compact preview string/elements (tables → "[Table]", images → "[Figure]").
 */
export const getPreviewText = (text) => {
  if (!text) return "";
  const lines = text.split("\n");
  const cleaned = lines.map((line) => {
    if (line.trim().startsWith("|")) return "[Table]";
    if (line.trim().startsWith("![")) return "[Figure]";
    return line;
  });

  const filtered = [];
  let lastSpecial = false;
  for (const line of cleaned) {
    if (line === "[Table]" || line === "[Figure]") {
      if (!lastSpecial) {
        filtered.push(line);
        lastSpecial = true;
      }
    } else {
      filtered.push(line);
      lastSpecial = false;
    }
  }
  return formatMathText(filtered.join(" "));
};
