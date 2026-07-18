import React, { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  BookOpen,
  FileQuestion,
  FolderArchive,
  History,
  ListVideo,
  Loader2,
  PlaySquare,
  Search,
} from "lucide-react";

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import { useGlobalSearch } from "@/features/search/hooks/useSearch";
import { cn } from "@/lib/utils";

const SEARCH_EVENT = "gateprep:open-search";

const TYPE_META = {
  subject: { icon: BookOpen, label: "Subject" },
  topic: { icon: BookOpen, label: "Topic" },
  question: { icon: FileQuestion, label: "Question" },
  pyq: { icon: History, label: "PYQ" },
  resource: { icon: FolderArchive, label: "Resource" },
  playlist: { icon: ListVideo, label: "Playlist" },
  video: { icon: PlaySquare, label: "Video" },
};

const isEditableTarget = (target) => {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  return (
    tag === "input" ||
    tag === "textarea" ||
    tag === "select" ||
    target.isContentEditable
  );
};

const isStudySurface = (pathname) =>
  document.body.dataset.studySurface === "true" ||
  /^\/playlists\/[^/]+/.test(pathname);

function useDebouncedValue(value, delay = 180) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timeout);
  }, [value, delay]);
  return debounced;
}

export function openGlobalSearch() {
  window.dispatchEvent(new Event(SEARCH_EVENT));
}

export default function GlobalSearch() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const inputRef = useRef(null);
  const resultRefs = useRef([]);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const debouncedQuery = useDebouncedValue(query);
  const enabled = Boolean(user && open);
  const { data: results = [], isFetching } = useGlobalSearch(debouncedQuery, enabled);

  const trimmed = query.trim();
  const showHint = trimmed.length < 2;
  const visibleResults = useMemo(() => results || [], [results]);

  useEffect(() => {
    if (!user) return;
    const openSearch = () => setOpen(true);
    const onKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        if (isEditableTarget(event.target) || isStudySurface(location.pathname)) {
          return;
        }
        event.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener(SEARCH_EVENT, openSearch);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener(SEARCH_EVENT, openSearch);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [location.pathname, user]);

  useEffect(() => {
    if (!open) return;
    setActiveIndex(0);
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }, [open, debouncedQuery]);

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!open) return;
    resultRefs.current[activeIndex]?.scrollIntoView({
      block: "nearest",
      inline: "nearest",
    });
  }, [activeIndex, open]);

  const close = () => {
    setOpen(false);
    setQuery("");
    setActiveIndex(0);
  };

  const choose = (result) => {
    if (!result?.url) return;
    close();
    navigate(result.url);
  };

  const onInputKeyDown = (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (visibleResults.length === 0) return;
      setActiveIndex((value) => Math.min(value + 1, visibleResults.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      if (visibleResults.length === 0) return;
      setActiveIndex((value) => Math.max(value - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(visibleResults[activeIndex]);
    }
  };

  if (!user) return null;

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? setOpen(true) : close())}>
      <DialogContent className="top-[18%] max-w-2xl translate-y-0 gap-0 overflow-hidden border-border bg-card p-0 shadow-2xl">
        <DialogTitle className="sr-only">Global search</DialogTitle>
        <div className="flex items-center gap-3 border-b border-border px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onInputKeyDown}
            placeholder="Search subjects, questions, PDFs, playlists..."
            className="h-9 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            data-testid="global-search-input"
          />
          {isFetching ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : null}
        </div>

        <div className="max-h-[430px] overflow-y-auto p-2">
          {showHint ? (
            <EmptyState title="Type at least 2 characters" text="Try a subject, topic, PDF name, playlist, or question keyword." />
          ) : visibleResults.length === 0 && !isFetching ? (
            <EmptyState title="No results found" text="Try a different keyword or check the exact spelling." />
          ) : (
            <div className="space-y-1">
              {visibleResults.map((result, index) => {
                const meta = TYPE_META[result.type] || { icon: Search, label: result.type };
                const Icon = meta.icon;
                const active = index === activeIndex;
                return (
                  <button
                    key={`${result.type}-${result.id}`}
                    ref={(node) => {
                      resultRefs.current[index] = node;
                    }}
                    type="button"
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => choose(result)}
                    className={cn(
                      "flex w-full items-start gap-3 rounded-lg px-3 py-3 text-left transition-colors",
                      active ? "bg-secondary text-foreground" : "hover:bg-secondary/60"
                    )}
                    data-testid={`global-search-result-${result.type}`}
                  >
                    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-background/60 text-muted-foreground">
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium">{result.title}</span>
                        <span className="shrink-0 rounded border border-border px-1.5 py-0.5 text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                          {result.badge || meta.label}
                        </span>
                      </span>
                      <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                        {result.subtitle || meta.label}
                      </span>
                      {result.excerpt && (
                        <span className="mt-1 block line-clamp-2 text-xs leading-relaxed text-muted-foreground/80">
                          {result.excerpt}
                        </span>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-border px-4 py-2 text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
          <span>Enter to open</span>
          <span>↑ ↓ to move</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}

const EmptyState = ({ title, text }) => (
  <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full border border-border bg-secondary/40">
      <Search className="h-4 w-4 text-muted-foreground" />
    </div>
    <div className="text-sm font-medium">{title}</div>
    <div className="mt-1 max-w-sm text-xs text-muted-foreground">{text}</div>
  </div>
);
