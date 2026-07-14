import React from "react";

export default function QueryError({ message = "Failed to load data.", onRetry }) {
  return (
    <div
      className="border border-dashed border-border rounded-lg p-8 text-center flex flex-col items-center gap-3"
      data-testid="query-error"
      role="alert"
    >
      <div className="text-sm text-foreground/80">{message}</div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="text-xs mono text-muted-foreground hover:text-foreground border border-border rounded-md px-3 py-1.5 transition-colors"
        >
          Try again
        </button>
      )}
    </div>
  );
}