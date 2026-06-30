import React, { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import QuestionViewer from "@/components/QuestionViewer";
import QuestionForm from "@/components/QuestionForm";
import FilterPills from "@/components/common/FilterPills";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, FileQuestion } from "lucide-react";
import Layout from "@/components/Layout";
import { toast } from "sonner";

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

  const [activeIndex, setActiveIndex] = useState(0);
  const [notes, setNotes] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [sessionCorrect, setSessionCorrect] = useState(0);
  const [sessionTotal, setSessionTotal] = useState(0);

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

  useEffect(() => {
    setActiveIndex(0);
    load();
  }, [filter]); // eslint-disable-line

  const activeQ = items[activeIndex];

  useEffect(() => {
    if (!activeQ) {
      setNotes("");
      return;
    }
    api.get(`/questions/${activeQ.question_id}/notes`)
      .then(r => setNotes(r.data?.data?.note_content || ""))
      .catch(() => setNotes(""));
  }, [activeQ?.question_id]);

  const saveNotes = async () => {
    if (!activeQ) return;
    setSavingNote(true);
    try {
      await api.post(`/questions/${activeQ.question_id}/notes`, { note_content: notes });
      toast.success("Notes saved");
    } catch {
      toast.error("Failed to save notes");
    }
    setSavingNote(false);
  };

  const handleAttempted = (attemptResult) => {
    setSessionTotal(prev => prev + 1);
    if (attemptResult?.attempt?.is_correct) {
      setSessionCorrect(prev => prev + 1);
    }
    load();
  };

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

  const relatedConcepts = useMemo(() => {
    if (!activeQ) return [];
    return [
      activeQ.topic_name || "General Topic",
      activeQ.subject_name || "General Subject",
      "SI Unit Precision",
      "Time Complexity"
    ].filter(Boolean);
  }, [activeQ]);

  const aiInsight = useMemo(() => {
    if (!activeQ) return "";
    if (activeQ.question_type === "NAT") {
      return "This is a Numerical Answer Type (NAT). Double-check your decimal conversion and unit prefixes (like milliseconds vs seconds) before submitting!";
    }
    if (activeQ.question_type === "MSQ") {
      return "This is a Multiple Select Question (MSQ) which may have one or more correct options. Note that there is no partial marking!";
    }
    return "MCQ questions have negative marking (-1/3). Eliminate obviously incorrect options to improve your accuracy, or use Skip if unsure.";
  }, [activeQ]);

  return (
    <Layout title="Question Bank">
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
              className="h-9 pl-3 pr-10 text-sm bg-transparent border border-border rounded-md appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[position:right_12px_center] bg-[size:16px] bg-no-repeat" data-testid="qb-subject-filter">
              <option value="">All subjects</option>
              {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
            </select>
            <select value={filter.topic_id} onChange={e => setFilter({ ...filter, topic_id: e.target.value })}
              className="h-9 pl-3 pr-10 text-sm bg-transparent border border-border rounded-md appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[position:right_12px_center] bg-[size:16px] bg-no-repeat">
              <option value="">All topics</option>
              {topics.map(t => <option key={t.topic_id} value={t.topic_id}>{t.name}</option>)}
            </select>
            <select value={filter.question_type} onChange={e => setFilter({ ...filter, question_type: e.target.value })}
              className="h-9 pl-3 pr-10 text-sm bg-transparent border border-border rounded-md appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[position:right_12px_center] bg-[size:16px] bg-no-repeat">
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
          <div className="grid grid-cols-12 gap-6 items-start">
            {/* Left Pane (Question Viewer) */}
            <div className="col-span-12 xl:col-span-8 space-y-6">
              <div className="border border-border rounded-3xl p-6 relative overflow-hidden bg-card/10 backdrop-blur-md">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-xs font-mono text-muted-foreground">Question {activeIndex + 1} of {total}</span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={activeIndex === 0}
                      onClick={() => setActiveIndex(prev => prev - 1)}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={activeIndex >= items.length - 1}
                      onClick={() => setActiveIndex(prev => prev + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
                {activeQ && (
                  <QuestionViewer
                    key={activeQ.question_id}
                    item={{ ...activeQ, flags: flagsByQid[activeQ.question_id] || activeQ.flags || [] }}
                    type="question"
                    hideNotes={true}
                    onEdit={(it) => setEditing(it)}
                    onDeleted={() => {
                      load();
                      setActiveIndex(0);
                    }}
                    onAttempted={handleAttempted}
                    onFlagsChanged={load}
                  />
                )}
              </div>
            </div>

            {/* Right Pane (Sidebar Details) */}
            <div className="col-span-12 xl:col-span-4 space-y-6">
              <div className="border border-border rounded-3xl p-6 bg-card/25 backdrop-blur-xl space-y-6 sticky top-24">
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      Personal Notes
                    </h3>
                    <span className="text-[10px] font-mono text-muted-foreground">
                      {savingNote ? "Saving..." : "Auto-saved"}
                    </span>
                  </div>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    onBlur={saveNotes}
                    placeholder="Jot down formulas or key logic for this question..."
                    className="w-full h-40 bg-white/5 border border-border rounded-2xl p-4 text-sm text-foreground placeholder:text-muted-foreground/30 focus:ring-1 focus:ring-primary/50 resize-none outline-none"
                  />
                </div>

                {relatedConcepts.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Related Concepts</h4>
                    <div className="flex flex-wrap gap-2">
                      {relatedConcepts.map((tag, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1 bg-white/5 border border-border rounded-full text-xs text-foreground/80 hover:text-foreground cursor-pointer transition-colors"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {aiInsight && (
                  <div className="p-4 border border-blue-500/20 rounded-2xl bg-blue-500/5 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-blue-400 text-sm font-bold">★ AI Insight</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {aiInsight}
                    </p>
                  </div>
                )}

                <div className="border border-dashed border-border rounded-2xl p-4 space-y-3 bg-card/10">
                  <h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Session Stats</h3>
                  <div className="flex justify-between items-end">
                    <div>
                      <p className="text-2xl font-bold text-foreground">{sessionCorrect}/{sessionTotal}</p>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Correct This Session</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-mono text-emerald-400">+{sessionCorrect * 20} XP</p>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Earned</p>
                    </div>
                  </div>
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${sessionTotal > 0 ? (sessionCorrect / sessionTotal) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
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
    </Layout>
  );
}
