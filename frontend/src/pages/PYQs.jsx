import React, { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import QuestionViewer from "@/components/QuestionViewer";
import QuestionForm from "@/components/QuestionForm";
import FilterPills from "@/components/common/FilterPills";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, History } from "lucide-react";
import Layout from "@/components/Layout";

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
    <Layout title="PYQs">
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
              className="h-9 pl-3 pr-10 text-sm bg-transparent border border-border rounded-md appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[position:right_12px_center] bg-[size:16px] bg-no-repeat" data-testid="pyq-subject-filter">
              <option value="">All subjects</option>
              {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
            </select>
            <select value={filter.topic_id} onChange={e => setFilter({ ...filter, topic_id: e.target.value })}
              className="h-9 pl-3 pr-10 text-sm bg-transparent border border-border rounded-md appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[position:right_12px_center] bg-[size:16px] bg-no-repeat">
              <option value="">All topics</option>
              {topics.map(t => <option key={t.topic_id} value={t.topic_id}>{t.name}</option>)}
            </select>
            <select value={filter.year} onChange={e => setFilter({ ...filter, year: e.target.value })}
              className="h-9 pl-3 pr-10 text-sm bg-transparent border border-border rounded-md w-28 appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[position:right_12px_center] bg-[size:16px] bg-no-repeat">
              <option value="">All years</option>
              {Array.from({ length: 27 }, (_, i) => 2026 - i).map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
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
    </Layout>
  );
}
