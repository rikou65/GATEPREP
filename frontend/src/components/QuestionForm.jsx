import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

/**
 * Reusable form to create or edit a Question / PYQ.
 * Props:
 *  - isPyq: bool
 *  - initial: existing item (null for create)
 *  - onSaved: (savedDoc) => void
 *  - onCancel: () => void
 */
export default function QuestionForm({ isPyq = false, initial = null, onSaved, onCancel }) {
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [saving, setSaving] = useState(false);
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

  useEffect(() => { api.get("/subjects").then(r => setSubjects(r.data?.data || [])); }, []);
  useEffect(() => {
    if (!form.subject_id) { setTopics([]); return; }
    api.get(`/subjects/${form.subject_id}/topics`).then(r => setTopics(r.data?.data || []));
  }, [form.subject_id]);

  const isEdit = !!initial;
  const itemId = isEdit ? (isPyq ? initial.pyq_id : initial.question_id) : null;

  const submit = async () => {
    if (!form.subject_id || !form.topic_id || !form.question_text) return toast.error("Subject, topic and question text are required");
    const payload = { ...form };
    if (form.question_type === "MSQ") {
      try { payload.correct_answer = JSON.parse(form.correct_answer); }
      catch { return toast.error("For MSQ, correct_answer must be JSON array e.g. [\"0\",\"2\"]"); }
    } else if (form.question_type === "NAT") {
      payload.options = null;
    }
    setSaving(true);
    try {
      let r;
      if (isEdit) {
        const endpoint = isPyq ? `/pyqs/${itemId}` : `/questions/${itemId}`;
        r = await api.put(endpoint, payload);
        toast.success(`${isPyq ? "PYQ" : "Question"} updated`);
      } else {
        const endpoint = isPyq ? "/pyqs" : "/questions";
        r = await api.post(endpoint, payload);
        toast.success(`${isPyq ? "PYQ" : "Question"} added`);
      }
      onSaved && onSaved(r.data?.data);
    } catch (e) {
      toast.error(e?.response?.data?.error?.message || e?.response?.data?.detail || "Save failed");
    }
    setSaving(false);
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <select value={form.subject_id} onChange={e => setForm({ ...form, subject_id: e.target.value, topic_id: "" })}
          className="h-10 px-3 text-sm bg-transparent border border-border rounded-md" data-testid="qf-subject">
          <option value="">Subject</option>
          {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
        </select>
        <select value={form.topic_id} onChange={e => setForm({ ...form, topic_id: e.target.value })}
          className="h-10 px-3 text-sm bg-transparent border border-border rounded-md" data-testid="qf-topic">
          <option value="">Topic</option>
          {topics.map(t => <option key={t.topic_id} value={t.topic_id}>{t.name}</option>)}
        </select>
        <select value={form.question_type} onChange={e => setForm({ ...form, question_type: e.target.value })}
          className="h-10 px-3 text-sm bg-transparent border border-border rounded-md">
          <option>MCQ</option><option>MSQ</option><option>NAT</option>
        </select>
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
