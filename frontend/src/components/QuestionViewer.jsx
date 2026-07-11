import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import AppSelect from "@/components/common/AppSelect";
import {
  CheckCircle2, XCircle, ChevronDown, ChevronUp, Bookmark, BookmarkCheck,
  Star, Clock, Pencil, Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { formatMathText, renderContentWithTables } from "@/lib/mathFormat";
import {
  useCreateMistake,
  useDeletePyq,
  useDeleteQuestion,
  usePyqAttempts,
  useQuestionAttempts,
  useQuestionNotes,
  useSaveQuestionNotes,
  useSubmitPyqAttempt,
  useSubmitQuestionAttempt,
  useTogglePyqFlag,
  useToggleQuestionFlag,
} from "@/features/practice/hooks/usePractice";

export default function QuestionViewer({ item, type = "question", onAttempted, onEdit, onDeleted, onFlagsChanged, hideNotes = false }) {
  const id = type === "pyq" ? item.pyq_id : item.question_id;
  const [selected, setSelected] = useState(null);
  const [natValue, setNatValue] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState(null);
  const [showSolution, setShowSolution] = useState(false);
  const [startedAt] = useState(Date.now());
  const [notes, setNotes] = useState("");
  const [mistakeType, setMistakeType] = useState("");
  const [flags, setFlags] = useState(item.flags || []);
  const [busyFlag, setBusyFlag] = useState(null);

  const { data: questionAttempts = [] } = useQuestionAttempts(type === "question" ? id : undefined);
  const { data: pyqAttempts = [] } = usePyqAttempts(type === "pyq" ? id : undefined);
  const attempts = type === "pyq" ? pyqAttempts : questionAttempts;
  const { data: noteData } = useQuestionNotes(type === "question" ? id : undefined);
  const saveQuestionNotes = useSaveQuestionNotes(type === "question" ? id : undefined);
  const submitQuestionAttempt = useSubmitQuestionAttempt(type === "question" ? id : undefined);
  const submitPyqAttempt = useSubmitPyqAttempt(type === "pyq" ? id : undefined);
  const toggleQuestionFlag = useToggleQuestionFlag(type === "question" ? id : undefined);
  const togglePyqFlag = useTogglePyqFlag(type === "pyq" ? id : undefined);
  const createMistake = useCreateMistake();
  const deleteQuestion = useDeleteQuestion();
  const deletePyq = useDeletePyq();

  useEffect(() => {
    if (type === "question") {
      setNotes(noteData?.note_content || "");
    }
  }, [noteData?.note_content, type]);

  useEffect(() => { setFlags(item.flags || []); }, [item.flags]);

  const saveNotes = async () => {
    if (type !== "question") return;
    try {
      await saveQuestionNotes.mutateAsync(notes);
      toast.success("Notes saved");
    } catch { toast.error("Failed to save"); }
  };

  const submit = async () => {
    let payload = selected;
    if (item.question_type === "NAT") payload = natValue;
    const time_taken = Math.round((Date.now() - startedAt) / 1000);
    try {
      const attemptPayload = { selected_answer: payload, time_taken };
      const resultData = type === "pyq"
        ? await submitPyqAttempt.mutateAsync(attemptPayload)
        : await submitQuestionAttempt.mutateAsync(attemptPayload);
      setResult(resultData);
      setSubmitted(true);
      setShowSolution(true);
      onAttempted && onAttempted(resultData);
    } catch { toast.error("Submit failed"); }
  };

  const logMistake = async () => {
    if (!mistakeType || type !== "question") return;
    try {
      await createMistake.mutateAsync({ question_id: id, mistake_type: mistakeType, note: "" });
      toast.success("Logged to Mistake Lab");
      setMistakeType("");
    } catch { toast.error("Failed"); }
  };

  const toggleFlag = async (flagType) => {
    setBusyFlag(flagType);
    try {
      const hasFlag = flags.includes(flagType);
      const resultData = type === "pyq"
        ? await togglePyqFlag.mutateAsync({ flagType, enabled: !hasFlag })
        : await toggleQuestionFlag.mutateAsync({ flagType, enabled: !hasFlag });
      const newFlags = resultData?.flags || [];
      setFlags(newFlags);
      onFlagsChanged && onFlagsChanged(id, newFlags);
      toast.success(hasFlag ? `Unmarked ${flagType}` : `Marked as ${flagType === "review" ? "review" : "important"}`);
    } catch {
      toast.error("Could not update flag");
    }
    setBusyFlag(null);
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete this ${type === "pyq" ? "PYQ" : "question"}? This also removes attempts, notes and flags.`)) return;
    try {
      if (type === "pyq") {
        await deletePyq.mutateAsync(id);
      } else {
        await deleteQuestion.mutateAsync(id);
      }
      toast.success("Deleted");
      onDeleted && onDeleted(id);
    } catch (e) {
      toast.error(e?.response?.data?.error?.message || "Delete failed");
    }
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

  const hasReview = flags.includes("review");
  const hasImportant = flags.includes("important");

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
        {item.topic && <Badge variant="secondary" className="text-[10px] font-medium">{item.topic}</Badge>}
        {item.year && <Badge variant="outline" className="mono text-[10px]">GATE {item.year}</Badge>}
        {item.source && <Badge variant="outline" className="mono text-[10px]">{item.source}</Badge>}
        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() => toggleFlag("review")}
            disabled={busyFlag === "review"}
            className={`h-7 px-2 rounded-md text-[10px] mono inline-flex items-center gap-1 border transition-colors ${
              hasReview ? "border-amber-500 text-amber-500 bg-amber-500/10" : "border-border text-muted-foreground hover:text-foreground"
            }`}
            data-testid="flag-review-btn"
            title={hasReview ? "Unmark review" : "Mark for review"}
          >
            {hasReview ? <BookmarkCheck className="w-3.5 h-3.5" /> : <Bookmark className="w-3.5 h-3.5" />}
            review
          </button>
          <button
            onClick={() => toggleFlag("important")}
            disabled={busyFlag === "important"}
            className={`h-7 px-2 rounded-md text-[10px] mono inline-flex items-center gap-1 border transition-colors ${
              hasImportant ? "border-yellow-400 text-yellow-300 bg-yellow-400/10" : "border-border text-muted-foreground hover:text-foreground"
            }`}
            data-testid="flag-important-btn"
            title={hasImportant ? "Unmark important" : "Mark as important"}
          >
            <Star className={`w-3.5 h-3.5 ${hasImportant ? "fill-yellow-300" : ""}`} />
            important
          </button>
          {onEdit && (
            <button
              onClick={() => onEdit(item)}
              className="h-7 w-7 inline-flex items-center justify-center rounded-md border border-border text-muted-foreground hover:text-foreground"
              data-testid="q-edit-btn"
              title="Edit"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
          )}
          {onDeleted && (
            <button
              onClick={handleDelete}
              className="h-7 w-7 inline-flex items-center justify-center rounded-md border border-border text-muted-foreground hover:text-red-500"
              data-testid="q-delete-btn"
              title="Delete"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="text-base leading-relaxed" data-testid="question-text">
        {renderContentWithTables(item.question_text)}
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
              <span className="text-sm">{formatMathText(opt)}</span>
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
                <span className="text-sm">{formatMathText(opt)}</span>
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
            <AppSelect
              value={mistakeType}
              onChange={setMistakeType}
              className="h-9 min-w-[180px] text-xs"
              testId="mistake-type-select"
              options={[
                { value: "", label: "Log mistake type..." },
                { value: "Conceptual Gap", label: "Conceptual Gap" },
                { value: "Calculation Error", label: "Calculation Error" },
                { value: "Question Misread", label: "Question Misread" },
                { value: "Silly Mistake", label: "Silly Mistake" },
              ]}
            />
            <Button size="sm" variant="outline" onClick={logMistake} data-testid="log-mistake-btn">
              <Bookmark className="w-3.5 h-3.5 mr-1" /> Log
            </Button>
          </div>
        )}
      </div>

      {showSolution && (
        <div
          className="mt-4 p-4 bg-secondary/40 border-l-2 border-foreground rounded-r-md text-sm leading-relaxed"
          data-testid="solution-content"
        >
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Solution</div>
          {renderContentWithTables(result?.solution || item.solution)}
        </div>
      )}

      {type === "question" && !hideNotes && (
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
            {saveQuestionNotes.isPending ? "Saving…" : "Auto-saves on blur"}
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
