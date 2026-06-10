import React, { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import QuestionViewer from "@/components/QuestionViewer";
import QuestionForm from "@/components/QuestionForm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, History } from "lucide-react";

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

export default function PYQs() {
  const [subjects, setSubjects] = useState([]);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState({
    subject_id: "", topic_id: "", year: "",
    attempted: "", result: "", flag: "",
  });
  const [topics, setTopics] = useState([]);
  const [openAdd, setOpenAdd] = useState(false);
  const [editing, setEditing] = useState(null);

  useEffect(() => { api.get("/subjects").then(r => setSubjects(r.data?.data || [])); }, []);
  useEffect(() => {
    if (!filter.subject_id) { setTopics([]); return; }
    api.get(`/subjects/${filter.subject_id}/topics`).then(r => setTopics(r.data?.data || []));
  }, [filter.subject_id]);

  const load = () => {
    const params = {};
    Object.entries(filter).forEach(([k, v]) => { if (v) params[k] = v; });
    api.get("/pyqs", { params }).then(r => {
      setItems(r.data?.data?.items || []);
      setTotal(r.data?.data?.total || 0);
    });
  };
  useEffect(load, [filter]);

  const showResultFilter = filter.attempted === "true";
  const setOne = (k, v) => setFilter(prev => {
    const next = { ...prev, [k]: v };
    if (k === "attempted" && v !== "true") next.result = "";
    return next;
  });

  const onSaved = () => { setOpenAdd(false); setEditing(null); load(); };

  const flagsByPid = useMemo(() => {
    const m = {};
    items.forEach(it => { m[it.pyq_id] = it.flags || []; });
    return m;
  }, [items]);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Past Year Questions</div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">PYQs</h1>
          <p className="text-sm text-muted-foreground mt-1 mono">{total} PYQ{total === 1 ? "" : "s"} · your private bank</p>
        </div>
        <Dialog open={openAdd} onOpenChange={setOpenAdd}>
          <DialogTrigger asChild>
            <Button data-testid="add-pyq-btn"><Plus className="w-4 h-4 mr-1" /> Add PYQ</Button>
          </DialogTrigger>
          <DialogContent className="bg-card border-border max-w-2xl">
            <DialogHeader><DialogTitle>Add PYQ</DialogTitle></DialogHeader>
            <QuestionForm isPyq={true} initial={null} onSaved={onSaved} onCancel={() => setOpenAdd(false)} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          <select value={filter.subject_id} onChange={e => setFilter({ ...filter, subject_id: e.target.value, topic_id: "" })}
            className="h-9 px-3 text-sm bg-transparent border border-border rounded-md" data-testid="pyq-subject-filter">
            <option value="">All subjects</option>
            {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
          </select>
          <select value={filter.topic_id} onChange={e => setFilter({ ...filter, topic_id: e.target.value })}
            className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
            <option value="">All topics</option>
            {topics.map(t => <option key={t.topic_id} value={t.topic_id}>{t.name}</option>)}
          </select>
          <Input type="number" value={filter.year} onChange={e => setFilter({ ...filter, year: e.target.value })} placeholder="Year" className="w-28" />
        </div>
        <div className="flex flex-wrap gap-2">
          <FilterPills
            label="Status"
            value={filter.attempted}
            onChange={(v) => setOne("attempted", v)}
            testid="pyq-status"
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
              testid="pyq-result"
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
            testid="pyq-flag"
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
          <History className="w-5 h-5" />
          No PYQs match these filters. Try clearing or click “Add PYQ” to create one.
        </div>
      ) : (
        <div>
          {items.map(q => (
            <QuestionViewer
              key={q.pyq_id}
              item={{ ...q, flags: flagsByPid[q.pyq_id] || q.flags || [] }}
              type="pyq"
              onEdit={(it) => setEditing(it)}
              onDeleted={() => load()}
              onAttempted={() => load()}
              onFlagsChanged={() => load()}
            />
          ))}
        </div>
      )}

      <Dialog open={!!editing} onOpenChange={(v) => !v && setEditing(null)}>
        <DialogContent className="bg-card border-border max-w-2xl">
          <DialogHeader><DialogTitle>Edit PYQ</DialogTitle></DialogHeader>
          {editing && (
            <QuestionForm isPyq={true} initial={editing} onSaved={onSaved} onCancel={() => setEditing(null)} />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
