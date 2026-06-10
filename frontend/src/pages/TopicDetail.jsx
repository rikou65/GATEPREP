import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Link, useParams } from "react-router-dom";
import { BookCheck, History, FileText, AlertOctagon } from "lucide-react";

export default function TopicDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);

  useEffect(() => { api.get(`/analytics/topic/${id}`).then(r => setData(r.data?.data)); }, [id]);

  if (!data) return <div className="text-sm text-muted-foreground">Loading…</div>;
  const t = data.topic;

  return (
    <div className="space-y-8">
      <div>
        <Link to={`/subjects/${t.subject_id}`} className="text-xs mono text-muted-foreground hover:text-foreground">← Back</Link>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-2">{t.name}</h1>
        <p className="text-sm text-muted-foreground mt-1">Topic metrics · derived from your activity</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Box icon={BookCheck} label="QBank Solved" value={`${data.qb.solved}/${data.qb.total}`} sub={`${data.qb.accuracy}% accuracy`} />
        <Box icon={History} label="PYQ Solved" value={`${data.pyq.solved}/${data.pyq.total}`} sub={`${data.pyq.accuracy}% accuracy`} />
        <Box icon={FileText} label="Notes" value={data.notes_count} />
        <Box icon={AlertOctagon} label="Mistakes" value={data.mistakes_count} />
      </div>

      <div className="flex gap-3">
        <Link to={`/questions?subject_id=${t.subject_id}&topic_id=${id}`} className="px-4 py-2 text-sm border border-border rounded-md hover:border-foreground/40" data-testid="open-qbank-btn">Open Question Bank →</Link>
        <Link to={`/pyqs?subject_id=${t.subject_id}&topic_id=${id}`} className="px-4 py-2 text-sm border border-border rounded-md hover:border-foreground/40" data-testid="open-pyqs-btn">Open PYQs →</Link>
      </div>
    </div>
  );
}

const Box = ({ icon: Icon, label, value, sub }) => (
  <div className="border border-border rounded-lg p-5">
    <Icon className="w-4 h-4 text-muted-foreground mb-3" strokeWidth={1.5} />
    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">{label}</div>
    <div className="text-2xl mono font-bold mt-1">{value}</div>
    {sub && <div className="text-xs text-muted-foreground mt-1 mono">{sub}</div>}
  </div>
);
