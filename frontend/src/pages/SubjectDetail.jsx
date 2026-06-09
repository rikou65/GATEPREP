import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Link, useParams } from "react-router-dom";
import { ChevronRight, BookCheck, History, FileText, AlertOctagon } from "lucide-react";

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
        <Card icon={BookCheck} label="QBank Solved" value={`${qbSolved}/${qbTotal}`} />
        <Card icon={History} label="PYQ Solved" value={`${pyqSolved}/${pyqTotal}`} />
        <Link to={`/questions?subject_id=${id}`} className="border border-border rounded-lg p-5 hover:border-foreground/40">
          <FileText className="w-4 h-4 text-muted-foreground mb-3" strokeWidth={1.5} />
          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">Open Question Bank</div>
          <div className="text-base font-medium mt-1">Practice →</div>
        </Link>
        <Link to={`/pyqs?subject_id=${id}`} className="border border-border rounded-lg p-5 hover:border-foreground/40">
          <History className="w-4 h-4 text-muted-foreground mb-3" strokeWidth={1.5} />
          <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">Open PYQs</div>
          <div className="text-base font-medium mt-1">Solve →</div>
        </Link>
      </div>

      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Topics</div>
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-border">
              <tr className="text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                <th className="p-3 font-medium">Topic</th>
                <th className="p-3 font-medium">QBank</th>
                <th className="p-3 font-medium">QBank Acc</th>
                <th className="p-3 font-medium">PYQ</th>
                <th className="p-3 font-medium">PYQ Acc</th>
                <th className="p-3 font-medium">Notes</th>
                <th className="p-3 font-medium">Mistakes</th>
                <th className="p-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.topic.topic_id} className="border-b border-border hover:bg-secondary/40">
                  <td className="p-3">{r.topic.name}</td>
                  <td className="p-3 mono text-xs">{r.qb.solved}/{r.qb.total}</td>
                  <td className="p-3 mono text-xs">{r.qb.accuracy}%</td>
                  <td className="p-3 mono text-xs">{r.pyq.solved}/{r.pyq.total}</td>
                  <td className="p-3 mono text-xs">{r.pyq.accuracy}%</td>
                  <td className="p-3 mono text-xs">{r.notes_count}</td>
                  <td className="p-3 mono text-xs">{r.mistakes_count}</td>
                  <td className="p-3 text-right">
                    <Link
                      to={`/topics/${r.topic.topic_id}`}
                      data-testid={`topic-row-${r.topic.topic_id}`}
                      className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                    >
                      open <ChevronRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const Card = ({ icon: Icon, label, value }) => (
  <div className="border border-border rounded-lg p-5">
    <Icon className="w-4 h-4 text-muted-foreground mb-3" strokeWidth={1.5} />
    <div className="text-xs uppercase tracking-[0.15em] text-muted-foreground">{label}</div>
    <div className="text-2xl mono font-bold mt-1">{value}</div>
  </div>
);
