import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Link, useParams } from "react-router-dom";
import { BookCheck, History, FileText, Sparkles, ArrowUpRight } from "lucide-react";

export default function SubjectDetail() {
  const { id } = useParams();
  const [subject, setSubject] = useState(null);
  const [rows, setRows] = useState([]);

  useEffect(() => {
    api.get(`/subjects/${id}`).then(r => setSubject(r.data?.data));
    api.get(`/analytics/subject/${id}`).then(r => setRows(r.data?.data || []));
  }, [id]);

  if (!subject) return <div className="text-sm text-muted-foreground">Loading…</div>;

  const qbTotal = rows.reduce((a, r) => a + r.qb.total, 0);
  const qbSolved = rows.reduce((a, r) => a + r.qb.solved, 0);
  const pyqTotal = rows.reduce((a, r) => a + r.pyq.total, 0);
  const pyqSolved = rows.reduce((a, r) => a + r.pyq.solved, 0);

  return (
    <div className="space-y-8">
      <div>
        <Link to="/subjects" className="text-xs mono text-muted-foreground hover:text-foreground">← Subjects</Link>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-2">{subject.name}</h1>
        <p className="text-sm text-muted-foreground mt-1">{rows.length} topics · {qbTotal} questions · {pyqTotal} PYQs</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <SummaryCard icon={BookCheck} label="QBank Solved" value={`${qbSolved}/${qbTotal}`} />
        <SummaryCard icon={History} label="PYQ Solved" value={`${pyqSolved}/${pyqTotal}`} />
        <Link to={`/questions?subject_id=${id}`} className="border border-border rounded-lg p-5 hover:border-foreground/40 transition-colors group">
          <FileText className="w-4 h-4 text-muted-foreground mb-3" strokeWidth={1.5} />
          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">Open Question Bank</div>
          <div className="text-base font-medium mt-1 inline-flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">Practice <ArrowUpRight className="w-4 h-4" /></div>
        </Link>
        <Link to={`/pyqs?subject_id=${id}`} className="border border-border rounded-lg p-5 hover:border-foreground/40 transition-colors group">
          <History className="w-4 h-4 text-muted-foreground mb-3" strokeWidth={1.5} />
          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">Open PYQs</div>
          <div className="text-base font-medium mt-1 inline-flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">Solve <ArrowUpRight className="w-4 h-4" /></div>
        </Link>
      </div>

      <div>
        <div className="flex items-baseline justify-between mb-3">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Topics</div>
          <div className="text-[10px] mono text-muted-foreground/70">click a topic to open it</div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {rows.map(r => <TopicCard key={r.topic.topic_id} row={r} />)}
        </div>
      </div>
    </div>
  );
}

const SummaryCard = ({ icon: Icon, label, value }) => (
  <div className="border border-border rounded-lg p-5">
    <Icon className="w-4 h-4 text-muted-foreground mb-3" strokeWidth={1.5} />
    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">{label}</div>
    <div className="text-2xl mono font-bold mt-1">{value}</div>
  </div>
);

const TopicCard = ({ row }) => {
  const { topic, qb, pyq, notes_count, mistakes_count } = row;
  const qbRemaining = qb.total - qb.solved;
  const pyqRemaining = pyq.total - pyq.solved;
  const accuracyTone = (acc, hasAttempts) => {
    if (!hasAttempts) return "text-muted-foreground/60";
    if (acc >= 75) return "text-emerald-400";
    if (acc >= 50) return "text-amber-400";
    return "text-red-400";
  };

  return (
    <Link
      to={`/topics/${topic.topic_id}`}
      data-testid={`topic-row-${topic.topic_id}`}
      className="group border border-border rounded-lg p-5 hover:border-foreground/30 hover:bg-secondary/20 transition-colors block"
    >
      <div className="flex items-start justify-between gap-3 mb-4">
        <h3 className="text-base font-semibold leading-snug">{topic.name}</h3>
        <ArrowUpRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all shrink-0 mt-0.5" />
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <MetricBlock
          label="QBank"
          solved={qb.solved}
          total={qb.total}
          remaining={qbRemaining}
          accuracy={qb.accuracy}
          accuracyTone={accuracyTone(qb.accuracy, qb.solved > 0)}
        />
        <MetricBlock
          label="PYQ"
          solved={pyq.solved}
          total={pyq.total}
          remaining={pyqRemaining}
          accuracy={pyq.accuracy}
          accuracyTone={accuracyTone(pyq.accuracy, pyq.solved > 0)}
        />
      </div>

      {(notes_count > 0 || mistakes_count > 0) && (
        <div className="flex items-center gap-3 pt-3 border-t border-border/60 text-[11px] mono text-muted-foreground">
          {notes_count > 0 && (
            <span className="inline-flex items-center gap-1">
              <FileText className="w-3 h-3" /> {notes_count} notes
            </span>
          )}
          {mistakes_count > 0 && (
            <span className="inline-flex items-center gap-1 text-amber-400/80">
              <Sparkles className="w-3 h-3" /> {mistakes_count} to revisit
            </span>
          )}
        </div>
      )}
    </Link>
  );
};

const MetricBlock = ({ label, solved, total, remaining, accuracy, accuracyTone }) => (
  <div className="rounded-md border border-border/70 px-3 py-2.5 bg-background/30">
    <div className="flex items-baseline justify-between mb-1.5">
      <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">{label}</span>
      <span className={`text-[11px] mono font-medium ${accuracyTone}`}>{accuracy}%</span>
    </div>
    <div className="text-sm mono">
      <span className="font-semibold">{solved}</span>
      <span className="text-muted-foreground">/{total}</span>
    </div>
    <div className="text-[10px] mono text-muted-foreground mt-0.5">
      {total === 0 ? "no items yet" : remaining === 0 ? "all done" : `${remaining} left`}
    </div>
  </div>
);
