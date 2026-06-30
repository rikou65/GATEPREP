import React, { useState, useEffect, useLayoutEffect, useRef, useCallback, useMemo } from "react";
import { Document, Page, Outline, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ZoomIn,
  ZoomOut,
  Loader2,
  Maximize,
  Minimize,
  Bookmark,
  BookmarkPlus,
  PanelRightOpen,
  PanelRightClose,
  Pencil,
  Trash2,
  Check,
  X as XIcon,
  FileText,
  Search,
  Bell,
  List
} from "lucide-react";

// Use the bundled worker (works in Brave / Chrome / Firefox without CDN)
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

const DEFAULT_ASPECT = 1.414; // ~A4 portrait
const RENDER_WINDOW = 2;

/**
 * PDF viewer with optional right-side panel for notes + important pages.
 *
 * Props (all panel-related props are optional — viewer also works standalone):
 *   blob              : Blob | string
 *   notes             : string                                        (current notes content)
 *   importantPages    : Array<{page:number, label:string}>            (sorted by page asc)
 *   onNotesChange     : (text:string) => void                         (debounced auto-save responsibility is the parent's)
 *   onTogglePage      : (page:number) => void                         (flag/unflag a page)
 *   onUpdateLabel     : (page:number, label:string) => void           (set/update label for an already-flagged page)
 */
export default function PdfCanvasViewer({
  blob,
  notes = "",
  importantPages = [],
  onNotesChange,
  onTogglePage,
  onUpdateLabel,
  title = "Untitled PDF",
  onClose,
}) {
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageInput, setPageInput] = useState("1");
  const [scale, setScale] = useState(1.0);
  const [containerWidth, setContainerWidth] = useState(0);
  const [aspectRatios, setAspectRatios] = useState({});
  const [panelOpen, setPanelOpen] = useState(true);
  const [activeTab, setActiveTab] = useState("notes");
  const [hasOutline, setHasOutline] = useState(true);
  const [labelEditingPage, setLabelEditingPage] = useState(null);
  const [labelDraft, setLabelDraft] = useState("");
  const [notesDraft, setNotesDraft] = useState(notes || "");

  const scrollAreaRef = useRef(null);
  const observerRef = useRef(null);
  const pageRefs = useRef({});
  const isScrollingProgrammatically = useRef(false);
  const zoomAnchorRef = useRef({ page: 1, percent: 0 });

  // Callback ref to connect ResizeObserver when the element mounts
  const wrapRef = useCallback((node) => {
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
    if (node) {
      scrollAreaRef.current = node;
      const ro = new ResizeObserver((entries) => {
        const w = entries[0]?.contentRect?.width;
        if (w) {
          isScrollingProgrammatically.current = true;
          setContainerWidth(w);
          setTimeout(() => {
            isScrollingProgrammatically.current = false;
          }, 100);
        }
      });
      ro.observe(node);
      observerRef.current = ro;
    } else {
      scrollAreaRef.current = null;
    }
  }, []);

  // Reset notes draft when parent-provided notes change (e.g. resource switch)
  useEffect(() => {
    setNotesDraft(notes || "");
  }, [notes]);

  // Base render width — independent of zoom. Scale is applied via CSS transform.
  const renderWidth = useMemo(() => {
    if (!containerWidth) return undefined;
    return Math.min(containerWidth - 48, 1100);
  }, [containerWidth]);

  // Flagged-page lookup (O(1)) and label map
  const pageLabelMap = useMemo(() => {
    const m = new Map();
    (importantPages || []).forEach((it) => {
      if (it && typeof it.page === "number") m.set(it.page, it.label || "");
    });
    return m;
  }, [importantPages]);

  const isCurrentFlagged = pageLabelMap.has(currentPage);

  // Track current page from scroll position
  const updateCurrentPageFromScroll = useCallback(() => {
    if (!scrollAreaRef.current || isScrollingProgrammatically.current) return;
    const container = scrollAreaRef.current;
    const containerTop = container.scrollTop;
    const containerCenter = containerTop + container.clientHeight / 3;
    let bestPage = currentPage;
    let bestDistance = Infinity;
    for (let i = 1; i <= numPages; i++) {
      const el = pageRefs.current[i];
      if (!el) continue;
      const top = el.offsetTop;
      const bottom = top + el.offsetHeight;
      if (containerCenter >= top && containerCenter <= bottom) {
        bestPage = i;
        bestDistance = 0;
        break;
      }
      const dist = Math.min(Math.abs(top - containerCenter), Math.abs(bottom - containerCenter));
      if (dist < bestDistance) { bestDistance = dist; bestPage = i; }
    }

    // Save zoom anchor relative to the best page
    const bestEl = pageRefs.current[bestPage];
    if (bestEl && bestEl.offsetHeight > 0) {
      const pct = (containerTop - bestEl.offsetTop) / bestEl.offsetHeight;
      zoomAnchorRef.current = { page: bestPage, percent: pct };
    }

    if (bestPage !== currentPage) {
      setCurrentPage(bestPage);
      setPageInput(String(bestPage));
    }
  }, [currentPage, numPages]);

  useEffect(() => {
    const node = scrollAreaRef.current;
    if (!node) return;
    const onScroll = () => updateCurrentPageFromScroll();
    node.addEventListener("scroll", onScroll, { passive: true });
    return () => node.removeEventListener("scroll", onScroll);
  }, [numPages, updateCurrentPageFromScroll]);

  const onLoad = ({ numPages: total }) => {
    setNumPages(total);
    setCurrentPage(1);
    setPageInput("1");
    setAspectRatios({});
  };

  const goToPage = useCallback((n) => {
    const clamped = Math.max(1, Math.min(numPages || 1, n));
    const el = pageRefs.current[clamped];
    if (el && scrollAreaRef.current) {
      isScrollingProgrammatically.current = true;
      scrollAreaRef.current.scrollTop = el.offsetTop - 8;
      
      // Update anchor immediately for the destination page
      zoomAnchorRef.current = { page: clamped, percent: 0 };
      
      setCurrentPage(clamped);
      setPageInput(String(clamped));
      setTimeout(() => { isScrollingProgrammatically.current = false; }, 50);
    }
  }, [numPages]);

  const jumpToPageInput = () => {
    const n = parseInt(pageInput, 10);
    if (!isNaN(n) && n >= 1 && n <= (numPages || 1)) {
      goToPage(n);
    } else {
      setPageInput(String(currentPage));
    }
  };

  // Keep the scroll position anchored during zoom changes or container resizes
  const prevScaleRef = useRef(scale);
  const prevWidthRef = useRef(renderWidth);
  useLayoutEffect(() => {
    const scaleChanged = prevScaleRef.current !== scale;
    const widthChanged = prevWidthRef.current !== renderWidth
      && prevWidthRef.current !== undefined && renderWidth !== undefined;
    prevScaleRef.current = scale;
    prevWidthRef.current = renderWidth;

    if (!scaleChanged && !widthChanged) return;

    const container = scrollAreaRef.current;
    const anchor = zoomAnchorRef.current;
    const el = pageRefs.current[anchor?.page];
    if (container && el) {
      isScrollingProgrammatically.current = true;
      const targetScrollTop = el.offsetTop + (anchor.percent * el.offsetHeight);
      container.scrollTop = Math.max(0, targetScrollTop);
      const timer = setTimeout(() => {
        isScrollingProgrammatically.current = false;
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [scale, renderWidth]);

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e) => {
      const tag = e.target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "ArrowRight" || e.key === "PageDown") { e.preventDefault(); goToPage(currentPage + 1); }
      if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); goToPage(currentPage - 1); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [currentPage, goToPage]);

  const shouldRenderPage = (p) =>
    p >= currentPage - RENDER_WINDOW && p <= currentPage + RENDER_WINDOW;

  const onPageRenderSuccess = useCallback((pageNum) => (pageObj) => {
    const w = pageObj?.width || pageObj?.originalWidth;
    const h = pageObj?.height || pageObj?.originalHeight;
    if (!w || !h) return;
    const aspect = w / h;
    setAspectRatios((prev) => (prev[pageNum] === aspect ? prev : { ...prev, [pageNum]: aspect }));
  }, []);

  // Debounced auto-save for notes (fires 600ms after last keystroke)
  useEffect(() => {
    if (!onNotesChange) return;
    if ((notesDraft || "") === (notes || "")) return;
    const t = setTimeout(() => onNotesChange(notesDraft), 600);
    return () => clearTimeout(t);
  }, [notesDraft, notes, onNotesChange]);

  const handleToggleCurrent = () => {
    if (!onTogglePage || !numPages) return;
    onTogglePage(currentPage);
  };

  const startEditLabel = (page, currentLabel) => {
    setLabelEditingPage(page);
    setLabelDraft(currentLabel || "");
  };
  const commitLabel = () => {
    if (labelEditingPage != null && onUpdateLabel) {
      onUpdateLabel(labelEditingPage, labelDraft.trim());
    }
    setLabelEditingPage(null);
    setLabelDraft("");
  };
  const cancelLabel = () => {
    setLabelEditingPage(null);
    setLabelDraft("");
  };

  if (!blob) return null;

  const panelEnabled = !!(onTogglePage || onNotesChange || onUpdateLabel);

  const renderHeader = () => (
    <header className="h-14 bg-[#111115] border-b border-white/10 flex items-center justify-between px-6 shrink-0 z-20">
      {/* Left side */}
      <div className="flex items-center gap-4 min-w-0">
        <button
          onClick={onClose}
          className="h-9 px-4 inline-flex items-center justify-center rounded-lg border border-white/10 bg-[#1b1b22] hover:bg-[#25252f] text-xs font-semibold text-white transition-colors"
        >
          ← Back to Library
        </button>
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-4 h-4 text-neutral-400 shrink-0" />
          <span className="text-sm font-semibold text-white truncate max-w-[150px] sm:max-w-[250px]">
            {title}
          </span>
        </div>
      </div>

      {/* Center: Zoom and Page Navigation Controls */}
      <div className="flex items-center gap-3">
        {/* Zoom Controls */}
        <div className="flex items-center gap-2.5 bg-[#16161c] px-2.5 py-1.5 rounded-lg border border-white/5">
          <button
            type="button"
            onClick={() => {
              isScrollingProgrammatically.current = true;
              setScale((s) => Math.max(0.5, +(s - 0.1).toFixed(2)));
            }}
            data-testid="pdf-zoom-out"
            className="text-neutral-400 hover:text-white transition-colors"
            title="Zoom out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span
            className="text-xs font-mono text-neutral-200 w-10 text-center tabular-nums select-none"
            data-testid="pdf-zoom-level"
          >
            {Math.round(scale * 100)}%
          </span>
          <button
            type="button"
            onClick={() => {
              isScrollingProgrammatically.current = true;
              setScale((s) => Math.min(3, +(s + 0.1).toFixed(2)));
            }}
            data-testid="pdf-zoom-in"
            className="text-neutral-400 hover:text-white transition-colors"
            title="Zoom in"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Page Navigation Controls */}
        <div className="flex items-center gap-2 bg-[#16161c] px-3 py-1.5 rounded-lg border border-white/5">
          <div className="flex items-center gap-0.5">
            <button
              type="button"
              onClick={() => goToPage(1)}
              disabled={currentPage <= 1}
              className="h-6 w-6 inline-flex items-center justify-center rounded text-neutral-400 hover:bg-white/5 hover:text-white disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
              title="First page"
            >
              <ChevronsLeft className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              data-testid="pdf-prev-page"
              className="h-6 w-6 inline-flex items-center justify-center rounded text-neutral-400 hover:bg-white/5 hover:text-white disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
              title="Previous page (←)"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center gap-1 text-xs select-none">
            <input
              type="text"
              inputMode="numeric"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value.replace(/[^0-9]/g, ""))}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); jumpToPageInput(); e.target.blur(); } }}
              onBlur={jumpToPageInput}
              className="w-10 h-6 text-center text-xs font-mono bg-[#0c0c10] border border-white/10 rounded text-neutral-100 focus:border-white/30 focus:outline-none"
              data-testid="pdf-page-input"
              aria-label="Current page"
            />
            <span className="font-mono text-neutral-500">/</span>
            <span className="font-mono text-neutral-300 min-w-[2ch]">{numPages || "—"}</span>
          </div>

          <div className="flex items-center gap-0.5">
            <button
              type="button"
              onClick={() => goToPage(currentPage + 1)}
              disabled={!numPages || currentPage >= numPages}
              data-testid="pdf-next-page"
              className="h-6 w-6 inline-flex items-center justify-center rounded text-neutral-400 hover:bg-white/5 hover:text-white disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
              title="Next page (→)"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => goToPage(numPages)}
              disabled={!numPages || currentPage >= numPages}
              className="h-6 w-6 inline-flex items-center justify-center rounded text-neutral-400 hover:bg-white/5 hover:text-white disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
              title="Last page"
            >
              <ChevronsRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {panelEnabled && (
            <>
              <div className="w-px h-4 bg-white/10 mx-0.5" />
              <button
                type="button"
                onClick={handleToggleCurrent}
                data-testid="pdf-flag-current-page"
                className={`h-6 px-2 inline-flex items-center justify-center rounded text-[10px] font-semibold gap-1 transition-all ${
                  isCurrentFlagged
                    ? "bg-amber-400 text-black shadow-md hover:bg-amber-500"
                    : "bg-[#1b1b22] hover:bg-[#25252f] text-neutral-300 hover:text-white border border-white/10"
                }`}
                title={isCurrentFlagged ? "Unbookmark this page" : "Bookmark this page"}
              >
                <Bookmark className={`w-3 h-3 ${isCurrentFlagged ? "fill-current" : ""}`} />
                BOOKMARK
              </button>
            </>
          )}
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative hidden md:block">
          <Search className="w-3.5 h-3.5 text-neutral-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search..."
            className="w-48 h-9 pl-9 pr-3 bg-[#16161c] border border-white/10 rounded-lg text-xs text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-white/20"
          />
        </div>
      </div>
    </header>
  );

  const renderRightSidePanel = () => (
    <aside
      className="w-[320px] xl:w-[360px] shrink-0 border-l border-white/10 bg-[#0f1015] flex flex-col"
      data-testid="pdf-notes-panel"
    >
      {/* Tabs header */}
      <div className="flex border-b border-white/10 shrink-0">
        <button
          type="button"
          onClick={() => setActiveTab("notes")}
          className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-all ${
            activeTab === "notes"
              ? "border-white text-white bg-white/[0.03]"
              : "border-transparent text-neutral-400 hover:text-white hover:bg-white/[0.01]"
          }`}
        >
          <Pencil className="w-3.5 h-3.5" />
          Personal Notes
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("index")}
          className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-all ${
            activeTab === "index"
              ? "border-white text-white bg-white/[0.03]"
              : "border-transparent text-neutral-400 hover:text-white hover:bg-white/[0.01]"
          }`}
        >
          <List className="w-3.5 h-3.5" />
          Index
        </button>
      </div>

      {activeTab === "notes" ? (
        <div className="flex-1 min-h-0 flex flex-col">
          {/* Note editor header */}
          <div className="px-4 py-2.5 flex items-center justify-between border-b border-white/5 bg-[#14151c]/50">
            <div className="text-[10px] uppercase tracking-[0.12em] text-neutral-400 font-semibold">
              Editor &mdash; Auto-saving
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[9px] font-mono text-neutral-500 uppercase">
                {(notesDraft || "") === (notes || "") ? "Saved" : "Saving..."}
              </span>
            </div>
          </div>

          {/* Textarea container */}
          <div className="flex-1 min-h-0 p-3">
            <textarea
              value={notesDraft}
              onChange={(e) => setNotesDraft(e.target.value)}
              placeholder="Capture equations, proofs, key definitions, or formulas..."
              className="w-full h-full resize-none bg-[#090a0f] border border-white/10 rounded-xl p-4 text-sm text-neutral-200 placeholder:text-neutral-600 focus:border-white/20 focus:outline-none leading-relaxed"
              data-testid="pdf-notes-textarea"
            />
          </div>

          {/* Editor action bar */}
          <div className="px-4 py-2 flex items-center justify-between border-t border-white/5 bg-[#14151c]/50 shrink-0">
            <div className="flex items-center gap-1">
              <button className="h-7 w-7 text-xs font-bold text-neutral-400 hover:text-white hover:bg-white/5 rounded transition-colors" title="Bold">B</button>
              <button className="h-7 w-7 text-xs italic text-neutral-400 hover:text-white hover:bg-white/5 rounded transition-colors" title="Italic">I</button>
              <button className="h-7 w-7 text-xs font-mono text-neutral-400 hover:text-white hover:bg-white/5 rounded transition-colors" title="Code">&lt;&gt;</button>
            </div>
            <button className="text-[11px] text-neutral-400 hover:text-white transition-colors" title="Export current notes to markdown file">
              Export to Markdown
            </button>
          </div>

          {/* Bookmarks section */}
          <div className="border-t border-white/10 flex-1 min-h-0 flex flex-col">
            <div className="px-4 py-2.5 flex items-center justify-between bg-[#14151c]/30 border-b border-white/5">
              <div className="text-[10px] uppercase tracking-[0.12em] text-neutral-400 font-semibold">
                Bookmarked in this PDF
              </div>
              <div className="text-[10px] font-mono text-neutral-500" data-testid="pdf-important-count">
                {(importantPages || []).length}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-2 py-2" data-testid="pdf-important-list">
              {(importantPages || []).length === 0 ? (
                <div className="text-xs text-neutral-500 px-3 py-4 italic">
                  Click the Bookmark button in the page navigation bar to add a bookmark.
                </div>
              ) : (
                importantPages.map(({ page, label }) => (
                  <div
                    key={page}
                    className="group rounded-xl hover:bg-white/[0.03] p-2 flex items-start gap-3 border border-transparent hover:border-white/5 transition-all mb-1"
                    data-testid={`pdf-bookmark-row-${page}`}
                  >
                    {/* Page number button */}
                    <button
                      type="button"
                      onClick={() => goToPage(page)}
                      className="shrink-0 inline-flex items-center justify-center px-2.5 h-8 rounded-lg text-xs font-mono bg-amber-400/10 text-amber-400 border border-amber-400/20 hover:bg-amber-400/20 transition-colors"
                      data-testid={`pdf-bookmark-jump-${page}`}
                      title={`Jump to page ${page}`}
                    >
                      p{page}
                    </button>

                    {/* Label area */}
                    {labelEditingPage === page ? (
                      <div className="flex-1 flex items-center gap-1.5">
                        <input
                          autoFocus
                          value={labelDraft}
                          onChange={(e) => setLabelDraft(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") { e.preventDefault(); commitLabel(); }
                            if (e.key === "Escape") { e.preventDefault(); cancelLabel(); }
                          }}
                          placeholder="Label (e.g. Heap proof)"
                          className="flex-1 h-8 px-2 text-xs bg-[#090a0f] border border-white/20 rounded-lg text-neutral-100 focus:border-white/40 focus:outline-none"
                          data-testid={`pdf-bookmark-label-input-${page}`}
                          maxLength={200}
                        />
                        <button
                          type="button"
                          onClick={commitLabel}
                          className="h-8 w-8 inline-flex items-center justify-center rounded-lg text-emerald-400 hover:bg-white/5 transition-colors"
                          data-testid={`pdf-bookmark-label-save-${page}`}
                          title="Save"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={cancelLabel}
                          className="h-8 w-8 inline-flex items-center justify-center rounded-lg text-neutral-400 hover:bg-white/5 transition-colors"
                          title="Cancel"
                        >
                          <XIcon className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <>
                        <div className="flex-1 min-w-0">
                          <button
                            type="button"
                            onClick={() => goToPage(page)}
                            className="block text-left text-xs font-medium text-neutral-200 truncate hover:text-white w-full"
                            data-testid={`pdf-bookmark-label-${page}`}
                          >
                            {label ? label : <span className="text-neutral-500 italic">add label…</span>}
                          </button>
                          <span className="text-[9px] text-neutral-500 block mt-0.5 font-mono">
                            Modified 2 hours ago
                          </span>
                        </div>
                        <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            type="button"
                            onClick={() => startEditLabel(page, label)}
                            className="h-7 w-7 inline-flex items-center justify-center rounded-lg text-neutral-400 hover:bg-white/5 hover:text-white transition-colors"
                            title="Edit label"
                            data-testid={`pdf-bookmark-edit-${page}`}
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => onTogglePage && onTogglePage(page)}
                            className="h-7 w-7 inline-flex items-center justify-center rounded-lg text-neutral-400 hover:bg-white/5 hover:text-red-400 transition-colors"
                            title="Remove bookmark"
                            data-testid={`pdf-bookmark-remove-${page}`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto px-4 py-4 bg-[#0f1015]">
          {hasOutline ? (
            <Outline
              className="pdf-outline"
              onItemClick={({ pageNumber }) => goToPage(pageNumber)}
              onLoadSuccess={() => setHasOutline(true)}
              onLoadError={() => setHasOutline(false)}
            />
          ) : (
            <div className="text-xs text-neutral-500 italic">
              No index / document outline available for this resource.
            </div>
          )}
        </div>
      )}
    </aside>
  );

  return (
    <div className="w-full h-full flex flex-col bg-[#0a0a0a]">
      <Document
        file={blob}
        onLoadSuccess={onLoad}
        className="flex-1 flex flex-col min-h-0 w-full relative"
        loading={
          <div className="w-full h-full flex flex-col bg-[#0a0a0a]">
            {renderHeader()}
            <div className="flex-1 flex flex-col items-center justify-center gap-3 text-neutral-400">
              <Loader2 className="w-8 h-8 animate-spin" />
              <div className="text-xs font-mono">Streaming PDF...</div>
            </div>
          </div>
        }
        error={
          <div className="w-full h-full flex flex-col bg-[#0a0a0a]">
            {renderHeader()}
            <div className="flex-1 flex items-center justify-center text-red-400 text-sm font-mono">
              Failed to render PDF.
            </div>
          </div>
        }
      >
        <div className="w-full h-full flex flex-col bg-[#0a0a0a] select-none">
          {renderHeader()}
          <div className="flex-1 flex min-h-0 relative">
            <div className="flex-1 min-w-0 flex flex-col relative h-full">
              <div
                ref={wrapRef}
                className="flex-1 overflow-y-auto overflow-x-auto bg-[#0a0a0a] pb-4"
                data-testid="pdf-scroll-area"
              >
                {numPages > 0 &&
                  Array.from({ length: numPages }, (_, i) => i + 1).map((p) => {
                    const inWindow = shouldRenderPage(p);
                    const aspect = aspectRatios[p] || DEFAULT_ASPECT;
                    const baseSlotHeight = renderWidth ? Math.round(renderWidth / aspect) : 1000;
                    const scaledWidth = renderWidth ? Math.round(renderWidth * scale) : undefined;
                    const scaledHeight = Math.round(baseSlotHeight * scale);
                    const flagged = pageLabelMap.has(p);
                    return (
                      <div
                        key={p}
                        ref={(el) => {
                          pageRefs.current[p] = el;
                        }}
                        data-page={p}
                        data-testid={`pdf-page-slot-${p}`}
                        className={`mx-auto my-4 bg-transparent shadow-[0_8px_40px_rgba(0,0,0,0.6)] relative select-text ${
                          flagged ? "ring-2 ring-amber-400/70" : ""
                        }`}
                        style={{ width: scaledWidth, height: scaledHeight }}
                      >
                        {flagged && (
                          <div
                            className="absolute -top-2 -right-2 z-[2] inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-amber-400 text-black shadow-md"
                            data-testid={`pdf-page-flag-badge-${p}`}
                            title={pageLabelMap.get(p) || `Page ${p} flagged`}
                          >
                            <Bookmark className="w-2.5 h-2.5 fill-current" />
                            {pageLabelMap.get(p) ? pageLabelMap.get(p) : `p${p}`}
                          </div>
                        )}
                        {/* CSS transform wrapper — zoom is visual-only, no re-render */}
                        <div
                          style={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: renderWidth,
                            height: baseSlotHeight,
                            transform: `scale(${scale})`,
                            transformOrigin: 'top left',
                            overflow: 'hidden',
                          }}
                        >
                          {inWindow ? (
                            <Page
                              key={`${p}-${renderWidth}`}
                              pageNumber={p}
                              width={renderWidth}
                              renderTextLayer={true}
                              renderAnnotationLayer={true}
                              onRenderSuccess={onPageRenderSuccess(p)}
                              loading={
                                <div className="flex items-center justify-center" style={{ height: baseSlotHeight }}>
                                  <Loader2 className="w-4 h-4 animate-spin text-neutral-400" />
                                </div>
                              }
                            />
                          ) : (
                            <div
                              className="flex items-center justify-center text-neutral-400 text-xs font-mono select-none"
                              style={{ height: baseSlotHeight }}
                            >
                              Page {p}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>

            {renderRightSidePanel()}
          </div>
        </div>
      </Document>
    </div>
  );
}
