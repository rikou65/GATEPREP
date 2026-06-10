import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useSearchParams } from "react-router-dom";
import QuestionViewer from "@/components/QuestionViewer";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, CheckCircle2 } from "lucide-react";

export default function PYQs() {
  const [search] = useSearchParams();
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [filter, setFilter] = useState({
    subject_id: search.get("subject_id") || "",
    topic_id: search.get("topic_id") || "",
    year: "",
  });
  const [items, setItems] = useState([]);
  const [idx, setIdx] = useState(0);

  // Sync filter with URL params (so navigation from Topic → PYQs pre-filters)
  useEffect(() => {
    const s = search.get("subject_id") || "";
    const t = search.get("topic_id") || "";
    setFilter((f) => ({ ...f, subject_id: s, topic_id: t }));
  }, [search]);

  useEffect(() => { api.get("/subjects").then(r => setSubjects(r.data?.data || [])); }, []);
  useEffect(() => {
    if (!filter.subject_id) { setTopics([]); return; }
    api.get(`/subjects/${filter.subject_id}/topics`).then(r => setTopics(r.data?.data || []));
  }, [filter.subject_id]);
  useEffect(() => {
    const params = {};
    Object.entries(filter).forEach(([k, v]) => { if (v) params[k] = v; });
    api.get("/pyqs", { params }).then(r => { setItems(r.data?.data?.items || []); setIdx(0); });
  }, [filter]);

  const current = items[idx];
  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Previous Year Questions</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">PYQs</h1>
        <p className="text-sm text-muted-foreground mt-1">Tracked separately from Question Bank — never merged.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <select data-testid="pyq-filter-subject" value={filter.subject_id} onChange={(e) => setFilter(f => ({ ...f, subject_id: e.target.value, topic_id: "" }))}
          className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">All subjects</option>
          {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
        </select>
        <select value={filter.topic_id} onChange={(e) => setFilter(f => ({ ...f, topic_id: e.target.value }))}
          className="h-9 px-3 text-sm bg-transparent border border-border rounded-md" disabled={!filter.subject_id}>
          <option value="">All topics</option>
          {topics.map(t => <option key={t.topic_id} value={t.topic_id}>{t.name}</option>)}
        </select>
        <select value={filter.year} onChange={(e) => setFilter(f => ({ ...f, year: e.target.value }))}
          className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">All years</option>
          {[2024, 2023, 2022, 2021, 2020, 2019, 2018].map(y => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>
      {items.length === 0 ? (
        <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-12 text-center">No PYQs match.</div>
      ) : (
        <div>
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="text-xs mono text-muted-foreground">
              PYQ {idx + 1} of {items.length}
              {current?.user_progress?.count > 0 && (
                <span className="ml-3 inline-flex items-center gap-1 text-emerald-500"><CheckCircle2 className="w-3 h-3" /> attempted {current.user_progress.count}×</span>
              )}
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" data-testid="pyq-prev-btn" disabled={idx === 0} onClick={() => setIdx(i => i - 1)}><ChevronLeft className="w-4 h-4" /></Button>
              <Button size="sm" variant="outline" data-testid="pyq-next-btn" disabled={idx === items.length - 1} onClick={() => setIdx(i => i + 1)}><ChevronRight className="w-4 h-4" /></Button>
            </div>
          </div>
          <QuestionViewer item={current} type="pyq" key={current.pyq_id} />
        </div>
      )}
    </div>
  );
}
