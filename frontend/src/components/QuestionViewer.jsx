import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { ChevronDown, ChevronUp, Bookmark, Clock, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";

/**
 * type: "question" | "pyq"
 */
export default function QuestionViewer({ item, type = "question", onAttempted }) {
  const id = type === "pyq" ? item.pyq_id : item.question_id;
  const baseUrl = type === "pyq" ? `/pyqs/${id}` : `/questions/${id}`;

  const [selected, setSelected] = useState(item.question_type === "MSQ" ? [] : "");
  const [natValue, setNatValue] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState(null);
  const [showSolution, setShowSolution] = useState(false);
  const [notes, setNotes] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [attempts, setAttempts] = useState([]);
  const [startedAt] = useState(Date.now());
  const [mistakeType, setMistakeType] = useState("");

  useEffect(() => {
    if (type === "question") {
      api.get(`${baseUrl}/notes`).then((r) => setNotes(r.data?.data?.note_content || ""));
    }
    api.get(`${baseUrl}/attempts`).then((r) => setAttempts(r.data?.data || []));
  }, [baseUrl, type]);

  const saveNotes = async () => {
    if (type !== "question") return;
    setSavingNote(true);
    try {
      await api.post(`${baseUrl}/notes`, { note_content: notes });
      toast.success("Notes saved");
    } catch { toast.error("Failed to save"); }
    setSavingNote(false);
  };

  const submit = async () => {
    let payload = selected;
    if (item.question_type === "NAT") payload = natValue;
    const time_taken = Math.round((Date.now() - startedAt) / 1000);
    try {
      const r = await api.post(`${baseUrl}/attempt`, { selected_answer: payload, time_taken });
      setResult(r.data?.data);
      setSubmitted(true);
      setShowSolution(true);
      const fresh = await api.get(`${baseUrl}/attempts`);
      setAttempts(fresh.data?.data || []);
      onAttempted && onAttempted(r.data?.data);
    } catch (e) { toast.error("Submit failed"); }
  };

  const logMistake = async () => {
    if (!mistakeType || type !== "question") return;
    try {
      await api.post("/mistakes", { question_id: id, mistake_type: mistakeType, note: "" });
      toast.success("Logged to Mistake Lab");
      setMistakeType("");
    } catch { toast.error("Failed"); }
  };

  const correctAnswer = result?.correct_answer ?? item.correct_answer;
  const isCorrect = result?.attempt?.is_correct;

  const optionState = (idx) => {
    if (!submitted) return "border-border";
    const i = String(idx);
    if (item.question_type === "MCQ") {
      if (i === String(correctAnswer)) return "opt-correct";
      if (i === String(selected) && i !== String(correctAnswer)) return "opt-incorrect";
      return "border-border opacity-60";
    }
    if (item.question_type === "MSQ") {
      const correctArr = (correctAnswer || []).map(String);
      const selArr = (selected || []).map(String);
      if (correctArr.includes(i) && selArr.includes(i)) return "opt-correct";
      if (!correctArr.includes(i) && selArr.includes(i)) return "opt-incorrect";
      if (correctArr.includes(i) && !selArr.includes(i)) return "opt-missed";
      return "border-border opacity-60";
    }
    return "border-border";
  };

  return (
    <div className="border-y border-border py-6 my-6 space-y-5" data-testid={`q-viewer-${id}`}>
      <div className="flex items-start gap-1.5 flex-wrap">
        {item.subject_name && (
          <Badge variant="secondary" className="text-[10px] font-medium" data-testid="q-subject-tag">
            {item.subject_name}
          </Badge>
        )}
        {item.topic_name && (
          <Badge variant="secondary" className="text-[10px] font-medium" data-testid="q-topic-tag">
            {item.topic_name}
          </Badge>
        )}
        <Badge variant="outline" className="mono text-[10px]">{item.question_type}</Badge>
        {item.difficulty && <Badge variant="outline" className="mono text-[10px]">{item.difficulty}</Badge>}
        {item.year && <Badge variant="outline" className="mono text-[10px]">GATE {item.year}</Badge>}
        {item.source && <Badge variant="outline" className="mono text-[10px]">{item.source}</Badge>}
      </div>

      <div className="text-base leading-relaxed whitespace-pre-wrap" data-testid="question-text">
        {item.question_text}
      </div>

      {item.question_type === "MCQ" && (
        <RadioGroup
          value={String(selected)}
          onValueChange={(v) => !submitted && setSelected(v)}
          className="space-y-2"
        >
          {item.options?.map((opt, i) => (
            <label
              key={i}
              data-testid={`question-mcq-option-${i}`}
              className={`flex items-start gap-3 p-3 border rounded-md cursor-pointer transition-colors ${optionState(i)}`}
            >
              <RadioGroupItem value={String(i)} disabled={submitted} className="mt-0.5" />
              <span className="text-sm">{opt}</span>
            </label>
          ))}
        </RadioGroup>
      )}

      {item.question_type === "MSQ" && (
        <div className="space-y-2">
          {item.options?.map((opt, i) => {
            const checked = (selected || []).includes(String(i));
            return (
              <label
                key={i}
                data-testid={`question-msq-option-${i}`}
                className={`flex items-start gap-3 p-3 border rounded-md cursor-pointer transition-colors ${optionState(i)}`}
              >
                <Checkbox
                  checked={checked}
                  disabled={submitted}
                  onCheckedChange={(c) => {
                    setSelected((prev) =>
                      c ? [...(prev || []), String(i)] : (prev || []).filter((x) => x !== String(i))
                    );
                  }}
                />
                <span className="text-sm">{opt}</span>
              </label>
            );
          })}
        </div>
      )}

      {item.question_type === "NAT" && (
        <div className="flex items-center gap-3">
          <Input
            type="text"
            value={natValue}
            onChange={(e) => setNatValue(e.target.value)}
            disabled={submitted}
            placeholder="Enter numerical answer"
            className="max-w-xs"
            data-testid="question-nat-input"
          />
          {submitted && (
            <div className="text-xs mono text-muted-foreground">
              Correct: <span className="text-foreground">{String(correctAnswer)}</span>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-3 items-center pt-2">
        {!submitted ? (
          <Button data-testid="submit-answer-btn" onClick={submit}>Submit Answer</Button>
        ) : (
          <div className={`flex items-center gap-2 text-sm font-medium ${isCorrect ? "text-emerald-500" : "text-red-500"}`}>
            {isCorrect ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            {isCorrect ? "Correct" : "Incorrect"}
          </div>
        )}
        <Button
          variant="outline"
          size="sm"
          data-testid="solution-toggle-btn"
          onClick={() => setShowSolution((s) => !s)}
        >
          {showSolution ? <ChevronUp className="w-4 h-4 mr-1" /> : <ChevronDown className="w-4 h-4 mr-1" />}
          {showSolution ? "Hide" : "Show"} Solution
        </Button>
        {submitted && !isCorrect && type === "question" && (
          <div className="flex items-center gap-2">
            <select
              value={mistakeType}
              onChange={(e) => setMistakeType(e.target.value)}
              className="h-9 px-2 text-xs bg-transparent border border-border rounded-md"
              data-testid="mistake-type-select"
            >
              <option value="">Log mistake type…</option>
              <option>Conceptual Gap</option>
              <option>Calculation Error</option>
              <option>Question Misread</option>
              <option>Silly Mistake</option>
            </select>
            <Button size="sm" variant="outline" onClick={logMistake} data-testid="log-mistake-btn">
              <Bookmark className="w-3.5 h-3.5 mr-1" /> Log
            </Button>
          </div>
        )}
      </div>

      {showSolution && (
        <div
          className="mt-4 p-4 bg-secondary/40 border-l-2 border-foreground rounded-r-md text-sm leading-relaxed whitespace-pre-wrap"
          data-testid="solution-content"
        >
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Solution</div>
          {result?.solution || item.solution}
        </div>
      )}

      {type === "question" && (
        <div className="space-y-2 pt-2">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">My Notes</div>
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={saveNotes}
            placeholder="Capture concepts, tricks, shortcuts, observations…"
            className="min-h-[100px] font-mono text-sm"
            data-testid="notes-textarea"
          />
          <div className="text-[10px] text-muted-foreground mono">
            {savingNote ? "Saving…" : "Auto-saves on blur"}
          </div>
        </div>
      )}

      <div className="space-y-2 pt-2">
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Attempt History</div>
        {attempts.length === 0 ? (
          <div className="text-xs text-muted-foreground mono">No attempts yet</div>
        ) : (
          <div className="space-y-1">
            {attempts.map((a) => (
              <div key={a.attempt_id} className="flex items-center gap-3 text-xs mono border border-border rounded-md p-2">
                {a.is_correct ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-red-500" />
                )}
                <span className="text-muted-foreground">{new Date(a.attempted_at).toLocaleString()}</span>
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Clock className="w-3 h-3" /> {a.time_taken}s
                </span>
                <span className="truncate">ans: {JSON.stringify(a.selected_answer)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
