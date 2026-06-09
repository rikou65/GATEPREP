import React, { useState, useEffect, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2 } from "lucide-react";

// Use the bundled worker (works in Brave / Chrome / Firefox without CDN)
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

export default function PdfCanvasViewer({ blob }) {
  const [numPages, setNumPages] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.2);
  const [containerWidth, setContainerWidth] = useState(0);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect?.width;
      if (w) setContainerWidth(w);
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  const onLoad = ({ numPages }) => {
    setNumPages(numPages);
    setPageNumber(1);
  };

  if (!blob) return null;

  return (
    <div className="w-full h-full flex flex-col bg-neutral-900">
      <div className="px-4 py-2 border-b border-border bg-card/90 flex items-center justify-center gap-2 text-xs mono">
        <Button
          size="sm"
          variant="outline"
          onClick={() => setPageNumber((p) => Math.max(1, p - 1))}
          disabled={pageNumber <= 1}
          data-testid="pdf-prev-page"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </Button>
        <span className="px-2">
          Page <span className="text-foreground">{pageNumber}</span> / {numPages || "…"}
        </span>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setPageNumber((p) => Math.min(numPages || p, p + 1))}
          disabled={!numPages || pageNumber >= numPages}
          data-testid="pdf-next-page"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </Button>
        <div className="mx-3 h-4 w-px bg-border" />
        <Button
          size="sm"
          variant="outline"
          onClick={() => setScale((s) => Math.max(0.5, s - 0.2))}
          data-testid="pdf-zoom-out"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </Button>
        <span className="px-1 text-muted-foreground">{Math.round(scale * 100)}%</span>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setScale((s) => Math.min(3, s + 0.2))}
          data-testid="pdf-zoom-in"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </Button>
      </div>
      <div ref={wrapRef} className="flex-1 overflow-auto flex items-start justify-center p-4">
        <Document
          file={blob}
          onLoadSuccess={onLoad}
          loading={
            <div className="text-muted-foreground flex items-center gap-2 mt-12">
              <Loader2 className="w-4 h-4 animate-spin" /> Rendering PDF…
            </div>
          }
          error={
            <div className="text-red-400 text-sm mt-12">Failed to render PDF.</div>
          }
        >
          <Page
            pageNumber={pageNumber}
            scale={scale}
            width={containerWidth ? Math.min(containerWidth - 32, 1100) : undefined}
            renderTextLayer={true}
            renderAnnotationLayer={false}
          />
        </Document>
      </div>
    </div>
  );
}
