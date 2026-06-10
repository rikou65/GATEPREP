import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Link } from "react-router-dom";
import { ArrowUpRight, Target, BookCheck, History, ListVideo, AlertOctagon, FolderArchive, TrendingUp, Library } from "lucide-react";

const StatCard = ({ icon: Icon, label, value, suffix, testId }) => (
  <div className="border border-border rounded-lg p-5 bg-card/40 hover:border-border/80 transition-colors" data-testid={testId}>
    <div className="flex items-start justify-between mb-3">
      <Icon className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
    </div>
    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">{label}</div>
    <div className="mt-2 flex items-baseline gap-1">
      <div className="text-3xl font-bold mono">{value}</div>
      {suffix && <div className="text-sm text-muted-foreground mono">{suffix}</div>}
    </div>
  </div>
);

export default function Dashboard() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/dashboard").then((r) => setData(r.data?.data)); }, []);

  if (!data) return <div className="text-sm text-muted-foreground">Loading…</div>;
  const s = data.summary;

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Overview</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Everything you've actually done — no manual status, no guesses.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={BookCheck} label="Questions Solved" value={s.questions_solved} testId="stat-questions-solved" />
        <StatCard icon={History} label="PYQs Solved" value={s.pyqs_solved} testId="stat-pyqs-solved" />
        <StatCard icon={ListVideo} label="Videos Completed" value={s.videos_completed} testId="stat-videos-completed" />
        <StatCard icon={Library} label="Playlists" value={s.total_playlists} testId="stat-playlists" />
        <StatCard icon={Target} label="QBank Accuracy" value={s.question_accuracy} suffix="%" testId="stat-qbank-accuracy" />
        <StatCard icon={TrendingUp} label="PYQ Accuracy" value={s.pyq_accuracy} suffix="%" testId="stat-pyq-accuracy" />
        <StatCard icon={AlertOctagon} label="Total Mistakes" value={s.total_mistakes} testId="stat-mistakes" />
        <StatCard icon={FolderArchive} label="Resources" value={s.resources_uploaded} testId="stat-resources" />
      </div>

      <div className="space-y-3">
        <div className="flex items-end justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">By Subject</div>
            <h2 className="text-xl font-semibold tracking-tight mt-1">Question Bank vs PYQ progress</h2>
          </div>
          <Link to="/subjects" className="text-xs mono text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
            View all <ArrowUpRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {data.subjects.map((s) => (
            <SubjectProgressCard key={s.subject.subject_id} row={s} />
          ))}
        </div>
      </div>
    </div>
  );
}

const accuracyTone = (acc, hasAttempts) => {
  if (!hasAttempts) return "text-muted-foreground/50";
  if (acc >= 75) return "text-emerald-400";
  if (acc >= 50) return "text-amber-400";
  return "text-red-400";
};

const barTone = (acc, hasAttempts) => {
  if (!hasAttempts) return "bg-muted-foreground/20";
  if (acc >= 75) return "bg-emerald-400/80";
  if (acc >= 50) return "bg-amber-400/80";
  return "bg-red-400/80";
};

const SubjectProgressCard = ({ row }) => {
  const { subject, qb, pyq } = row;
  const qbPct = qb.total > 0 ? Math.round((qb.solved / qb.total) * 100) : 0;
  const pyqPct = pyq.total > 0 ? Math.round((pyq.solved / pyq.total) * 100) : 0;

  return (
    <Link
      to={`/subjects/${subject.subject_id}`}
      data-testid={`subject-row-${subject.subject_id}`}
      className="group block border border-border rounded-lg p-4 hover:border-foreground/30 hover:bg-secondary/20 transition-colors"
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="text-sm font-semibold leading-snug">{subject.name}</div>
        <ArrowUpRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all shrink-0 mt-0.5" />
      </div>

      <ProgressRow label="QBank" solved={qb.solved} total={qb.total} accuracy={qb.accuracy} pct={qbPct} />
      <div className="h-2" />
      <ProgressRow label="PYQ" solved={pyq.solved} total={pyq.total} accuracy={pyq.accuracy} pct={pyqPct} />
    </Link>
  );
};

const ProgressRow = ({ label, solved, total, accuracy, pct }) => {
  const hasAttempts = solved > 0;
  return (
    <div>
      <div className="flex items-center justify-between text-[10px] mono mb-1">
        <span className="uppercase tracking-[0.15em] text-muted-foreground">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-foreground/90">
            <span className="font-semibold">{solved}</span>
            <span className="text-muted-foreground">/{total}</span>
          </span>
          <span className={`tabular-nums ${accuracyTone(accuracy, hasAttempts)}`}>{accuracy}%</span>
        </div>
      </div>
      <div className="h-1.5 rounded-full bg-muted-foreground/10 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${barTone(accuracy, hasAttempts)}`}
          style={{ width: `${total > 0 ? pct : 0}%` }}
        />
      </div>
    </div>
  );
};
