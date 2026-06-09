import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";

export default function Subjects() {
  const [subjects, setSubjects] = useState([]);
  useEffect(() => { api.get("/subjects").then(r => setSubjects(r.data?.data || [])); }, []);
  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Syllabus</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Subjects</h1>
        <p className="text-sm text-muted-foreground mt-1">Official GATE CSE syllabus · system-owned, cannot be edited.</p>
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        {subjects.map(s => (
          <Link
            key={s.subject_id}
            to={`/subjects/${s.subject_id}`}
            data-testid={`subject-card-${s.subject_id}`}
            className="group border border-border rounded-lg p-5 bg-card/40 hover:border-foreground/40 transition-colors flex items-center justify-between"
          >
            <div>
              <div className="text-xs mono text-muted-foreground">#{String(s.order + 1).padStart(2, "0")}</div>
              <div className="text-base font-medium mt-1">{s.name}</div>
            </div>
            <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-transform group-hover:translate-x-0.5" />
          </Link>
        ))}
      </div>
    </div>
  );
}
