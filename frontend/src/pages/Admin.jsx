import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";

function QuestionForm({ isPyq = false }) {
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [form, setForm] = useState({
    subject_id: "", topic_id: "", question_type: "MCQ",
    question_text: "", options: ["", "", "", ""], correct_answer: "",
    solution: "", difficulty: "Medium", source: "Admin", year: 2024,
  });
  useEffect(() => { api.get("/subjects").then(r => setSubjects(r.data?.data || [])); }, []);
  useEffect(() => {
    if (!form.subject_id) return;
    api.get(`/subjects/${form.subject_id}/topics`).then(r => setTopics(r.data?.data || []));
  }, [form.subject_id]);

  const submit = async () => {
    if (!form.subject_id || !form.topic_id || !form.question_text) return toast.error("Missing fields");
    const payload = { ...form };
    if (form.question_type === "MSQ") {
      try { payload.correct_answer = JSON.parse(form.correct_answer); }
      catch { return toast.error("MSQ correct_answer must be JSON array e.g. [\"0\",\"2\"]"); }
    }
    if (form.question_type === "NAT") payload.options = null;
    try {
      const endpoint = isPyq ? "/admin/pyqs" : "/admin/questions";
      await api.post(endpoint, payload);
      toast.success("Saved");
      setForm({ ...form, question_text: "", options: ["", "", "", ""], correct_answer: "", solution: "" });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  };

  return (
    <div className="space-y-3 max-w-2xl">
      <div className="grid grid-cols-2 gap-2">
        <select value={form.subject_id} onChange={e => setForm({ ...form, subject_id: e.target.value, topic_id: "" })} className="h-10 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">Subject</option>
          {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
        </select>
        <select value={form.topic_id} onChange={e => setForm({ ...form, topic_id: e.target.value })} className="h-10 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">Topic</option>
          {topics.map(t => <option key={t.topic_id} value={t.topic_id}>{t.name}</option>)}
        </select>
        <select value={form.question_type} onChange={e => setForm({ ...form, question_type: e.target.value })} className="h-10 px-3 text-sm bg-transparent border border-border rounded-md">
          <option>MCQ</option><option>MSQ</option><option>NAT</option>
        </select>
        <select value={form.difficulty} onChange={e => setForm({ ...form, difficulty: e.target.value })} className="h-10 px-3 text-sm bg-transparent border border-border rounded-md">
          <option>Easy</option><option>Medium</option><option>Hard</option>
        </select>
        {isPyq && (
          <Input type="number" placeholder="Year" value={form.year} onChange={e => setForm({ ...form, year: parseInt(e.target.value || "2024") })} />
        )}
      </div>
      <Textarea placeholder="Question text" value={form.question_text} onChange={e => setForm({ ...form, question_text: e.target.value })} className="min-h-[100px]" />
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
        placeholder={form.question_type === "MSQ" ? 'Correct answer JSON e.g. ["0","2"]' : "Correct answer (index for MCQ, value for NAT)"}
        value={typeof form.correct_answer === "string" ? form.correct_answer : JSON.stringify(form.correct_answer)}
        onChange={e => setForm({ ...form, correct_answer: e.target.value })}
      />
      <Textarea placeholder="Solution" value={form.solution} onChange={e => setForm({ ...form, solution: e.target.value })} />
      <Button onClick={submit} data-testid={isPyq ? "save-pyq-btn" : "save-question-btn"}>Save {isPyq ? "PYQ" : "Question"}</Button>
    </div>
  );
}

export default function Admin() {
  const [users, setUsers] = useState([]);
  useEffect(() => { api.get("/admin/users").then(r => setUsers(r.data?.data || [])).catch(() => {}); }, []);
  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Administration</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Admin Panel</h1>
      </div>
      <Tabs defaultValue="questions">
        <TabsList>
          <TabsTrigger value="questions" data-testid="tab-add-questions">Add Question</TabsTrigger>
          <TabsTrigger value="pyqs" data-testid="tab-add-pyqs">Add PYQ</TabsTrigger>
          <TabsTrigger value="users" data-testid="tab-users">Users</TabsTrigger>
        </TabsList>
        <TabsContent value="questions" className="pt-4"><QuestionForm /></TabsContent>
        <TabsContent value="pyqs" className="pt-4"><QuestionForm isPyq /></TabsContent>
        <TabsContent value="users" className="pt-4">
          <div className="border border-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-border">
                <tr className="text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                  <th className="p-3">Name</th><th className="p-3">Email</th><th className="p-3">Admin</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.user_id} className="border-b border-border">
                    <td className="p-3">{u.name}</td>
                    <td className="p-3 mono text-xs">{u.email}</td>
                    <td className="p-3 mono text-xs">{u.is_admin ? "yes" : "no"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
