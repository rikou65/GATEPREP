import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import AppSelect from "@/components/common/AppSelect";
import { toast } from "sonner";
import { useSavePyq, useSaveQuestion } from "@/features/practice/hooks/usePractice";
import { useSubjects, useTopics } from "@/features/subjects/hooks/useSubjects";

/**
 * Reusable form to create or edit a Question / PYQ.
 * Props:
 *  - isPyq: bool
 *  - initial: existing item (null for create)
 *  - onSaved: (savedDoc) => void
 *  - onCancel: () => void
 */
export default function QuestionForm({ isPyq = false, initial = null, onSaved, onCancel }) {
  const [form, setForm] = useState(() => ({
    subject_id: initial?.subject_id || "",
    topic_id: initial?.topic_id || "",
    question_type: initial?.question_type || "MCQ",
    question_text: initial?.question_text || "",
    options: initial?.options || ["", "", "", ""],
    correct_answer:
      initial?.correct_answer !== undefined && initial?.correct_answer !== null
        ? (typeof initial.correct_answer === "string" ? initial.correct_answer : JSON.stringify(initial.correct_answer))
        : "",
    solution: initial?.solution || "",
    source: initial?.source || (isPyq ? "GATE" : "User"),
    year: initial?.year || (isPyq ? new Date().getFullYear() : null),
  }));

  const isEdit = !!initial;
  const itemId = isEdit ? (isPyq ? initial.pyq_id : initial.question_id) : null;
  const { data: subjects = [] } = useSubjects();
  const { data: topics = [] } = useTopics(form.subject_id);
  const saveQuestion = useSaveQuestion();
  const savePyq = useSavePyq();
  const saving = saveQuestion.isPending || savePyq.isPending;

  const submit = async () => {
    if (!form.subject_id || !form.topic_id || !form.question_text) return toast.error("Subject, topic and question text are required");
    const payload = { ...form };
    if (form.question_type === "MSQ") {
      try { payload.correct_answer = JSON.parse(form.correct_answer); }
      catch { return toast.error("For MSQ, correct_answer must be JSON array e.g. [\"0\",\"2\"]"); }
    } else if (form.question_type === "NAT") {
      payload.options = null;
    }
    try {
      const saved = isPyq
        ? await savePyq.mutateAsync({ pyqId: itemId, payload })
        : await saveQuestion.mutateAsync({ questionId: itemId, payload });
      toast.success(`${isPyq ? "PYQ" : "Question"} ${isEdit ? "updated" : "added"}`);
      onSaved && onSaved(saved);
    } catch (e) {
      toast.error(e?.response?.data?.error?.message || e?.response?.data?.detail || "Save failed");
    }
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <AppSelect
          value={form.subject_id}
          onChange={(value) => setForm({ ...form, subject_id: value, topic_id: "" })}
          className="w-full"
          testId="qf-subject"
          options={[
            { value: "", label: "Subject" },
            ...subjects.map((s) => ({ value: s.subject_id, label: s.name })),
          ]}
        />
        <AppSelect
          value={form.topic_id}
          onChange={(value) => setForm({ ...form, topic_id: value })}
          className="w-full"
          testId="qf-topic"
          options={[
            { value: "", label: "Topic" },
            ...topics.map((t) => ({ value: t.topic_id, label: t.name })),
          ]}
        />
        <AppSelect
          value={form.question_type}
          onChange={(value) => setForm({ ...form, question_type: value })}
          className="w-full"
          options={[
            { value: "MCQ", label: "MCQ" },
            { value: "MSQ", label: "MSQ" },
            { value: "NAT", label: "NAT" },
          ]}
        />
        {isPyq && (
          <Input type="number" placeholder="Year" value={form.year || ""} onChange={e => setForm({ ...form, year: parseInt(e.target.value || "0") || null })} />
        )}
        <Input placeholder="Source (e.g. NPTEL, Made Easy, GATE 2024)" value={form.source}
          onChange={e => setForm({ ...form, source: e.target.value })} />
      </div>
      <Textarea placeholder="Question text" value={form.question_text} onChange={e => setForm({ ...form, question_text: e.target.value })} className="min-h-[100px]" data-testid="qf-text" />
      {form.question_type !== "NAT" && (
        <div className="space-y-2">
          {form.options.map((o, i) => (
            <Input key={i} placeholder={`Option ${i}`} value={o} onChange={e => {
              const opts = [...form.options]; opts[i] = e.target.value; setForm({ ...form, options: opts });
            }} />
          ))}
        </div>
      )}
      <Input
        placeholder={form.question_type === "MSQ" ? 'Correct answer JSON e.g. ["0","2"]' : "Correct answer (index 0/1/2/3 for MCQ, numeric value for NAT)"}
        value={form.correct_answer}
        onChange={e => setForm({ ...form, correct_answer: e.target.value })}
        data-testid="qf-answer"
      />
      <Textarea placeholder="Solution / explanation" value={form.solution} onChange={e => setForm({ ...form, solution: e.target.value })} />
      <div className="flex justify-end gap-2 pt-2">
        {onCancel && <Button variant="outline" onClick={onCancel} disabled={saving}>Cancel</Button>}
        <Button onClick={submit} disabled={saving} data-testid="qf-save">
          {saving ? "Saving…" : (isEdit ? "Save changes" : `Add ${isPyq ? "PYQ" : "Question"}`)}
        </Button>
      </div>
    </div>
  );
}
