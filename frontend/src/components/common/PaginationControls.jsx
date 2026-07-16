import { Button } from "@/components/ui/button";

export default function PaginationControls({ page, pageSize, total, visibleCount, onPageChange }) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : page * pageSize + 1;
  const end = Math.min(total, page * pageSize + visibleCount);

  return (
    <div className="flex items-center justify-between gap-3 flex-wrap border border-border rounded-lg px-4 py-3 bg-card/20">
      <div className="text-xs mono text-muted-foreground">
        Showing {start}-{end} of {total}
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page === 0}
          onClick={() => onPageChange(page - 1)}
        >
          Previous page
        </Button>
        <span className="text-xs mono text-muted-foreground px-2">
          Page {page + 1} of {pageCount}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= pageCount - 1}
          onClick={() => onPageChange(page + 1)}
        >
          Next page
        </Button>
      </div>
    </div>
  );
}
