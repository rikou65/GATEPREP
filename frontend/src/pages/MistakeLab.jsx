import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trash2, AlertOctagon } from "lucide-react";
import { toast } from "sonner";
import Layout from "@/components/Layout";
import QueryError from "@/components/common/QueryError";
import AppSelect from "@/components/common/AppSelect";
import { useDeleteMistake, useMistakes } from "@/features/practice/hooks/usePractice";
import { useSubjects } from "@/features/subjects/hooks/useSubjects";

export default function MistakeLab() {
  const [filter, setFilter] = useState({ subject_id: "", mistake_type: "" });
  const { data: subjects = [] } = useSubjects();
  const { data: items = [], isError, refetch } = useMistakes(filter);
  const deleteMistake = useDeleteMistake();

  if (isError) return (
    <Layout title="Mistake Lab">
      <QueryError onRetry={refetch} />
    </Layout>
  );

  const remove = async (id) => {
    try {
      await deleteMistake.mutateAsync(id);
      toast.success("Removed");
    } catch {
      toast.error("Failed to remove mistake");
    }
  };

  return (
    <Layout title="Mistake Lab">
      <div className="space-y-6">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Self-correction</div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Mistake Lab</h1>
          <p className="text-sm text-muted-foreground mt-1">Categorize and revisit incorrect attempts.</p>
        </div>
        <div className="flex gap-2">
          <AppSelect
            value={filter.subject_id}
            onChange={(value) => setFilter(f => ({ ...f, subject_id: value }))}
            className="min-w-[190px]"
            options={[
              { value: "", label: "All subjects" },
              ...subjects.map((s) => ({ value: s.subject_id, label: s.name })),
            ]}
          />
          <AppSelect
            value={filter.mistake_type}
            onChange={(value) => setFilter(f => ({ ...f, mistake_type: value }))}
            className="min-w-[160px]"
            options={[
              { value: "", label: "All types" },
              { value: "Conceptual Gap", label: "Conceptual Gap" },
              { value: "Calculation Error", label: "Calculation Error" },
              { value: "Question Misread", label: "Question Misread" },
              { value: "Silly Mistake", label: "Silly Mistake" },
            ]}
          />
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
    </Layout>
  );
}
