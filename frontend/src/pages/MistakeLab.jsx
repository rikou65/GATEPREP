import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trash2, AlertOctagon } from "lucide-react";
import { toast } from "sonner";

export default function MistakeLab() {
  const [subjects, setSubjects] = useState([]);
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState({ subject_id: "", mistake_type: "" });

  const load = () => {
    const params = {};
    Object.entries(filter).forEach(([k, v]) => { if (v) params[k] = v; });
    api.get("/mistakes", { params }).then(r => setItems(r.data?.data || []));
  };
  useEffect(() => { api.get("/subjects").then(r => setSubjects(r.data?.data || [])); }, []);
  useEffect(load, [filter]); // eslint-disable-line

  const remove = async (id) => {
    await api.delete(`/mistakes/${id}`);
    toast.success("Removed");
    load();
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Self-correction</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Mistake Lab</h1>
        <p className="text-sm text-muted-foreground mt-1">Categorize and revisit incorrect attempts.</p>
      </div>
      <div className="flex gap-2">
        <select value={filter.subject_id} onChange={(e) => setFilter(f => ({ ...f, subject_id: e.target.value }))} className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">All subjects</option>
          {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
        </select>
        <select value={filter.mistake_type} onChange={(e) => setFilter(f => ({ ...f, mistake_type: e.target.value }))} className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">All types</option>
          <option>Conceptual Gap</option>
          <option>Calculation Error</option>
          <option>Question Misread</option>
          <option>Silly Mistake</option>
        </select>
      </div>
      {items.length === 0 ? (
        <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-12 text-center flex flex-col items-center gap-2">
          <AlertOctagon className="w-5 h-5" />
          No mistakes logged yet. Mistakes flagged from Question Bank will appear here.
        </div>
      ) : (
        <div className="space-y-2">
          {items.map(m => (
            <div key={m.mistake_id} className="border border-border rounded-lg p-4" data-testid={`mistake-${m.mistake_id}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline" className="mono text-[10px]">{m.mistake_type}</Badge>
                    <span className="text-[10px] mono text-muted-foreground">{new Date(m.created_at).toLocaleString()}</span>
                  </div>
                  <div className="text-sm mt-2">{m.question?.question_text}</div>
                </div>
                <Button size="sm" variant="ghost" data-testid={`delete-mistake-${m.mistake_id}`} onClick={() => remove(m.mistake_id)}>
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
