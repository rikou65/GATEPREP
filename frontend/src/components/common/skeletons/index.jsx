import React from "react";
import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse rounded-md bg-white/[0.07]", className)}
      {...props}
    />
  );
}

export function PageHeaderSkeleton({ actions = false }) {
  return (
    <div className="flex items-end justify-between gap-4 flex-wrap">
      <div className="space-y-3 min-w-[240px]">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-4 w-80 max-w-full" />
      </div>
      {actions && <Skeleton className="h-10 w-40 rounded-lg" />}
    </div>
  );
}

export function FilterBarSkeleton({ count = 3 }) {
  return (
    <div className="flex flex-wrap gap-2">
      {Array.from({ length: count }).map((_, index) => (
        <Skeleton key={index} className="h-11 w-40 rounded-lg" />
      ))}
    </div>
  );
}

export function StatGridSkeleton({ count = 4, columns = "grid-cols-2 md:grid-cols-4" }) {
  return (
    <div className={cn("grid gap-3", columns)}>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="border border-border rounded-lg p-5 bg-card/30 space-y-4">
          <Skeleton className="h-4 w-4 rounded" />
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-8 w-20" />
        </div>
      ))}
    </div>
  );
}

export function CardGridSkeleton({ count = 6, columns = "grid-cols-1 md:grid-cols-2 xl:grid-cols-3" }) {
  return (
    <div className={cn("grid gap-3", columns)}>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="border border-border rounded-lg p-4 bg-card/30 space-y-4">
          <Skeleton className="h-4 w-3/4" />
          <div className="space-y-2">
            <Skeleton className="h-2 w-full rounded-full" />
            <Skeleton className="h-2 w-5/6 rounded-full" />
          </div>
          <Skeleton className="h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 4, columns = 5 }) {
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div
        className="grid gap-4 border-b border-border p-3"
        style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={index} className="h-3 w-16" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, row) => (
        <div
          key={row}
          className="grid gap-4 border-b border-border p-3 last:border-b-0"
          style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
        >
          {Array.from({ length: columns }).map((_, column) => (
            <Skeleton
              key={column}
              className={cn("h-4", column === 0 ? "w-4/5" : "w-2/3")}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton({ height = "h-[280px]" }) {
  return (
    <div className="border border-border rounded-lg p-5 space-y-4">
      <Skeleton className="h-3 w-44" />
      <div className={cn("relative rounded-lg border border-dashed border-border/70 p-5", height)}>
        <div className="absolute inset-x-5 bottom-5 flex items-end justify-between gap-3">
          {[44, 72, 36, 88, 54, 64, 42].map((heightPct, index) => (
            <Skeleton
              key={index}
              className="w-full rounded-t"
              style={{ height: `${heightPct}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function QuestionViewerSkeleton() {
  return (
    <div className="grid grid-cols-12 gap-6 items-start">
      <div className="col-span-12 xl:col-span-8">
        <div className="border border-border rounded-3xl p-6 bg-card/10 space-y-6">
          <div className="flex justify-between">
            <Skeleton className="h-4 w-36" />
            <div className="flex gap-2">
              <Skeleton className="h-8 w-20 rounded-lg" />
              <Skeleton className="h-8 w-16 rounded-lg" />
            </div>
          </div>
          <div className="space-y-3">
            <Skeleton className="h-5 w-11/12" />
            <Skeleton className="h-5 w-10/12" />
            <Skeleton className="h-5 w-3/4" />
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-12 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
      <div className="col-span-12 xl:col-span-4">
        <div className="border border-border rounded-3xl p-6 bg-card/25 space-y-5">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-40 w-full rounded-2xl" />
          <Skeleton className="h-20 w-full rounded-2xl" />
          <Skeleton className="h-24 w-full rounded-2xl" />
        </div>
      </div>
    </div>
  );
}

export function PlaylistDetailSkeleton() {
  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 5rem)" }}>
      <div className="shrink-0 space-y-3 mb-4">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-9 w-96 max-w-full" />
      </div>
      <div className="flex-1 min-h-0 grid grid-cols-12 gap-6 items-stretch">
        <div className="col-span-12 xl:col-span-7 space-y-4">
          <Skeleton className="aspect-video w-full rounded-3xl bg-white/[0.05]" />
          <Skeleton className="h-7 w-4/5" />
          <div className="flex gap-2">
            <Skeleton className="h-9 w-32 rounded-lg" />
            <Skeleton className="h-9 w-28 rounded-lg" />
          </div>
          <Skeleton className="h-2 w-full rounded-full" />
        </div>
        <div className="col-span-12 xl:col-span-5 flex flex-col gap-3">
          <div className="border border-border rounded-2xl p-4 space-y-3 flex-1">
            <Skeleton className="h-3 w-32" />
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-16 w-full rounded-xl" />
            ))}
          </div>
          <div className="border border-border rounded-2xl p-4 space-y-3 flex-1">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-40 w-full rounded-2xl" />
          </div>
        </div>
      </div>
    </div>
  );
}

export function StagingListSkeleton() {
  return (
    <div className="grid gap-4">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="border border-border rounded-lg p-5 bg-card/30 space-y-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-5 w-32" />
            <div className="flex gap-2">
              <Skeleton className="h-8 w-20 rounded-lg" />
              <Skeleton className="h-8 w-20 rounded-lg" />
            </div>
          </div>
          <Skeleton className="h-4 w-11/12" />
          <Skeleton className="h-4 w-10/12" />
          <div className="grid sm:grid-cols-2 gap-2">
            <Skeleton className="h-10 rounded-md" />
            <Skeleton className="h-10 rounded-md" />
          </div>
        </div>
      ))}
    </div>
  );
}
