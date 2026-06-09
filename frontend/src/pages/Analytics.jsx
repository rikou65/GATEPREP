import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

export default function Analytics() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/dashboard").then(r => setData(r.data?.data)); }, []);
  if (!data) return <div className="text-sm text-muted-foreground">Loading…</div>;

  const chartData = data.subjects.map(s => ({
    name: s.subject.name.split(" ")[0],
    QBank: s.qb.solved,
    PYQ: s.pyq.solved,
  }));
  const accData = data.subjects.map(s => ({
    name: s.subject.name.split(" ")[0],
    "QBank Acc": s.qb.accuracy,
    "PYQ Acc": s.pyq.accuracy,
  }));

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Insights</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Analytics</h1>
        <p className="text-sm text-muted-foreground mt-1">Question Bank and PYQ tracked independently.</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-5">
        <div className="border border-border rounded-lg p-5">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-3">Solved · by subject</div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={11} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="QBank" fill="#10B981" />
              <Bar dataKey="PYQ" fill="#3B82F6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="border border-border rounded-lg p-5">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-3">Accuracy · by subject</div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={accData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={11} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} domain={[0, 100]} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="QBank Acc" fill="#F59E0B" />
              <Bar dataKey="PYQ Acc" fill="#A78BFA" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
