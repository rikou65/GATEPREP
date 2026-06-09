import React, { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useSearchParams } from "react-router-dom";
import QuestionViewer from "@/components/QuestionViewer";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChevronLeft, ChevronRight, CheckCircle2 } from "lucide-react";

export default function QuestionBank() {
  const [search] = useSearchParams();
  const subject_id = search.get("subject_id");
  const topic_id = search.get("topic_id");
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [filter, setFilter] = useState({
    subject_id: subject_id || "",
    topic_id: topic_id || "",
    question_type: "",
    difficulty: "",
  });
  const [items, setItems] = useState([]);
  const [idx, setIdx] = useState(0);

  useEffect(() => { api.get("/subjects").then(r => setSubjects(r.data?.data || [])); }, []);
  useEffect(() => {
    if (!filter.subject_id) { setTopics([]); return; }
    api.get(`/subjects/${filter.subject_id}/topics`).then(r => setTopics(r.data?.data || []));
  }, [filter.subject_id]);

  useEffect(() => {
    const params = {};
    Object.entries(filter).forEach(([k, v]) => { if (v) params[k] = v; });
    api.get("/questions", { params }).then(r => { setItems(r.data?.data?.items || []); setIdx(0); });
  }, [filter]);

  const current = items[idx];

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Practice</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Question Bank</h1>
      </div>

      <div className="flex flex-wrap gap-2">
        <select data-testid="filter-subject" value={filter.subject_id} onChange={(e) => setFilter(f => ({ ...f, subject_id: e.target.value, topic_id: "" }))}
          className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">All subjects</option>
          {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
        </select>
        <select data-testid="filter-topic" value={filter.topic_id} onChange={(e) => setFilter(f => ({ ...f, topic_id: e.target.value }))}
          className="h-9 px-3 text-sm bg-transparent border border-border rounded-md" disabled={!filter.subject_id}>
          <option value="">All topics</option>
          {topics.map(t => <option key={t.topic_id} value={t.topic_id}>{t.name}</option>)}
        </select>
        <select value={filter.question_type} onChange={(e) => setFilter(f => ({ ...f, question_type: e.target.value }))}
          className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">All types</option>
          <option>MCQ</option><option>MSQ</option><option>NAT</option>
        </select>
        <select value={filter.difficulty} onChange={(e) => setFilter(f => ({ ...f, difficulty: e.target.value }))}
          className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">All difficulties</option>
          <option>Easy</option><option>Medium</option><option>Hard</option>
        </select>
      </div>

      {items.length === 0 ? (
        <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-12 text-center">
          No questions match. Try adjusting filters.
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="text-xs mono text-muted-foreground">
              Question {idx + 1} of {items.length}
              {current?.user_progress?.count > 0 && (
                <span className="ml-3 inline-flex items-center gap-1 text-emerald-500">
                  <CheckCircle2 className="w-3 h-3" /> attempted {current.user_progress.count}×
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" data-testid="prev-q-btn" disabled={idx === 0} onClick={() => setIdx(i => i - 1)}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button size="sm" variant="outline" data-testid="next-q-btn" disabled={idx === items.length - 1} onClick={() => setIdx(i => i + 1)}>
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
          <QuestionViewer item={current} type="question" key={current.question_id} />
        </div>
      )}
    </div>
  );
}
