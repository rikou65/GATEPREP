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
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-border">
              <tr className="text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                <th className="p-3 font-medium">Subject</th>
                <th className="p-3 font-medium">QBank Solved</th>
                <th className="p-3 font-medium">QBank Acc</th>
                <th className="p-3 font-medium">PYQ Solved</th>
                <th className="p-3 font-medium">PYQ Acc</th>
              </tr>
            </thead>
            <tbody>
              {data.subjects.map((s) => (
                <tr key={s.subject.subject_id} className="border-b border-border hover:bg-secondary/40">
                  <td className="p-3">
                    <Link to={`/subjects/${s.subject.subject_id}`} className="hover:underline" data-testid={`subject-row-${s.subject.subject_id}`}>
                      {s.subject.name}
                    </Link>
                  </td>
                  <td className="p-3 mono text-xs">{s.qb.solved}/{s.qb.total}</td>
                  <td className="p-3 mono text-xs">{s.qb.accuracy}%</td>
                  <td className="p-3 mono text-xs">{s.pyq.solved}/{s.pyq.total}</td>
                  <td className="p-3 mono text-xs">{s.pyq.accuracy}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
