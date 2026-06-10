import React, { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import QuestionViewer from "@/components/QuestionViewer";
import QuestionForm from "@/components/QuestionForm";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, FileQuestion } from "lucide-react";

const FilterPills = ({ label, value, onChange, options, testid }) => (
  <div className="flex items-center gap-1 border border-border rounded-md p-0.5 bg-card/30" data-testid={testid}>
    <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground px-2">{label}</span>
    {options.map(o => (
      <button
        key={o.value}
        onClick={() => onChange(o.value)}
        className={`px-2 h-7 text-xs rounded transition-colors ${
          value === o.value ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground"
        }`}
        data-testid={`${testid}-${o.value || "all"}`}
      >
        {o.label}
      </button>
    ))}
  </div>
);

export default function QuestionBank() {
  const [subjects, setSubjects] = useState([]);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState({
    subject_id: "", topic_id: "", difficulty: "", question_type: "",
    attempted: "", result: "", flag: "",
  });
  const [topics, setTopics] = useState([]);
  const [openAdd, setOpenAdd] = useState(false);
  const [editing, setEditing] = useState(null); // question object or null

  useEffect(() => { api.get("/subjects").then(r => setSubjects(r.data?.data || [])); }, []);
  useEffect(() => {
    if (!filter.subject_id) { setTopics([]); return; }
    api.get(`/subjects/${filter.subject_id}/topics`).then(r => setTopics(r.data?.data || []));
  }, [filter.subject_id]);

  const load = () => {
    const params = {};
    Object.entries(filter).forEach(([k, v]) => { if (v) params[k] = v; });
    api.get("/questions", { params }).then(r => {
      setItems(r.data?.data?.items || []);
      setTotal(r.data?.data?.total || 0);
    });
  };
  useEffect(load, [filter]);

  const showResultFilter = filter.attempted === "true";

  const setOne = (k, v) => setFilter(prev => {
    const next = { ...prev, [k]: v };
    // If user moves off Attempted, clear the result sub-filter to keep state clean.
    if (k === "attempted" && v !== "true") next.result = "";
    return next;
  });

  const onSaved = (savedDoc) => {
    setOpenAdd(false);
    setEditing(null);
    load();
  };

  const flagsByQid = useMemo(() => {
    const m = {};
    items.forEach(it => { m[it.question_id] = it.flags || []; });
    return m;
  }, [items]);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Library</div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Question Bank</h1>
          <p className="text-sm text-muted-foreground mt-1 mono">{total} question{total === 1 ? "" : "s"} · your private bank</p>
        </div>
        <Dialog open={openAdd} onOpenChange={setOpenAdd}>
          <DialogTrigger asChild>
            <Button data-testid="add-question-btn"><Plus className="w-4 h-4 mr-1" /> Add Question</Button>
          </DialogTrigger>
          <DialogContent className="bg-card border-border max-w-2xl">
            <DialogHeader><DialogTitle>Add Question</DialogTitle></DialogHeader>
            <QuestionForm isPyq={false} initial={null} onSaved={onSaved} onCancel={() => setOpenAdd(false)} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          <select value={filter.subject_id} onChange={e => setFilter({ ...filter, subject_id: e.target.value, topic_id: "" })}
            className="h-9 px-3 text-sm bg-transparent border border-border rounded-md" data-testid="qb-subject-filter">
            <option value="">All subjects</option>
            {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
          </select>
          <select value={filter.topic_id} onChange={e => setFilter({ ...filter, topic_id: e.target.value })}
            className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
            <option value="">All topics</option>
            {topics.map(t => <option key={t.topic_id} value={t.topic_id}>{t.name}</option>)}
          </select>
          <select value={filter.difficulty} onChange={e => setFilter({ ...filter, difficulty: e.target.value })}
            className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
            <option value="">All difficulty</option>
            <option>Easy</option><option>Medium</option><option>Hard</option>
          </select>
          <select value={filter.question_type} onChange={e => setFilter({ ...filter, question_type: e.target.value })}
            className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
            <option value="">All types</option>
            <option>MCQ</option><option>MSQ</option><option>NAT</option>
          </select>
        </div>
        <div className="flex flex-wrap gap-2">
          <FilterPills
            label="Status"
            value={filter.attempted}
            onChange={(v) => setOne("attempted", v)}
            testid="qb-status"
            options={[
              { value: "", label: "All" },
              { value: "false", label: "Not attempted" },
              { value: "true", label: "Attempted" },
            ]}
          />
          {showResultFilter && (
            <FilterPills
              label="Result"
              value={filter.result}
              onChange={(v) => setOne("result", v)}
              testid="qb-result"
              options={[
                { value: "", label: "All" },
                { value: "correct", label: "Correct" },
                { value: "incorrect", label: "Incorrect" },
              ]}
            />
          )}
          <FilterPills
            label="Flag"
            value={filter.flag}
            onChange={(v) => setOne("flag", v)}
            testid="qb-flag"
            options={[
              { value: "", label: "All" },
              { value: "review", label: "Review" },
              { value: "important", label: "Important" },
            ]}
          />
        </div>
      </div>

      {items.length === 0 ? (
        <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-12 text-center flex flex-col items-center gap-2">
          <FileQuestion className="w-5 h-5" />
          No questions match these filters. Try clearing or click “Add Question” to create one.
        </div>
      ) : (
        <div>
          {items.map(q => (
            <QuestionViewer
              key={q.question_id}
              item={{ ...q, flags: flagsByQid[q.question_id] || q.flags || [] }}
              type="question"
              onEdit={(it) => setEditing(it)}
              onDeleted={() => load()}
              onAttempted={() => load()}
              onFlagsChanged={(_id, _flags) => load()}
            />
          ))}
        </div>
      )}

      <Dialog open={!!editing} onOpenChange={(v) => !v && setEditing(null)}>
        <DialogContent className="bg-card border-border max-w-2xl">
          <DialogHeader><DialogTitle>Edit Question</DialogTitle></DialogHeader>
          {editing && (
            <QuestionForm isPyq={false} initial={editing} onSaved={onSaved} onCancel={() => setEditing(null)} />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
