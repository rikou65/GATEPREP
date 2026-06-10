import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2, Maximize, Minimize } from "lucide-react";

// Use the bundled worker (works in Brave / Chrome / Firefox without CDN)
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

// Approximate page aspect ratio used for placeholder height before the real
// page measures itself. ~1.414 = A4 portrait.
const DEFAULT_ASPECT = 1.414;
// How many pages around the current viewport we actually render canvases for.
const RENDER_WINDOW = 2;

export default function PdfCanvasViewer({ blob }) {
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageInput, setPageInput] = useState("1");
  const [scale, setScale] = useState(1.1);
  const [containerWidth, setContainerWidth] = useState(0);
  const [renderedHeights, setRenderedHeights] = useState({}); // pageNum -> actual height
  const [fitWidth, setFitWidth] = useState(true);

  const wrapRef = useRef(null);
  const pageRefs = useRef({});
  const isScrollingProgrammatically = useRef(false);

  // -- Track container width for fit-to-width rendering -------------------
  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect?.width;
      if (w) setContainerWidth(w);
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  // Page width to render at. When fitWidth is on, scale follows container.
  const renderWidth = useMemo(() => {
    if (!containerWidth) return undefined;
    const base = Math.min(containerWidth - 48, 1100);
    return fitWidth ? base : base * (scale / 1.1);
  }, [containerWidth, fitWidth, scale]);

  // Estimated height for a page placeholder (used to keep scrollbar honest
  // before the real canvas measures itself).
  const placeholderHeight = useMemo(() => {
    if (!renderWidth) return 1000;
    return Math.round(renderWidth * DEFAULT_ASPECT);
  }, [renderWidth]);

  // -- Track which page is "current" via scroll position -------------------
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

  // -- Document load handler ----------------------------------------------
  const onLoad = ({ numPages: total }) => {
    setNumPages(total);
    setCurrentPage(1);
    setPageInput("1");
    setRenderedHeights({});
  };

  // -- Page navigation ----------------------------------------------------
  const goToPage = useCallback((n) => {
    const clamped = Math.max(1, Math.min(numPages || n, n));
    const el = pageRefs.current[clamped];
    if (el && wrapRef.current) {
      isScrollingProgrammatically.current = true;
      wrapRef.current.scrollTo({ top: el.offsetTop - 8, behavior: "smooth" });
      setCurrentPage(clamped);
      setPageInput(String(clamped));
      // Release the flag after the smooth scroll likely finished.
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

  // -- Keyboard shortcuts -------------------------------------------------
  useEffect(() => {
    const onKey = (e) => {
      if (e.target?.tagName === "INPUT") return;
      if (e.key === "ArrowRight" || e.key === "PageDown") { e.preventDefault(); goToPage(currentPage + 1); }
      if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); goToPage(currentPage - 1); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [currentPage, goToPage]);

  // -- Windowed rendering decision ----------------------------------------
  const shouldRenderPage = (p) =>
    p >= currentPage - RENDER_WINDOW && p <= currentPage + RENDER_WINDOW;

  // -- Track real page heights after render -------------------------------
  const onPageRenderSuccess = useCallback((pageNum) => (pageObj) => {
    const h = Math.round(pageObj?.height || 0);
    if (!h) return;
    setRenderedHeights((prev) => (prev[pageNum] === h ? prev : { ...prev, [pageNum]: h }));
  }, []);

  if (!blob) return null;

  return (
    <div className="w-full h-full flex flex-col bg-[#0a0a0a]">
      {/* TOOLBAR ----------------------------------------------------------*/}
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

        {/* Zoom cluster */}
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
        </div>
      </div>

      {/* SCROLL AREA — continuous, all pages stacked ----------------------*/}
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
            return (
              <div
                key={p}
                ref={(el) => { pageRefs.current[p] = el; }}
                data-page={p}
                data-testid={`pdf-page-slot-${p}`}
                className="mx-auto my-3 bg-white shadow-[0_4px_30px_rgba(0,0,0,0.4)] relative"
                style={{ width: renderWidth, minHeight: slotHeight }}
              >
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
  );
}
