import React from "react";

export default function FilterPills({ label, value, onChange, options, testid }) {
  return (
    <div className="flex items-center gap-1 border border-border rounded-md p-0.5 bg-card/30" data-testid={testid}>
      <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground px-2">{label}</span>
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`px-2 h-7 text-xs rounded transition-colors ${
            value === o.value ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground"
          }`}
          data-testid={`${testid}-${o.value || "all"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
