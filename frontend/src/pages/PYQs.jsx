import React, { useEffect, useMemo, useState } from "react";
import QuestionViewer from "@/components/QuestionViewer";
import QuestionForm from "@/components/QuestionForm";
import FilterPills from "@/components/common/FilterPills";
import AppSelect from "@/components/common/AppSelect";
import PaginationControls from "@/components/common/PaginationControls";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, History } from "lucide-react";
import Layout from "@/components/Layout";
import QueryError from "@/components/common/QueryError";
import { usePyqs } from "@/features/practice/hooks/usePractice";
import { useSubjects, useTopics } from "@/features/subjects/hooks/useSubjects";

const PAGE_SIZE = 50;

export default function PYQs() {
  const [filter, setFilter] = useState({
    subject_id: "", topic_id: "", year: "",
    attempted: "", result: "", flag: "",
  });
  const [page, setPage] = useState(0);
  const [openAdd, setOpenAdd] = useState(false);
  const [editing, setEditing] = useState(null);

  const { data: subjects = [] } = useSubjects();
  const { data: topics = [] } = useTopics(filter.subject_id);
  const queryFilter = useMemo(() => ({
    ...filter,
    limit: PAGE_SIZE,
    skip: page * PAGE_SIZE,
  }), [filter, page]);
  const { data: pyqData, refetch: refetchPyqs, isError } = usePyqs(queryFilter);
  const items = pyqData?.items || [];
  const total = pyqData?.total || 0;

  useEffect(() => {
    setPage(0);
  }, [filter]);

  const showResultFilter = filter.attempted === "true";
  const setOne = (k, v) => setFilter(prev => {
    const next = { ...prev, [k]: v };
    if (k === "attempted" && v !== "true") next.result = "";
    return next;
  });

  const onSaved = () => { setOpenAdd(false); setEditing(null); refetchPyqs(); };

  const flagsByPid = useMemo(() => {
    const m = {};
    items.forEach(it => { m[it.pyq_id] = it.flags || []; });
    return m;
  }, [items]);

  if (isError) return (
    <Layout title="PYQs">
      <QueryError onRetry={refetchPyqs} />
    </Layout>
  );

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
            <AppSelect
              value={filter.subject_id}
              onChange={(value) => setFilter({ ...filter, subject_id: value, topic_id: "" })}
              className="min-w-[190px]"
              testId="pyq-subject-filter"
              options={[
                { value: "", label: "All subjects" },
                ...subjects.map((s) => ({ value: s.subject_id, label: s.name })),
              ]}
            />
            <AppSelect
              value={filter.topic_id}
              onChange={(value) => setFilter({ ...filter, topic_id: value })}
              className="min-w-[160px]"
              options={[
                { value: "", label: "All topics" },
                ...topics.map((t) => ({ value: t.topic_id, label: t.name })),
              ]}
            />
            <AppSelect
              value={filter.year}
              onChange={(value) => setFilter({ ...filter, year: value })}
              className="min-w-[120px]"
              options={[
                { value: "", label: "All years" },
                ...Array.from({ length: 27 }, (_, i) => 2026 - i).map((y) => ({ value: String(y), label: String(y) })),
              ]}
            />
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
                onDeleted={() => refetchPyqs()}
                onAttempted={() => refetchPyqs()}
                onFlagsChanged={() => refetchPyqs()}
              />
            ))}
          </div>
        )}

        {total > PAGE_SIZE && (
          <PaginationControls
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            visibleCount={items.length}
            onPageChange={setPage}
          />
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
