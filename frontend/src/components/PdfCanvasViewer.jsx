import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import {
  ChevronLeft,
  ChevronRight,
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
}) {
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageInput, setPageInput] = useState("1");
  const [scale, setScale] = useState(1.1);
  const [containerWidth, setContainerWidth] = useState(0);
  const [renderedHeights, setRenderedHeights] = useState({});
  const [fitWidth, setFitWidth] = useState(true);
  const [panelOpen, setPanelOpen] = useState(false);
  const [labelEditingPage, setLabelEditingPage] = useState(null);
  const [labelDraft, setLabelDraft] = useState("");
  const [notesDraft, setNotesDraft] = useState(notes || "");

  const wrapRef = useRef(null);
  const pageRefs = useRef({});
  const isScrollingProgrammatically = useRef(false);

  // Reset notes draft when parent-provided notes change (e.g. resource switch)
  useEffect(() => {
    setNotesDraft(notes || "");
  }, [notes]);

  // Track container width
  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect?.width;
      if (w) setContainerWidth(w);
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  const renderWidth = useMemo(() => {
    if (!containerWidth) return undefined;
    const base = Math.min(containerWidth - 48, 1100);
    return fitWidth ? base : base * (scale / 1.1);
  }, [containerWidth, fitWidth, scale]);

  const placeholderHeight = useMemo(() => {
    if (!renderWidth) return 1000;
    return Math.round(renderWidth * DEFAULT_ASPECT);
  }, [renderWidth]);

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
    if (!wrapRef.current || isScrollingProgrammatically.current) return;
    const container = wrapRef.current;
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
    if (bestPage !== currentPage) {
      setCurrentPage(bestPage);
      setPageInput(String(bestPage));
    }
  }, [currentPage, numPages]);

  useEffect(() => {
    const node = wrapRef.current;
    if (!node) return;
    const onScroll = () => updateCurrentPageFromScroll();
    node.addEventListener("scroll", onScroll, { passive: true });
    return () => node.removeEventListener("scroll", onScroll);
  }, [updateCurrentPageFromScroll]);

  const onLoad = ({ numPages: total }) => {
    setNumPages(total);
    setCurrentPage(1);
    setPageInput("1");
    setRenderedHeights({});
  };

  const goToPage = useCallback((n) => {
    const clamped = Math.max(1, Math.min(numPages || n, n));
    const el = pageRefs.current[clamped];
    if (el && wrapRef.current) {
      isScrollingProgrammatically.current = true;
      wrapRef.current.scrollTo({ top: el.offsetTop - 8, behavior: "smooth" });
      setCurrentPage(clamped);
      setPageInput(String(clamped));
      setTimeout(() => { isScrollingProgrammatically.current = false; }, 500);
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
    const h = Math.round(pageObj?.height || 0);
    if (!h) return;
    setRenderedHeights((prev) => (prev[pageNum] === h ? prev : { ...prev, [pageNum]: h }));
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

  // Show panel features only when the parent wired up a handler.
  const panelEnabled = !!(onTogglePage || onNotesChange || onUpdateLabel);

  return (
    <div className="w-full h-full flex bg-[#0a0a0a]">
      {/* MAIN PDF AREA ====================================================*/}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* TOOLBAR ------------------------------------------------------- */}
        <div
          className="sticky top-0 z-10 flex items-center justify-between gap-3 px-4 py-2.5 bg-[#161616]/95 backdrop-blur border-b border-white/10 shrink-0"
          data-testid="pdf-toolbar"
        >
          {/* Page navigation cluster */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              data-testid="pdf-prev-page"
              className="h-8 w-8 inline-flex items-center justify-center rounded-md text-neutral-300 hover:bg-white/5 hover:text-white disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
              title="Previous page (←)"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-1.5 px-1">
              <input
                type="text"
                inputMode="numeric"
                value={pageInput}
                onChange={(e) => setPageInput(e.target.value.replace(/[^0-9]/g, ""))}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); jumpToPageInput(); e.target.blur(); } }}
                onBlur={jumpToPageInput}
                className="w-12 h-7 px-1.5 text-center text-xs font-mono bg-[#0a0a0a] border border-white/10 rounded text-neutral-100 focus:border-white/30 focus:outline-none"
                data-testid="pdf-page-input"
                aria-label="Current page"
              />
              <span className="text-xs font-mono text-neutral-500">/</span>
              <span className="text-xs font-mono text-neutral-300 min-w-[2ch]">{numPages || "—"}</span>
            </div>

            <button
              type="button"
              onClick={() => goToPage(currentPage + 1)}
              disabled={!numPages || currentPage >= numPages}
              data-testid="pdf-next-page"
              className="h-8 w-8 inline-flex items-center justify-center rounded-md text-neutral-300 hover:bg-white/5 hover:text-white disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
              title="Next page (→)"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Zoom + panel controls cluster */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => { setFitWidth(false); setScale((s) => Math.max(0.5, +(s - 0.1).toFixed(2))); }}
              data-testid="pdf-zoom-out"
              className="h-8 w-8 inline-flex items-center justify-center rounded-md text-neutral-300 hover:bg-white/5 hover:text-white transition-colors"
              title="Zoom out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span
              className="text-xs font-mono text-neutral-300 w-12 text-center tabular-nums select-none"
              data-testid="pdf-zoom-level"
            >
              {Math.round(scale * 100)}%
            </span>
            <button
              type="button"
              onClick={() => { setFitWidth(false); setScale((s) => Math.min(3, +(s + 0.1).toFixed(2))); }}
              data-testid="pdf-zoom-in"
              className="h-8 w-8 inline-flex items-center justify-center rounded-md text-neutral-300 hover:bg-white/5 hover:text-white transition-colors"
              title="Zoom in"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <div className="mx-2 h-5 w-px bg-white/10" />
            <button
              type="button"
              onClick={() => { setFitWidth((v) => !v); if (!fitWidth) setScale(1.1); }}
              data-testid="pdf-fit-width"
              className={`h-8 px-2.5 inline-flex items-center justify-center rounded-md text-xs font-medium transition-colors ${
                fitWidth ? "bg-white/10 text-white" : "text-neutral-300 hover:bg-white/5 hover:text-white"
              }`}
              title={fitWidth ? "Disable fit-to-width" : "Fit to width"}
            >
              {fitWidth ? <Minimize className="w-3.5 h-3.5 mr-1" /> : <Maximize className="w-3.5 h-3.5 mr-1" />}
              Fit
            </button>

            {panelEnabled && (
              <>
                <div className="mx-2 h-5 w-px bg-white/10" />
                <button
                  type="button"
                  onClick={handleToggleCurrent}
                  data-testid="pdf-flag-current-page"
                  className={`h-8 px-2.5 inline-flex items-center justify-center rounded-md text-xs font-medium transition-colors ${
                    isCurrentFlagged
                      ? "bg-amber-400/15 text-amber-300 ring-1 ring-amber-400/30"
                      : "text-neutral-300 hover:bg-white/5 hover:text-white"
                  }`}
                  title={isCurrentFlagged ? "Unflag this page" : "Flag this page as important"}
                >
                  {isCurrentFlagged ? <Bookmark className="w-3.5 h-3.5 mr-1 fill-current" /> : <BookmarkPlus className="w-3.5 h-3.5 mr-1" />}
                  {isCurrentFlagged ? "Flagged" : "Flag"}
                </button>
                <button
                  type="button"
                  onClick={() => setPanelOpen((v) => !v)}
                  data-testid="pdf-toggle-panel"
                  className={`h-8 w-8 inline-flex items-center justify-center rounded-md transition-colors ${
                    panelOpen ? "bg-white/10 text-white" : "text-neutral-300 hover:bg-white/5 hover:text-white"
                  }`}
                  title={panelOpen ? "Hide notes panel" : "Show notes panel"}
                >
                  {panelOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
                </button>
              </>
            )}
          </div>
        </div>

        {/* SCROLL AREA -------------------------------------------------- */}
        <div
          ref={wrapRef}
          className="flex-1 overflow-y-auto overflow-x-hidden bg-[#0a0a0a] scroll-smooth"
          data-testid="pdf-scroll-area"
        >
          <Document
            file={blob}
            onLoadSuccess={onLoad}
            loading={
              <div className="text-neutral-400 flex items-center gap-2 justify-center pt-20">
                <Loader2 className="w-4 h-4 animate-spin" /> Rendering PDF…
              </div>
            }
            error={
              <div className="text-red-400 text-sm pt-20 text-center">Failed to render PDF.</div>
            }
          >
            {numPages > 0 && Array.from({ length: numPages }, (_, i) => i + 1).map((p) => {
              const inWindow = shouldRenderPage(p);
              const knownHeight = renderedHeights[p];
              const slotHeight = knownHeight || placeholderHeight;
              const flagged = pageLabelMap.has(p);
              return (
                <div
                  key={p}
                  ref={(el) => { pageRefs.current[p] = el; }}
                  data-page={p}
                  data-testid={`pdf-page-slot-${p}`}
                  className={`mx-auto my-3 bg-white shadow-[0_4px_30px_rgba(0,0,0,0.4)] relative ${flagged ? "ring-2 ring-amber-400/70" : ""}`}
                  style={{ width: renderWidth, minHeight: slotHeight }}
                >
                  {flagged && (
                    <div
                      className="absolute -top-2 -right-2 z-[2] inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-400 text-black shadow-md"
                      data-testid={`pdf-page-flag-badge-${p}`}
                      title={pageLabelMap.get(p) || `Page ${p} flagged`}
                    >
                      <Bookmark className="w-2.5 h-2.5 fill-current" />
                      {pageLabelMap.get(p) ? pageLabelMap.get(p) : `p${p}`}
                    </div>
                  )}
                  {inWindow ? (
                    <Page
                      pageNumber={p}
                      width={renderWidth}
                      renderTextLayer={true}
                      renderAnnotationLayer={false}
                      onRenderSuccess={onPageRenderSuccess(p)}
                      loading={
                        <div className="flex items-center justify-center" style={{ height: slotHeight }}>
                          <Loader2 className="w-4 h-4 animate-spin text-neutral-400" />
                        </div>
                      }
                    />
                  ) : (
                    <div
                      className="flex items-center justify-center text-neutral-300 text-xs font-mono select-none"
                      style={{ height: slotHeight }}
                    >
                      Page {p}
                    </div>
                  )}
                </div>
              );
            })}
          </Document>
        </div>
      </div>

      {/* RIGHT-SIDE PANEL ================================================*/}
      {panelEnabled && panelOpen && (
        <aside
          className="w-[320px] xl:w-[360px] shrink-0 border-l border-white/10 bg-[#0f0f0f] flex flex-col"
          data-testid="pdf-notes-panel"
        >
          {/* Bookmarks section */}
          <div className="border-b border-white/10 shrink-0">
            <div className="px-4 py-2.5 flex items-center justify-between">
              <div className="text-[10px] uppercase tracking-[0.18em] text-neutral-400 font-medium">
                Important pages
              </div>
              <div className="text-[10px] font-mono text-neutral-500" data-testid="pdf-important-count">
                {(importantPages || []).length}
              </div>
            </div>
            <div className="max-h-[40vh] overflow-y-auto px-2 pb-2" data-testid="pdf-important-list">
              {(importantPages || []).length === 0 ? (
                <div className="text-xs text-neutral-500 px-2 py-3">
                  Hit <span className="text-neutral-300">Flag</span> on the toolbar to bookmark the current page.
                </div>
              ) : (
                importantPages.map(({ page, label }) => (
                  <div
                    key={page}
                    className="group rounded-md hover:bg-white/5 px-2 py-2 flex items-start gap-2"
                    data-testid={`pdf-bookmark-row-${page}`}
                  >
                    <button
                      type="button"
                      onClick={() => goToPage(page)}
                      className="shrink-0 inline-flex items-center justify-center w-9 h-7 rounded text-[11px] font-mono bg-amber-400/15 text-amber-300 ring-1 ring-amber-400/30 hover:bg-amber-400/25"
                      data-testid={`pdf-bookmark-jump-${page}`}
                      title={`Jump to page ${page}`}
                    >
                      p{page}
                    </button>

                    {labelEditingPage === page ? (
                      <div className="flex-1 flex items-center gap-1">
                        <input
                          autoFocus
                          value={labelDraft}
                          onChange={(e) => setLabelDraft(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") { e.preventDefault(); commitLabel(); }
                            if (e.key === "Escape") { e.preventDefault(); cancelLabel(); }
                          }}
                          placeholder="Label (e.g. Heap proof)"
                          className="flex-1 h-7 px-2 text-xs bg-[#0a0a0a] border border-white/15 rounded text-neutral-100 focus:border-white/40 focus:outline-none"
                          data-testid={`pdf-bookmark-label-input-${page}`}
                          maxLength={200}
                        />
                        <button
                          type="button"
                          onClick={commitLabel}
                          className="h-7 w-7 inline-flex items-center justify-center rounded text-emerald-400 hover:bg-white/5"
                          data-testid={`pdf-bookmark-label-save-${page}`}
                          title="Save"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={cancelLabel}
                          className="h-7 w-7 inline-flex items-center justify-center rounded text-neutral-400 hover:bg-white/5"
                          title="Cancel"
                        >
                          <XIcon className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <>
                        <button
                          type="button"
                          onClick={() => startEditLabel(page, label)}
                          className="flex-1 text-left text-xs text-neutral-200 truncate hover:text-white"
                          data-testid={`pdf-bookmark-label-${page}`}
                          title={label || "Click to add a label"}
                        >
                          {label ? label : <span className="text-neutral-500 italic">add label…</span>}
                        </button>
                        <button
                          type="button"
                          onClick={() => startEditLabel(page, label)}
                          className="opacity-0 group-hover:opacity-100 h-7 w-7 inline-flex items-center justify-center rounded text-neutral-400 hover:bg-white/5 hover:text-white transition-opacity"
                          title="Edit label"
                          data-testid={`pdf-bookmark-edit-${page}`}
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => onTogglePage && onTogglePage(page)}
                          className="opacity-0 group-hover:opacity-100 h-7 w-7 inline-flex items-center justify-center rounded text-neutral-400 hover:bg-white/5 hover:text-red-400 transition-opacity"
                          title="Remove bookmark"
                          data-testid={`pdf-bookmark-remove-${page}`}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Notes section */}
          <div className="flex-1 min-h-0 flex flex-col">
            <div className="px-4 py-2.5 flex items-center justify-between">
              <div className="text-[10px] uppercase tracking-[0.18em] text-neutral-400 font-medium">
                Notes
              </div>
              <div className="text-[10px] font-mono text-neutral-500" data-testid="pdf-notes-status">
                {(notesDraft || "") === (notes || "") ? "saved" : "saving…"}
              </div>
            </div>
            <div className="flex-1 min-h-0 px-3 pb-3">
              <textarea
                value={notesDraft}
                onChange={(e) => setNotesDraft(e.target.value)}
                placeholder="Free-form notes for this PDF. Anything you type here is auto-saved."
                className="w-full h-full resize-none bg-[#0a0a0a] border border-white/10 rounded-md p-3 text-sm text-neutral-100 placeholder:text-neutral-600 focus:border-white/30 focus:outline-none leading-relaxed"
                data-testid="pdf-notes-textarea"
              />
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
